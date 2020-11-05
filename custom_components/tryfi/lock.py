import logging

from homeassistant.components.lock import LockEntity
from homeassistant.const import ATTR_ATTRIBUTION, STATE_LOCKED, STATE_UNLOCKED
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DOMAIN


async def async_setup_entry(hass, config_entry, async_add_devices):
    """Add sensors for passed config_entry in HA."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    tryfi = coordinator.data

    new_devices = []
    for pet in tryfi.pets:
        new_devices.append(TryFiLock(hass, pet, coordinator))
    if new_devices:
        async_add_devices(new_devices)


class TryFiLock(CoordinatorEntity, LockEntity):
    def __init__(self, hass, pet, coordinator):
        self._petId = pet.petId
        self._hass = hass
        super().__init__(coordinator)

    @property
    def name(self):
        return f"{self.pet.name} - Lost State"

    @property
    def petId(self):
        return self._petId

    @property
    def pet(self):
        return self.coordinator.data.getPet(self.petId)

    @property
    def tryfi(self):
        return self.coordinator.data

    @property
    def unique_id(self):
        return f"{self.pet.petId}-lost"

    @property
    def device_id(self):
        return self.unique_id

    @property
    def is_locked(self):
        # if pet is lost (returns true) then retrun is locked as false
        if self.pet.isLost:
            return False
        else:
            return True

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.pet.petId)},
            "name": self.pet.name,
            "manufacturer": "TryFi",
            "model": self.pet.breed,
            "sw_version": self.pet.device.buildId,
        }

    # dog is home then its "locked"
    def lock(self, **kwargs):
        self.pet.setLostDogMode(self.tryfi.session, False)

    # dog is lost then its "unlocked"
    def unlock(self, **kwargs):
        self.pet.setLostDogMode(self.tryfi.session, True)
