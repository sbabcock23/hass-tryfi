"""Support for TryFi sensors."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfLength,
    UnitOfTime,
    UnitOfMass,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL, SENSOR_STATS_BY_TIME, SENSOR_STATS_BY_TYPE
from .pytryfi import PyTryFi

_LOGGER = logging.getLogger(__name__)

SENSOR_DESCRIPTIONS: dict[str, SensorEntityDescription] = {
    "battery": SensorEntityDescription(
        key="battery",
        name="Collar Battery Level",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "steps": SensorEntityDescription(
        key="steps",
        name="Steps",
        native_unit_of_measurement="steps",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:paw",
    ),
    "distance": SensorEntityDescription(
        key="distance",
        name="Distance",
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:map-marker-distance",
    ),
    "sleep": SensorEntityDescription(
        key="sleep",
        name="Sleep",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:sleep",
    ),
    "nap": SensorEntityDescription(
        key="nap",
        name="Nap",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:power-sleep",
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up TryFi sensors from a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    tryfi: PyTryFi = coordinator.data

    entities: list[SensorEntity] = []
    
    _LOGGER.info("Setting up TryFi sensors - found %d pets and %d bases", len(tryfi.pets), len(tryfi.bases))
    
    # Add pet sensors
    for pet in tryfi.pets:
        _LOGGER.debug("Adding sensors for pet: %s", pet.name)
        
        # Battery sensor
        entities.append(TryFiBatterySensor(coordinator, pet))
        
        # Activity stats sensors
        for stat_type in SENSOR_STATS_BY_TYPE:
            for stat_time in SENSOR_STATS_BY_TIME:
                entities.append(
                    PetStatsSensor(coordinator, pet, stat_type, stat_time)
                )
        
        # Generic sensors
        entities.extend([
            PetGenericSensor(coordinator, pet, "Activity Type"),
            PetGenericSensor(coordinator, pet, "Current Place Name"),
            PetGenericSensor(coordinator, pet, "Current Place Address"),
            PetGenericSensor(coordinator, pet, "Connected To"),
            PetGenericSensor(coordinator, pet, "Home City State"),
            PetGenericSensor(coordinator, pet, "Gender"),
            PetGenericSensor(coordinator, pet, "Weight"),
            PetGenericSensor(coordinator, pet, "Age"),
            PetGenericSensor(coordinator, pet, "Connection State"),
            PetGenericSensor(coordinator, pet, "LED Color"),
            PetGenericSensor(coordinator, pet, "Module ID"),
            PetGenericSensor(coordinator, pet, "Signal Strength"),
        ])
        
        # Add sleep quality score sensor
        if hasattr(pet, "device") and pet.device:
            entities.append(PetSleepQualitySensor(coordinator, pet))
    
    # Add base sensors
    for base in tryfi.bases:
        _LOGGER.debug("Adding sensors for base: %s", base.name)
        entities.extend([
            TryFiBaseSensor(coordinator, base),
            TryFiBaseDiagnosticSensor(coordinator, base, "WiFi SSID"),
            TryFiBaseDiagnosticSensor(coordinator, base, "Base ID"),
            TryFiBaseDiagnosticSensor(coordinator, base, "Connection Quality"),
        ])
    
    async_add_entities(entities)


class TryFiSensorBase(CoordinatorEntity, SensorEntity):
    """Base class for TryFi sensors."""
    
    _attr_has_entity_name = False
    
    def __init__(self, coordinator: Any) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)


class TryFiBatterySensor(TryFiSensorBase):
    """Representation of a TryFi battery sensor."""
    
    def __init__(self, coordinator: Any, pet: Any) -> None:
        """Initialize the battery sensor."""
        super().__init__(coordinator)
        self._pet_id = pet.petId
        self._attr_unique_id = f"{pet.petId}-battery"
        self._attr_name = f"{pet.name} Collar Battery Level"
        description = SENSOR_DESCRIPTIONS["battery"]
        self._attr_device_class = description.device_class
        self._attr_native_unit_of_measurement = description.native_unit_of_measurement
        self._attr_state_class = description.state_class
        self._attr_entity_category = description.entity_category
    
    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        pet = self.coordinator.data.getPet(self._pet_id)
        return {
            "identifiers": {(DOMAIN, pet.petId)},
            "name": pet.name,
            "manufacturer": MANUFACTURER,
            "model": MODEL,
        }
    
    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        pet = self.coordinator.data.getPet(self._pet_id)
        if pet and pet.device:
            return pet.device.batteryPercent
        return None
    
    @property
    def icon(self) -> str:
        """Return the icon to use in the frontend."""
        battery_level = self.native_value
        charging = False
        
        pet = self.coordinator.data.getPet(self._pet_id)
        if pet and pet.device:
            charging = pet.device.isCharging
        
        return icon_for_battery_level(battery_level, charging)


class PetStatsSensor(TryFiSensorBase):
    """Representation of a TryFi pet statistics sensor."""
    
    def __init__(
        self,
        coordinator: Any,
        pet: Any,
        stat_type: str,
        stat_time: str,
    ) -> None:
        """Initialize the statistics sensor."""
        super().__init__(coordinator)
        self._pet_id = pet.petId
        self._stat_type = stat_type.upper()
        self._stat_time = stat_time.upper()
        self._attr_unique_id = f"{pet.petId}-{stat_time.lower()}-{stat_type.lower()}"
        self._attr_name = f"{pet.name} {stat_time.title()} {stat_type.title()}"
        
        # Set attributes from description
        if stat_type.lower() in SENSOR_DESCRIPTIONS:
            description = SENSOR_DESCRIPTIONS[stat_type.lower()]
            self._attr_device_class = description.device_class
            self._attr_native_unit_of_measurement = description.native_unit_of_measurement
            self._attr_state_class = description.state_class
            self._attr_icon = description.icon
    
    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        pet = self.coordinator.data.getPet(self._pet_id)
        return {
            "identifiers": {(DOMAIN, pet.petId)},
            "name": pet.name,
            "manufacturer": MANUFACTURER,
            "model": MODEL,
        }
    
    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        pet = self.coordinator.data.getPet(self._pet_id)
        if not pet:
            return None
            
        # Build the attribute name from stat_time and stat_type
        # e.g., "DAILY" + "STEPS" -> "dailySteps"
        attr_name = f"{self._stat_time.lower()}{self._stat_type.title()}"
        
        # Special case for total distance
        if self._stat_type == "DISTANCE":
            attr_name = f"{self._stat_time.lower()}TotalDistance"
            
        # Try to get the attribute value
        value = getattr(pet, attr_name, None)
        
        # Convert distance from meters to kilometers
        if value is not None and self._stat_type == "DISTANCE":
            value = round(value / 1000, 2)
        
        # Convert sleep/nap from seconds to minutes
        if value is not None and (self._stat_type == "SLEEP" or self._stat_type == "NAP"):
            value = round(value / 60, 1)
            
        return value


class PetGenericSensor(TryFiSensorBase):
    """Representation of a generic TryFi pet sensor."""
    
    def __init__(self, coordinator: Any, pet: Any, sensor_type: str) -> None:
        """Initialize the generic sensor."""
        super().__init__(coordinator)
        self._pet_id = pet.petId
        self._sensor_type = sensor_type
        self._attr_unique_id = f"{pet.petId}-{sensor_type.replace(' ', '-').lower()}"
        self._attr_name = f"{pet.name} {sensor_type}"
        self._attr_icon = self._get_icon()
        
        # Set units for specific sensor types
        if sensor_type == "Weight":
            self._attr_native_unit_of_measurement = UnitOfMass.POUNDS
            self._attr_device_class = SensorDeviceClass.WEIGHT
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif sensor_type == "Age":
            self._attr_native_unit_of_measurement = "years"
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif sensor_type == "Signal Strength":
            self._attr_native_unit_of_measurement = PERCENTAGE
            self._attr_state_class = SensorStateClass.MEASUREMENT
    
    def _get_icon(self) -> str:
        """Get icon based on sensor type."""
        icons = {
            "Activity Type": "mdi:run",
            "Current Place Name": "mdi:map-marker",
            "Current Place Address": "mdi:home-map-marker",
            "Connected To": "mdi:wifi",
            "Home City State": "mdi:home-city",
            "Gender": "mdi:gender-male-female",
            "Weight": "mdi:weight",
            "Age": "mdi:calendar-clock",
            "Connection State": "mdi:connection",
            "LED Color": "mdi:palette",
            "Module ID": "mdi:identifier",
            "Signal Strength": "mdi:signal",
        }
        return icons.get(self._sensor_type, "mdi:information")
    
    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        pet = self.coordinator.data.getPet(self._pet_id)
        return {
            "identifiers": {(DOMAIN, pet.petId)},
            "name": pet.name,
            "manufacturer": MANUFACTURER,
            "model": MODEL,
        }
    
    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        pet = self.coordinator.data.getPet(self._pet_id)
        if not pet:
            return None
        
        if self._sensor_type == "Activity Type":
            return getattr(pet, "activityType", None)
        elif self._sensor_type == "Current Place Name":
            return getattr(pet, "currPlaceName", None)
        elif self._sensor_type == "Current Place Address":
            return getattr(pet, "currPlaceAddress", None)
        elif self._sensor_type == "Connected To":
            return getattr(pet, "connectedTo", None)
        elif self._sensor_type == "Home City State":
            return getattr(pet, "homeCityState", None)
        elif self._sensor_type == "Gender":
            return getattr(pet, "gender", None)
        elif self._sensor_type == "Weight":
            return getattr(pet, "weight", None)
        elif self._sensor_type == "Age":
            if hasattr(pet, "yearOfBirth") and pet.yearOfBirth:
                from datetime import datetime
                current_year = datetime.now().year
                age = current_year - pet.yearOfBirth
                return age
            return None
        elif self._sensor_type == "Connection State":
            if hasattr(pet, "device") and pet.device:
                return getattr(pet.device, "connectionStateType", None)
        elif self._sensor_type == "LED Color":
            if hasattr(pet, "device") and pet.device:
                return getattr(pet.device, "ledColor", None)
        elif self._sensor_type == "Module ID":
            if hasattr(pet, "device") and pet.device:
                return getattr(pet.device, "moduleId", None)
        elif self._sensor_type == "Signal Strength":
            connected_to = getattr(pet, "connectedTo", None)
            if connected_to and "Cellular Signal Strength" in str(connected_to):
                # Extract percentage from string like "Cellular Signal Strength - 85"
                try:
                    strength = int(connected_to.split(" - ")[-1])
                    return strength
                except:
                    pass
            return None
        
        return None


class TryFiBaseSensor(TryFiSensorBase):
    """Representation of a TryFi base station sensor."""
    
    def __init__(self, coordinator: Any, base: Any) -> None:
        """Initialize the base sensor."""
        super().__init__(coordinator)
        self._base_id = base.baseId
        self._attr_unique_id = base.baseId
        self._attr_name = base.name
        self._attr_icon = "mdi:home-circle"
    
    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        base = self.coordinator.data.getBase(self._base_id)
        return {
            "identifiers": {(DOMAIN, base.baseId)},
            "name": base.name,
            "manufacturer": MANUFACTURER,
            "model": "TryFi Base Station",
        }
    
    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        base = self.coordinator.data.getBase(self._base_id)
        if not base:
            return None
            
        # Return detailed status including health
        if not base.online:
            return "Offline"
        elif hasattr(base, 'onlineQuality') and base.onlineQuality == "UNHEALTHY":
            return "Unhealthy"
        else:
            return "Online"
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional base station attributes."""
        base = self.coordinator.data.getBase(self._base_id)
        if not base:
            return {}
        
        attrs = {}
        
        # Network information
        if hasattr(base, 'networkname') and base.networkname:
            attrs["wifi_network"] = base.networkname
        
        # Connection quality
        if hasattr(base, 'onlineQuality'):
            attrs["connection_quality"] = base.onlineQuality
            
        # Last update time
        if hasattr(base, 'lastUpdated'):
            attrs["last_updated"] = base.lastUpdated
            
        return attrs


