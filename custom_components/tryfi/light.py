from homeassistant.helpers.icon import icon_for_battery_level
from homeassistant.const import STATE_OK, STATE_PROBLEM, DEVICE_CLASS_BATTERY, PERCENTAGE
from . import TRYFI_DOMAIN, TRYFI_FLAG_UPDATED
from homeassistant.util import color
from homeassistant.components.light import LightEntity, SUPPORT_COLOR
import logging

from homeassistant.core import callback
from homeassistant.helpers.dispatcher import dispatcher_send, async_dispatcher_connect

from homeassistant.helpers import device_registry as dr
from .const import DOMAIN
LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_devices):
    """Add sensors for passed config_entry in HA."""
    tryfi = hass.data[DOMAIN][config_entry.entry_id]

    new_devices = []
    for pet in tryfi.pets:
        new_devices.append(TryFiPetLight(hass, tryfi, pet))
    if new_devices:
        async_add_devices(new_devices)

class TryFiPetLight(LightEntity):
    def __init__(self, hass, tryfi, pet):
        self._pet = pet
        self._tryfi = tryfi
        self._hass = hass

    async def async_added_to_hass(self):
        """Register callbacks."""
        # register callback when data has been updated
        LOGGER.info(f"Notifying update for data for {self.name}")
        async_dispatcher_connect(self._hass, TRYFI_FLAG_UPDATED, self._update_callback)       
    @callback
    def _update_callback(self):
        """Call update method."""
        LOGGER.info(f"Scheduling update for data for {self.name}")
        self.async_schedule_update_ha_state(True)
    @property
    def should_poll(self):
        """Updates occur periodically from __init__ when changes detected"""
        return True
    
    def update(self):
        LOGGER.info(f"Updating data for {self.name}")
        #print(self.pet)
        #self._tryfi = self._hass.data[DOMAIN]
        #self._pet = self._tryfi.getPet(self.pet.petId)
        #print(self.pet)
    @property
    def name(self):
        return f"{self.pet.name} - Collar Light"
    @property
    def unique_id(self):
        print(self.pet)
        return f"{self.pet.petId}-light"
    @property
    def device_id(self):
        return self.unique_id
    @property
    def pet(self):
        return self._pet
    @property
    def is_on(self):
        return bool(self.pet.device.ledOn)
    #@property
    #def hs_color(self):
    #    colorObj = color(self.pet.device.ledColor)
    #    return colorObj.hsl
    @property
    def tryfi(self):
        return self._tryfi
    @property
    def pet(self):
        return self._pet
    @property
    def supported_features(self):
        return SUPPORT_COLOR

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.pet.petId)},
            "name": self.pet.name,
            "manufacturer": "TryFi",
            "model": self.pet.breed,
            "sw_version": self.pet.device.buildId,
            #"via_device": (TRYFI_DOMAIN, self.tryfi)
        }
    
    def turn_on(self, **kwargs):
        self.pet.turnOnOffLed(self.tryfi.session, "ON")
    def turn_off(self, **kwargs):
        self.pet.turnOnOffLed(self.tryfi.session, "OFF")
