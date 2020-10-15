from homeassistant.helpers.icon import icon_for_battery_level
from homeassistant.const import STATE_OK, STATE_PROBLEM, DEVICE_CLASS_BATTERY, PERCENTAGE
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import dispatcher_send, async_dispatcher_connect
import logging
from . import TRYFI_DOMAIN, TRYFI_FLAG_UPDATED, TryFiCore, TryFiPet
LOGGER = logging.getLogger(__name__)

def setup_scanner(hass, config, add_entities, discovery_info=None):
    """Set up the sensor platform."""
    ##add_entities([ExampleSensor()])
    #tryfi_service = hass.data.get(TRYFI_DOMAIN)
    tryfi = hass.data[TRYFI_DOMAIN]
    
    for pet in tryfi._pets:
        tracker = TryFiPetTracker(add_entities, hass, tryfi, pet)
        tracker.update()
        add_entities(tracker)


class TryFiPetTracker():
    def __init__(self, see, hass, tryfi, pet):
        self._pet = pet
        self._see = see
        self._hass = hass
        self._tryfi = tryfi
        #super().__init__(hass, tryfi, pet)
        print (self.pet)
        print (self._see)
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
        self._tryfi = self._hass.data[TRYFI_DOMAIN]
        for pet in self._tryfi.pets:
            if self.pet.name == pet.name:
                self._pet = pet
                break
    @property
    def name(self):
        return f"{self.pet.name} Tracker"
    @property
    def pet(self):
        return self._pet
    @property
    def unique_id(self):
        return f"{self.pet.petId}-tracker"
    @property
    def device_id(self):
        return self.unique_id
    @property
    def entity_picture(self):
        return self.pet.photoLink
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

