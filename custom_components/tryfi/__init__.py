import asyncio

from homeassistant.core import callback
from homeassistant.helpers.entity import Entity
from homeassistant.helpers import config_validation as cv, discovery
from homeassistant.helpers.dispatcher import dispatcher_send, async_dispatcher_connect
from homeassistant.helpers.event import track_time_interval
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant import exceptions

from .const import DOMAIN, CONF_USERNAME, CONF_PASSWORD, CONF_POLLING_RATE, DEFAULT_POLLING_RATE
import logging
from datetime import timedelta
from pytryfi import PyTryFi

TRYFI_DOMAIN = "tryfi"
TRYFI_SERVICE = "tryfi_service"
TRYFI_FLAG_UPDATED = 'tryfi_updated'

REFRESH_TIME = 60

LOGGER = logging.getLogger(__name__)


PLATFORMS = ["device_tracker", "light", "sensor"]
#PLATFORMS = ["sensor"]


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Hello World component."""
    # Ensure our name space for storing objects is a known type. A dict is
    # common/preferred as it allows a separate instance of your class for each
    # instance that has been created in the UI.
    hass.data.setdefault(DOMAIN, {})

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Hello World from a config entry."""
    # Store an instance of the "connecting" class that does the work of speaking
    # with your actual devices.
    hass.data[DOMAIN][entry.entry_id] = PyTryFi(username=entry.data["username"], password=entry.data["password"])

    print(hass.data[DOMAIN][entry.entry_id])
    
    # def refresh_all_data(event_time):
        
    #     hass.data[DOMAIN][entry.entry_id].updatePets()
    #     hass.data[DOMAIN][entry.entry_id].updateBases()
    #     dispatcher_send(hass, TRYFI_FLAG_UPDATED)
    #     #print(f"Refreshing data for TRYFI {event_time}\n{hass.data[TRYFI_DOMAIN]}")

    # hass.services.register(DOMAIN, 'update', refresh_all_data)
    # # automatically update ADTPulse data (samples) on the scan interval
    # scan_interval = timedelta(seconds = 10)
    # track_time_interval(hass, refresh_all_data, scan_interval)

    # This creates each HA object for each platform your device requires.
    # It's done by calling the `async_setup_entry` function in each platform module.
    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    return True


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
        print(tryfi)
        userId = tryfi._userId
        if userId != None or "":
            LOGGER.info("Success Connecting to TryFi")
    except Exception as err:
        LOGGER.error("Error connecting to TryFi")
        raise CannotConnect from err

class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""