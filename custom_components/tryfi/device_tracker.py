from homeassistant.helpers.icon import icon_for_battery_level
from homeassistant.const import STATE_OK, STATE_PROBLEM, DEVICE_CLASS_BATTERY, PERCENTAGE
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import dispatcher_send, async_dispatcher_connect
from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.components.device_tracker import SOURCE_TYPE_GPS

import logging
from . import DOMAIN, TRYFI_FLAG_UPDATED
LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_devices):
    """Add sensors for passed config_entry in HA."""
    tryfi = hass.data[DOMAIN][config_entry.entry_id]

    new_devices = []
    for pet in tryfi.pets:
        new_devices.append(TryFiPetTracker(async_add_devices, hass, tryfi, pet))
    if new_devices:
        async_add_devices(new_devices, True)

class TryFiPetTracker(TrackerEntity):
    def __init__(self, see, hass, tryfi, pet):
        self._pet = pet
        self._see = see
        self._hass = hass
        self._tryfi = tryfi

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
        #self._tryfi = self._hass.data[DOMAIN]
        #self._pet = self._tryfi.getPet(self.pet.petId)
        # for pet in self._tryfi.pets:
        #     if self.pet.name == pet.name:
        #         self._pet = pet
        #         break
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
    @property
    def latitude(self):
        return float(self.pet.currLatitude)
    @property
    def longitude(self):
        return float(self.pet.currLongitude)
    @property
    def source_type(self):
        """Return the source type, eg gps or router, of the device."""
        return SOURCE_TYPE_GPS
    @property
    def battery_level(self):
        return self.pet.device.batteryPercent

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