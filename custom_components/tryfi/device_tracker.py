from homeassistant.helpers.icon import icon_for_battery_level
from homeassistant.const import STATE_OK, STATE_PROBLEM, DEVICE_CLASS_BATTERY, PERCENTAGE
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import dispatcher_send, async_dispatcher_connect
from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.components.device_tracker import SOURCE_TYPE_GPS
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)
import logging
from .const import DOMAIN
LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_devices):
    """Add sensors for passed config_entry in HA."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    tryfi = coordinator.data

    new_devices = []
    for pet in tryfi.pets:
        new_devices.append(TryFiPetTracker(async_add_devices, hass, pet, coordinator))
    if new_devices:
        async_add_devices(new_devices, True)

class TryFiPetTracker(CoordinatorEntity, TrackerEntity):
    def __init__(self, see, hass, pet, coordinator):
        self._petId = pet.petId
        self._see = see
        super().__init__(coordinator)

    @property
    def name(self):
        return f"{self.pet.name} Tracker"
    @property
    def pet(self):
        return self.coordinator.data.getPet(self.petId)
    @property
    def petId(self):
        return self._petId
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
        }