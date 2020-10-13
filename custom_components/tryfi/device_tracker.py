from homeassistant.helpers.icon import icon_for_battery_level
from homeassistant.const import STATE_OK, STATE_PROBLEM, DEVICE_CLASS_BATTERY, PERCENTAGE
from . import TRYFI_DOMAIN, TryFiCore, TryFiPet

def setup_scanner(hass, config, add_entities, discovery_info=None):
    """Set up the sensor platform."""
    ##add_entities([ExampleSensor()])
    #tryfi_service = hass.data.get(TRYFI_DOMAIN)
    tryfi = hass.data[TRYFI_DOMAIN]
    
    for pet in tryfi._pets:
        tracker = TryFiPetTracker(add_entities, pet)
        tracker.update()
        add_entities(tracker)


class TryFiPetTracker(TryFiPet):
    def __init__(self, see, pet):
        self._pet = pet
        self._see = see
        print (self.pet)
        print (self._see)
    @property
    def pet(self):
        return self._pet
    @property
    def unique_id(self):
        return self.pet.petId
    @property
    def device_id(self):
        return self.unique_id
    def update(self) -> None:
        dev_id = self.pet.petId
        attrs = {}
        gps = [float(self.pet.currLatitude), float(self.pet.currLongitude)]
        self._see(
            dev_id = dev_id,
            host_name=self.pet.name,
            gps=gps,
            attributes=attrs,
            icon="mdi:dog"
        )

