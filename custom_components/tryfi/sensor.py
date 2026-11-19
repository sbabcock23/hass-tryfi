"""Collar battery, activity totals, whereabouts, connection, and base status."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfLength, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .client import Base, Pet
from .const import DOMAIN, SENSOR_STATS_BY_TIME, SENSOR_STATS_BY_TYPE
from .coordinator import TryFiConfigEntry, TryFiDataUpdateCoordinator
from .entity import TryFiPetEntity, async_add_per_base, async_add_per_pet

# Read-only, and every reading comes from the coordinator's one refresh.
PARALLEL_UPDATES = 0


@dataclass(frozen=True)
class _Stat:
    """Where one stat type lives on a pet, and what it means."""

    read: Callable[[Pet], dict[str, Any]]
    divisor: int | None
    unit: str
    device_class: SensorDeviceClass | None
    precision: int


# TryFi reports distance in metres and rest in seconds. Distance stays in
# kilometres and rest in minutes, the units upstream used, so the long-term
# statistics already recorded carry on in the same unit.
_STATS = {
    "STEPS": _Stat(lambda pet: pet.steps, None, "steps", None, 0),
    "DISTANCE": _Stat(
        lambda pet: pet.distance_m,
        1000,
        UnitOfLength.KILOMETERS,
        SensorDeviceClass.DISTANCE,
        2,
    ),
    "SLEEP": _Stat(
        lambda pet: pet.sleep_s, 60, UnitOfTime.MINUTES, SensorDeviceClass.DURATION, 0
    ),
    "NAP": _Stat(
        lambda pet: pet.nap_s, 60, UnitOfTime.MINUTES, SensorDeviceClass.DURATION, 0
    ),
}

# TryFi's activity and connection type names, and the state each becomes. One
# TryFi does not list here reads as unknown rather than as a raw API name.
ACTIVITY_STATES = {"OngoingRest": "resting", "OngoingWalk": "walking"}
CONNECTION_STATES = {
    "ConnectedToBase": "base",
    "ConnectedToWifi": "wifi",
    "ConnectedToCellular": "cellular",
    "ConnectedToUser": "phone",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TryFiConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data

    def per_pet(pet: Pet) -> list[SensorEntity]:
        return [
            TryFiBatterySensor(coordinator, pet),
            *(
                PetStatsSensor(coordinator, pet, stat_type, stat_time)
                for stat_type in SENSOR_STATS_BY_TYPE
                for stat_time in SENSOR_STATS_BY_TIME
            ),
            PetActivitySensor(coordinator, pet),
            PetPlaceSensor(coordinator, pet, "Current Place Name"),
            PetPlaceSensor(coordinator, pet, "Current Place Address"),
            PetConnectionSensor(coordinator, pet),
            PetSignalSensor(coordinator, pet),
        ]

    async_add_per_pet(entry, async_add_entities, per_pet)
    async_add_per_base(
        entry, async_add_entities, lambda base: [TryFiBaseSensor(coordinator, base)]
    )


def _slug(label: str) -> str:
    return label.lower().replace(" ", "-")


class TryFiBaseSensor(CoordinatorEntity[TryFiDataUpdateCoordinator], SensorEntity):
    """Whether a charging base is online. The base's only entity."""

    _attr_has_entity_name = True
    # The base's main feature, so it takes the device's own name.
    _attr_name = None
    _attr_translation_key = "base"

    def __init__(self, coordinator: TryFiDataUpdateCoordinator, base: Base) -> None:
        super().__init__(coordinator)
        self._base_id = base.base_id
        self._attr_unique_id = f"{base.base_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, base.base_id)},
            name=base.name,
            manufacturer="TryFi",
            model="TryFi Base",
        )

    @property
    def available(self) -> bool:
        return (
            super().available
            and self.coordinator.data.get_base(self._base_id) is not None
        )

    @property
    def native_value(self) -> str | None:
        base = self.coordinator.data.get_base(self._base_id)
        if base is None or base.online is None:
            return None
        return "Online" if base.online else "Offline"


