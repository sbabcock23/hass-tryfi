from homeassistant.core import callback
from homeassistant.helpers.entity import Entity
from homeassistant.helpers import config_validation as cv, discovery
from homeassistant.helpers.dispatcher import dispatcher_send, async_dispatcher_connect
from homeassistant.helpers.event import track_time_interval
from homeassistant.const import CONF_NAME, CONF_USERNAME, CONF_PASSWORD
import logging
from datetime import timedelta
from pytryfi import PyTryFi

TRYFI_DOMAIN = "tryfi"
TRYFI_SERVICE = "tryfi_service"
TRYFI_FLAG_UPDATED = 'tryfi_updated'

REFRESH_TIME = 60

LOGGER = logging.getLogger(__name__)

def setup(hass, config):
    """Set up a skeleton component."""
    conf = config[TRYFI_DOMAIN]
    username = conf.get(CONF_USERNAME)
    password = conf.get(CONF_PASSWORD)

    tryfi = PyTryFi(username, password)
    #tryfiEntity = TryFiCore(hass, tryfi)
    #hass.data[TRYFI_DOMAIN] = tryfi
    hass.data[TRYFI_DOMAIN] = tryfi
    
    def refresh_all_data(event_time):
        
        hass.data[TRYFI_DOMAIN].updatePets()
        hass.data[TRYFI_DOMAIN].updateBases()
        dispatcher_send(hass, TRYFI_FLAG_UPDATED)
        #print(f"Refreshing data for TRYFI {event_time}\n{hass.data[TRYFI_DOMAIN]}")

    hass.services.register(TRYFI_DOMAIN, 'update', refresh_all_data)
    # automatically update ADTPulse data (samples) on the scan interval
    scan_interval = timedelta(seconds = 10)
    track_time_interval(hass, refresh_all_data, scan_interval)

    discovery.load_platform(hass, "sensor", TRYFI_DOMAIN, {}, config)
    discovery.load_platform(hass, "device_tracker", TRYFI_DOMAIN, {}, config)
    discovery.load_platform(hass, "light", TRYFI_DOMAIN, {}, config)
    #light
    #update function

    return True

class TryFiCore(Entity):
    def __init__(self, hass, tryfi):
        self._name = f"tryfi_{tryfi.username}"
        self._hass = hass
        self._tryfi = tryfi
    @property
    def tryfi(self):
        return self._tryfi
    
    async def async_added_to_hass(self):
        """Register callbacks."""
        # register callback when cached ADTPulse data has been updated
        async_dispatcher_connect(self._hass, TRYFI_FLAG_UPDATED, self._update_callback)       
    @callback
    def _update_callback(self):
        """Call update method."""
        self.async_schedule_update_ha_state()

class TryFiPet(TryFiCore):
    def __init__(self, hass, tryfi, pet):
        self._pet = pet
    @property
    def pet(self):
        return self._pet
    