from homeassistant.components.select import SelectEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

async def async_setup_entry(hass, config_entry, async_add_devices):
    """Add sensors for passed config_entry in HA."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    tryfi = coordinator.data

    new_devices = []
    for pet in tryfi.pets:
        new_devices.append(TryFiLostMode(hass, pet, coordinator))
    if new_devices:
        async_add_devices(new_devices)


class TryFiLostMode(CoordinatorEntity, SelectEntity):
    def __init__(self, hass, pet, coordinator):
        self._petId = pet.petId
        self._hass = hass
        super().__init__(coordinator)

    @property
    def name(self):
        return f"{self.pet.name} Lost Mode"

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
    def options(self):
        return ['Safe', 'Lost']

    @property
    def current_option(self):
        if self.pet.isLost:
            return 'Lost'
        else:
            return 'Safe'

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.pet.petId)},
            "name": self.pet.name,
            "manufacturer": "TryFi",
            "model": self.pet.breed,
            "sw_version": self.pet.device.buildId,
        }
    
    def select_option(self, option):
        self.pet.setLostDogMode(self.tryfi.session, option == 'Lost')