class TryFiBaseDiagnosticSensor(TryFiSensorBase):
    """Representation of a TryFi base station diagnostic sensor."""
    
    def __init__(self, coordinator: Any, base: Any, sensor_type: str) -> None:
        """Initialize the diagnostic sensor."""
        super().__init__(coordinator)
        self._base_id = base.baseId
        self._sensor_type = sensor_type
        self._attr_unique_id = f"{base.baseId}-{sensor_type.replace(' ', '-').lower()}"
        self._attr_name = f"{base.name} {sensor_type}"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_icon = self._get_icon()
    
    def _get_icon(self) -> str:
        """Get icon based on sensor type."""
        icons = {
            "WiFi SSID": "mdi:wifi",
            "Base ID": "mdi:identifier",
            "Connection Quality": "mdi:signal",
        }
        return icons.get(self._sensor_type, "mdi:information")
    
    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        base = self.coordinator.data.getBase(self._base_id)
        return {
            "identifiers": {(DOMAIN, base.baseId)},
            "name": base.name,
            "manufacturer": MANUFACTURER,
            "model": "TryFi Base Station",
        }
    
    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        base = self.coordinator.data.getBase(self._base_id)
        if not base:
            return None
        
        if self._sensor_type == "WiFi SSID":
            return getattr(base, "networkname", None)
        elif self._sensor_type == "Base ID":
            return getattr(base, "baseId", None)
        elif self._sensor_type == "Connection Quality":
            return getattr(base, "onlineQuality", None)
        
        return None


