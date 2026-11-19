"""Polling TryFi on a timer."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, TypeAlias

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import TryFiAuthError, TryFiClient, TryFiError
from .const import (
    CONF_POLLING_RATE,
    CONF_USERNAME,
    DEFAULT_POLLING_RATE,
    DOMAIN,
    MIN_POLLING_RATE,
)

LOGGER = logging.getLogger(__package__)

TryFiConfigEntry: TypeAlias = ConfigEntry["TryFiDataUpdateCoordinator"]


def polling_rate(entry: ConfigEntry[Any]) -> int:
    """Seconds between refreshes: the options, then the entry, then the default.

    Upstream only ever read entry.data, so the options form saved a value
    nothing looked at. Its form also stored the number as text, and entries
    from it may still hold "10"; anything below the floor is raised to it.
    """
    raw = entry.options.get(
        CONF_POLLING_RATE, entry.data.get(CONF_POLLING_RATE, DEFAULT_POLLING_RATE)
    )
    try:
        rate = int(float(raw))
    except (TypeError, ValueError):
        rate = DEFAULT_POLLING_RATE
    return max(rate, MIN_POLLING_RATE)


class TryFiDataUpdateCoordinator(DataUpdateCoordinator[TryFiClient]):
    """Refreshes every pet and base on the account."""

    config_entry: TryFiConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: TryFiConfigEntry, client: TryFiClient
    ) -> None:
        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=polling_rate(entry)),
        )
        self.client = client

    async def _async_update_data(self) -> TryFiClient:
        try:
            await self.client.async_refresh()
        except TryFiError as first:
            LOGGER.debug("TryFi refresh failed (%s); signing in again", first)
            await self._async_sign_in_and_retry()
        self._async_remove_stale_devices()
        return self.client

    async def _async_sign_in_and_retry(self) -> None:
        # Once per failed poll, never in a loop: an outage costs one sign-in a
        # poll interval, not a burst of them. TryFi's session can lapse, and
        # upstream had no way back from that short of a reload (#56, #91).
        try:
            await self.client.async_login()
            await self.client.async_refresh()
        except TryFiAuthError as err:
            raise ConfigEntryAuthFailed(
                translation_domain=DOMAIN,
                translation_key="auth_failed",
                translation_placeholders={
                    "username": self.config_entry.data[CONF_USERNAME]
                },
            ) from err
        except TryFiError as err:
            # The coordinator logs this once when updates start failing and
            # once when they recover, rather than on every poll.
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="update_failed",
                translation_placeholders={"error": str(err)},
            ) from err

    def _async_remove_stale_devices(self) -> None:
        """Remove the device of any pet or base the account no longer lists.

        Only on a refresh whose listing was complete, and only for things
        absent from it. A removed device takes the user's entity ids with it,
        so anything short of TryFi plainly listing the account is no grounds:
        not an answer with errors beside it (review of ad0329c: one partial
        answer deleted every pet), not one listing nothing at all, and not a
        pet listed but unreadable or without its collar, which can be deleted
        by hand.
        """
        listed = self.client.listed_pet_ids | self.client.listed_base_ids
        if not self.client.listing_complete or not listed:
            return
        registry = dr.async_get(self.hass)
        for device in dr.async_entries_for_config_entry(
            registry, self.config_entry.entry_id
        ):
            ours = {value for domain, value in device.identifiers if domain == DOMAIN}
            if ours and not ours & listed:
                LOGGER.info("Removing %s: no longer on the TryFi account", device.name)
                # Not async_update_device(remove_config_entry_id=): deprecated
                # from 2026.10. A TryFi device belongs to this entry alone.
                registry.async_remove_device(device.id)