class PetActivitySensor(TryFiPetEntity, SensorEntity):
    """Resting or walking."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = list(ACTIVITY_STATES.values())

    def __init__(self, coordinator: TryFiDataUpdateCoordinator, pet: Pet) -> None:
        super().__init__(coordinator, pet, "activity-type", "activity_type")

    @property
    def native_value(self) -> str | None:
        return ACTIVITY_STATES.get(self.pet.activity_type or "")


class PetPlaceSensor(TryFiPetEntity, SensorEntity):
    """The saved place the pet is at, by name or by address."""

    def __init__(
        self, coordinator: TryFiDataUpdateCoordinator, pet: Pet, label: str
    ) -> None:
        super().__init__(coordinator, pet, _slug(label), _slug(label).replace("-", "_"))
        self._address = label == "Current Place Address"

    @property
    def native_value(self) -> str | None:
        pet = self.pet
        return pet.place_address if self._address else pet.place_name


class PetConnectionSensor(TryFiPetEntity, SensorEntity):
    """How the collar last reached TryFi, and through what."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = list(CONNECTION_STATES.values())
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: TryFiDataUpdateCoordinator, pet: Pet) -> None:
        super().__init__(coordinator, pet, "connected-to", "connected_to")

    @property
    def native_value(self) -> str | None:
        return CONNECTION_STATES.get(self.collar.connection_type or "")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Which base, whose phone, or what signal (upstream #60)."""
        collar = self.collar
        attributes: dict[str, Any] = {}
        if base_id := collar.connected_base_id:
            attributes["base_id"] = base_id
            if (base := self.coordinator.data.get_base(base_id)) is not None:
                attributes["base_name"] = base.name
        if person := collar.connected_person:
            attributes["person"] = person
        if collar.signal_strength is not None:
            attributes["signal_strength"] = collar.signal_strength
        return attributes


class PetSignalSensor(TryFiPetEntity, SensorEntity):
    """Cellular signal, when the collar last connected over cellular."""

    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: TryFiDataUpdateCoordinator, pet: Pet) -> None:
        super().__init__(coordinator, pet, "signal-strength", "signal_strength")

    @property
    def native_value(self) -> int | None:
        return self.collar.signal_strength


class PetStatsSensor(TryFiPetEntity, SensorEntity):
    """Steps, distance, sleep or nap over the current day, week or month."""

    # Each total climbs through its period and drops back at the start of the
    # next, which is the shape total_increasing describes: Home Assistant reads
    # the drop as a new cycle rather than as a fall.
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(
        self,
        coordinator: TryFiDataUpdateCoordinator,
        pet: Pet,
        stat_type: str,
        stat_time: str,
    ) -> None:
        period, kind = stat_time.lower(), stat_type.lower()
        super().__init__(coordinator, pet, f"{period}-{kind}", f"{period}_{kind}")
        self._stat = _STATS[stat_type]
        self._period = period
        self._attr_native_unit_of_measurement = self._stat.unit
        self._attr_device_class = self._stat.device_class
        self._attr_suggested_display_precision = self._stat.precision
        # Today's figures are the useful ones. The weekly and monthly totals
        # start disabled on a new install; entities that already exist keep
        # whatever they had.
        self._attr_entity_registry_enabled_default = period == "daily"

    @property
    def native_value(self) -> float | None:
        # Absent or None when TryFi did not report the period: unknown, never a
        # false 0, which statistics would count as a reset.
        value = self._stat.read(self.pet).get(self._period)
        if value is None:
            return None
        if self._stat.divisor is None:
            return float(value) if not isinstance(value, int) else value
        return float(value) / self._stat.divisor


class TryFiBatterySensor(TryFiPetEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: TryFiDataUpdateCoordinator, pet: Pet) -> None:
        super().__init__(coordinator, pet, "battery", "collar_battery_level")

    @property
    def native_value(self) -> int | None:
        return self.collar.battery_percent
