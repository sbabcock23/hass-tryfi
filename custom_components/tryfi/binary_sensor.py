import logging

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    DEVICE_CLASS_BATTERY_CHARGING,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.icon import icon_for_battery_level

from .const import DOMAIN

LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_devices):
    """Add binary sensors for passed config_entry in HA."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    tryfi = coordinator.data

    new_devices = []
    for pet in tryfi.pets:
        LOGGER.debug(f"Adding Pet Battery Charging Binary Sensor: {pet}")
        new_devices.append(TryFiBatteryChargingBinarySensor(hass, pet, coordinator))
    if new_devices:
        async_add_devices(new_devices)

class TryFiBatteryChargingBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of a Binary Sensor."""

    def __init__(self, hass, pet, coordinator):
        self._hass = hass
        self._petId = pet.petId
        super().__init__(coordinator)

    @property
    def name(self):
        """Return the name of the binary sensor."""
        return f"{self.pet.name} Collar Battery Charging"

    @property
    def unique_id(self):
        """Return the ID of this sensor."""
        return f"{self.pet.petId}-battery-charging"

    @property
    def petId(self):
        return self._petId

    @property
    def pet(self):
        return self.coordinator.data.getPet(self.petId)

    @property
    def device(self):
        return self.pet.device

    @property
    def device_id(self):
        return self.unique_id

    @property
    def device_class(self):
        """Return the device class of the binary sensor."""
        return DEVICE_CLASS_BATTERY_CHARGING

    @property
    def isCharging(self):
        return bool(self.pet.device.isCharging)

    @property
    def icon(self):
        """Return the icon for charging."""
        if self.isCharging:
            return "mdi:power-plug"
        else:
            return "mdi:power-plug-off"

    @property
    def is_on(self):
        """Return the state of the binary sensor"""
        return self.isCharging

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.pet.petId)},
            "name": self.pet.name,
            "manufacturer": "TryFi",
            "model": self.pet.breed,
            "sw_version": self.pet.device.buildId,
        }
