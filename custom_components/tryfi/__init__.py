import asyncio
import logging
from datetime import timedelta

from homeassistant import exceptions
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import discovery
from homeassistant.helpers.dispatcher import async_dispatcher_connect, dispatcher_send
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import track_time_interval
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)
from pytryfi import PyTryFi

from .const import (
    CONF_PASSWORD,
    CONF_POLLING_RATE,
    CONF_USERNAME,
    DEFAULT_POLLING_RATE,
    DOMAIN,
    PLATFORMS,
)

LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict):
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    tryfi = await hass.async_add_executor_job(PyTryFi,entry.data["username"], entry.data["password"])
    hass.data[DOMAIN][entry.entry_id] = tryfi

    # Exceptions are swallowed in the PyTryFi library, so we must assert a 
    # sucessful login before continuing with setup. When not successful,
    # hass will continue to retry setup
    if not hasattr(tryfi, 'currentUser'):
        raise ConfigEntryNotReady

    # The options flow writes the polling rate to entry.options, so prefer it.
    # entry.data only holds the value captured during initial setup.
    polling_rate = entry.options.get(
        CONF_POLLING_RATE, entry.data.get(CONF_POLLING_RATE, DEFAULT_POLLING_RATE)
    )
    coordinator = TryFiDataUpdateCoordinator(hass, tryfi, int(polling_rate))
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # This creates each HA object for each platform your device requires.
    # It's done by calling the `async_setup_entry` function in each platform module.
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True


async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Reload the entry so a changed polling rate takes effect."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    # This is called when an entry/configured device is to be removed. The class
    # needs to unload itself, and remove callbacks. See the classes for further
    # details
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_connect_or_timeout(hass, tryfi):
    userId = None
    try:
        userId = tryfi._userId
        if userId != None or "":
            LOGGER.info("Success Connecting to TryFi")
    except Exception as err:
        LOGGER.error("Error connecting to TryFi")
        raise CannotConnect from err


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class TryFiDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage the refresh of the tryfi data api"""

    def __init__(self, hass, tryfi, pollingRate):
        self._tryfi = tryfi
        self._hass = hass
        self._pollingRate = int(pollingRate)
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=pollingRate),
        )

    @property
    def tryfi(self):
        return self._tryfi

    @property
    def pollingRate(self):
        return self._pollingRate

    async def _async_update_data(self):
        """Update data via library."""
        try:
            await self._hass.async_add_executor_job(self.tryfi.update)
        except Exception as error:
            LOGGER.error("Error updating TryFi data\n{error}")
            raise UpdateFailed(error) from error
        return self.tryfi
