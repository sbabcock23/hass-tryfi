from homeassistant.helpers.entity import Entity
from homeassistant.helpers import config_validation as cv, discovery
from homeassistant.const import CONF_NAME, CONF_USERNAME, CONF_PASSWORD
from pytryfi import PyTryFi

TRYFI_DOMAIN = "tryfi"
DOMAIN_SERVICE = "tryfi_service"

TRYFI_FLAG_UPDATED = 'tryfi_updated'

REFRESH_TIME = 60

def setup(hass, config):
    """Set up a skeleton component."""
    conf = config[TRYFI_DOMAIN]
    username = conf.get(CONF_USERNAME)
    password = conf.get(CONF_PASSWORD)

    tryfi = PyTryFi(username, password)
    hass.data[TRYFI_DOMAIN] = tryfi
    
    def refresh_all_data(event_time):
        print(f"Refreshing data for TRYFI {event_time}")


    hass.services.register(TRYFI_DOMAIN, 'update', refresh_all_data)

    discovery.load_platform(hass, "sensor", TRYFI_DOMAIN, {}, config)
    discovery.load_platform(hass, "device_tracker", TRYFI_DOMAIN, {}, config)
    discovery.load_platform(hass, "light", TRYFI_DOMAIN, {}, config)
    #light
    #update function

    return True

class TryFiCore(Entity):
    def __init__(self, tryfi):
        self._name = f"tryfi_{tryfi.username}"
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

class TryFiPet(TryFiCore):
    def __init__(self, pet):
        self._pet = pet
    @property
    def pet(self):
        return self._pet
    