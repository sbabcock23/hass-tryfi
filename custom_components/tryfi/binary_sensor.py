"""Support for TryFi binary sensors."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.helpers.entity import EntityCategory
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .pytryfi import PyTryFi

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up TryFi binary sensors from a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    tryfi: PyTryFi = coordinator.data

    entities = []
    
    _LOGGER.info("Setting up TryFi binary sensors - found %d pets and %d bases", len(tryfi.pets), len(tryfi.bases))
    
    # Add battery charging sensors for pets
    entities.extend([
        TryFiBatteryChargingBinarySensor(coordinator, pet)
        for pet in tryfi.pets
    ])
    
    # Add health sensors for base stations
    entities.extend([
        TryFiBaseHealthBinarySensor(coordinator, base)
        for base in tryfi.bases
    ])
    
    # Add firmware update sensors for pets with devices
    entities.extend([
        TryFiFirmwareUpdateBinarySensor(coordinator, pet)
        for pet in tryfi.pets
        if hasattr(pet, "device") and pet.device
    ])
    
    async_add_entities(entities)


class TryFiBatteryChargingBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of a TryFi battery charging binary sensor."""
    
    _attr_has_entity_name = False
    _attr_device_class = BinarySensorDeviceClass.BATTERY_CHARGING
    
    def __init__(self, coordinator: Any, pet: Any) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._pet_id = pet.petId
        self._attr_unique_id = f"{pet.petId}-battery-charging"
        self._attr_name = f"{pet.name} Collar Battery Charging"
    
    @property
    def pet(self) -> Any:
        """Get the pet object from coordinator data."""
        return self.coordinator.data.getPet(self._pet_id)
    
    @property
    def is_on(self) -> bool | None:
        """Return true if the battery is charging."""
        if self.pet and hasattr(self.pet, "device") and self.pet.device:
            return bool(getattr(self.pet.device, "isCharging", False))
        return None
    
    @property
    def icon(self) -> str:
        """Return the icon to use in the frontend."""
        return "mdi:power-plug" if self.is_on else "mdi:power-plug-off"
    
    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        pet = self.pet
        if not pet:
            return {}
        
        device_info = {
            "identifiers": {(DOMAIN, pet.petId)},
            "name": pet.name,
            "manufacturer": MANUFACTURER,
            "model": MODEL,
        }
        
        # Add breed if available
        if hasattr(pet, "breed") and pet.breed:
            device_info["model"] = f"{MODEL} - {pet.breed}"
        
        # Add firmware version if available
        if hasattr(pet, "device") and pet.device:
            if hasattr(pet.device, "buildId"):
                device_info["sw_version"] = pet.device.buildId
        
        return device_info


class TryFiBaseHealthBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of a TryFi base station health binary sensor."""
    
    _attr_has_entity_name = False
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    
    def __init__(self, coordinator: Any, base: Any) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._base_id = base.baseId
        self._attr_unique_id = f"{base.baseId}-health"
        self._attr_name = f"{base.name} Connection Health"
    
    @property
    def base(self) -> Any:
        """Get the base object from coordinator data."""
        return self.coordinator.data.getBase(self._base_id)
    
    @property
    def is_on(self) -> bool | None:
        """Return true if the base station connection is healthy."""
        base = self.base
        if not base:
            return None
            
        # Connection is healthy if online and not explicitly unhealthy
        if not base.online:
            return False
            
        if hasattr(base, "onlineQuality"):
            return base.onlineQuality != "UNHEALTHY"
            
        return True
    
    @property
    def icon(self) -> str:
        """Return the icon to use in the frontend."""
        if self.is_on:
            return "mdi:wifi-check"
        return "mdi:wifi-alert"
    
    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        base = self.base
        if not base:
            return {}
        
        return {
            "identifiers": {(DOMAIN, base.baseId)},
            "name": base.name,
            "manufacturer": MANUFACTURER,
            "model": "TryFi Base Station",
        }


class TryFiFirmwareUpdateBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of a TryFi firmware update availability sensor."""
    
    _attr_has_entity_name = False
    _attr_device_class = BinarySensorDeviceClass.UPDATE
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    
    # Known firmware versions (you can update this list as new versions are released)
    LATEST_FIRMWARE = "3.3.0"  # Example version
    
    def __init__(self, coordinator: Any, pet: Any) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._pet_id = pet.petId
        self._attr_unique_id = f"{pet.petId}-firmware-update"
        self._attr_name = f"{pet.name} Firmware Update Available"
    
    @property
    def pet(self) -> Any:
        """Get the pet object from coordinator data."""
        return self.coordinator.data.getPet(self._pet_id)
    
    @property
    def is_on(self) -> bool | None:
        """Return true if firmware update is available."""
        if self.pet and hasattr(self.pet, "device") and self.pet.device:
            current_version = getattr(self.pet.device, "buildId", None)
            if current_version:
                # Simple version comparison - you might want to improve this
                # For now, just check if versions are different
                return current_version != self.LATEST_FIRMWARE
        return None
    
    @property
    def icon(self) -> str:
        """Return the icon to use in the frontend."""
        return "mdi:update" if self.is_on else "mdi:check-circle"
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        attrs = {}
        if self.pet and hasattr(self.pet, "device") and self.pet.device:
            current_version = getattr(self.pet.device, "buildId", None)
            if current_version:
                attrs["current_version"] = current_version
                attrs["latest_version"] = self.LATEST_FIRMWARE
        return attrs
    
    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        pet = self.pet
        if not pet:
            return {}
        
        device_info = {
            "identifiers": {(DOMAIN, pet.petId)},
            "name": pet.name,
            "manufacturer": MANUFACTURER,
            "model": MODEL,
        }
        
        # Add breed if available
        if hasattr(pet, "breed") and pet.breed:
            device_info["model"] = f"{MODEL} - {pet.breed}"
        
        # Add firmware version if available
        if hasattr(pet, "device") and pet.device:
            if hasattr(pet.device, "buildId"):
                device_info["sw_version"] = pet.device.buildId
        
        return device_info