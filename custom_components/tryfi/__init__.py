"""The TryFi integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr

from .api import TryFiAuthError, TryFiError, async_connect
from .const import CONF_PASSWORD, CONF_USERNAME, DOMAIN, PLATFORMS, account_id
from .coordinator import TryFiConfigEntry, TryFiDataUpdateCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: TryFiConfigEntry) -> bool:
    try:
        client = await async_connect(
            hass, entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD]
        )
    except TryFiAuthError as err:
        # Starts the re-authentication flow, so a changed password asks for the
        # new one instead of retrying the old one in the background for ever.
        raise ConfigEntryAuthFailed(
            translation_domain=DOMAIN,
            translation_key="auth_failed",
            translation_placeholders={"username": entry.data[CONF_USERNAME]},
        ) from err
    except TryFiError as err:
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN,
            translation_key="cannot_connect",
            translation_placeholders={"error": str(err)},
        ) from err

    _async_adopt_unique_id(hass, entry, client.user_id)
    coordinator = TryFiDataUpdateCoordinator(hass, entry, client)
    # Signing in has just read every pet and base, so hand that over rather
    # than fetching the whole account a second time straight away.
    coordinator.async_set_updated_data(client)
    entry.runtime_data = coordinator

    entry.async_on_unload(entry.add_update_listener(_async_reload_on_change))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: TryFiConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        # Home Assistant detaches it on unload too; doing it here does not
        # depend on the session having been made inside setup.
        entry.runtime_data.client.detach()
    return unloaded


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: TryFiConfigEntry, device: dr.DeviceEntry
) -> bool:
    """Allow deleting a device by hand once TryFi no longer reports it.

    For a pet the account still lists but cannot be read, or one whose collar
    was taken off: automatic removal leaves those, since they may come back.
    """
    client = entry.runtime_data.client
    current = {pet.pet_id for pet in client.pets} | {
        base.base_id for base in client.bases
    }
    return not any(
        domain == DOMAIN and value in current for domain, value in device.identifiers
    )


def _async_adopt_unique_id(
    hass: HomeAssistant, entry: TryFiConfigEntry, user_id: str | None
) -> None:
    """Give an entry the account's TryFi user id as its unique id.

    So the config flow can refuse a second entry for the same account. Left
    alone if another entry already holds it, which only a duplicate made
    before 0.1.0 could.
    """
    if user_id is None or entry.unique_id == user_id:
        return
    # None for an entry made by upstream; the login email for one given an id
    # by 2b0fb15, before the id became TryFi's user id. Anything else is left.
    if entry.unique_id not in (None, account_id(entry.data[CONF_USERNAME])):
        return
    if hass.config_entries.async_entry_for_domain_unique_id(DOMAIN, user_id):
        return
    hass.config_entries.async_update_entry(entry, unique_id=user_id)


async def _async_reload_on_change(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Apply a new polling rate without a restart."""
    await hass.config_entries.async_reload(entry.entry_id)