class PetSleepQualitySensor(TryFiSensorBase):
    """Representation of a TryFi pet sleep quality sensor."""
    
    def __init__(self, coordinator: Any, pet: Any) -> None:
        """Initialize the sleep quality sensor."""
        super().__init__(coordinator)
        self._pet_id = pet.petId
        self._attr_unique_id = f"{pet.petId}-sleep-quality"
        self._attr_name = f"{pet.name} Sleep Quality Score"
        self._attr_icon = "mdi:sleep"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT
    
    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        pet = self.coordinator.data.getPet(self._pet_id)
        return {
            "identifiers": {(DOMAIN, pet.petId)},
            "name": pet.name,
            "manufacturer": MANUFACTURER,
            "model": MODEL,
        }
    
    @property
    def native_value(self) -> StateType:
        """Calculate sleep quality score based on sleep patterns."""
        pet = self.coordinator.data.getPet(self._pet_id)
        if not pet:
            return None
        
        # Get daily sleep and nap in seconds from API
        daily_sleep_seconds = getattr(pet, "dailySleep", 0)
        daily_nap_seconds = getattr(pet, "dailyNap", 0)
        
        # Convert to minutes for calculation
        daily_sleep = daily_sleep_seconds / 60
        daily_nap = daily_nap_seconds / 60
        
        # Total rest in minutes
        total_rest = daily_sleep + daily_nap
        
        # Dogs typically need 12-14 hours of sleep per day (720-840 minutes)
        # Puppies and older dogs need more (up to 18-20 hours)
        optimal_rest = 780  # 13 hours as baseline
        
        if total_rest == 0:
            return 0
        
        # Calculate score based on how close to optimal
        if total_rest >= optimal_rest:
            # Good amount of rest
            score = min(100, 80 + (total_rest - optimal_rest) / 30)
        else:
            # Less than optimal
            score = max(0, (total_rest / optimal_rest) * 80)
        
        # Bonus points for good sleep/nap balance
        if daily_sleep > 0 and daily_nap > 0:
            balance_ratio = min(daily_sleep, daily_nap) / max(daily_sleep, daily_nap)
            score = min(100, score + (balance_ratio * 20))
        
        return round(score)


def icon_for_battery_level(
    battery_level: int | None, charging: bool = False
) -> str:
    """Return battery icon based on level and charging status."""
    if battery_level is None:
        return "mdi:battery-unknown"
    
    if charging:
        return "mdi:battery-charging"
    
    if battery_level >= 90:
        return "mdi:battery"
    elif battery_level >= 70:
        return "mdi:battery-80"
    elif battery_level >= 50:
        return "mdi:battery-60"
    elif battery_level >= 30:
        return "mdi:battery-40"
    elif battery_level >= 10:
        return "mdi:battery-20"
    else:
        return "mdi:battery-alert"