from homeassistant.helpers.icon import icon_for_battery_level
from homeassistant.const import STATE_OK, STATE_PROBLEM, DEVICE_CLASS_BATTERY, PERCENTAGE
from . import TRYFI_DOMAIN, TryFiCore, TryFiPet
from homeassistant.util import color
from homeassistant.components.light import LightEntity

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the sensor platform."""
    ##add_entities([ExampleSensor()])
    #tryfi_service = hass.data.get(TRYFI_DOMAIN)
    tryfi = hass.data[TRYFI_DOMAIN]

    for pet in tryfi._pets:
        print(pet)
        
        add_entities([TryFiPetLight(pet)])

class TryFiPetLight(LightEntity):
    def __init__(self, pet):
        self._pet = pet
    
    @property
    def name(self):
        return f"{self.pet.name} - Collar Light"
    @property
    def unique_id(self):
        return self.pet.petId
    @property
    def device_id(self):
        return self.unique_id
    @property
    def pet(self):
        return self._pet
    @property
    def is_on(self):
        return bool(self.pet._device.ledOn)
    @property
    def hs_color(self):
        colorObj = Color(self.pet._device.ledColor)
        return colorObj.hsl