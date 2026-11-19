"""Whether each collar is on charge."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .client import Pet
from .coordinator import TryFiConfigEntry, TryFiDataUpdateCoordinator
from .entity import TryFiPetEntity, async_add_per_pet

# Read-only, and every reading comes from the coordinator's one refresh.
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TryFiConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_per_pet(
        entry,
        async_add_entities,
        lambda pet: [TryFiBatteryChargingBinarySensor(coordinator, pet)],
    )


class TryFiBatteryChargingBinarySensor(TryFiPetEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.BATTERY_CHARGING
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: TryFiDataUpdateCoordinator, pet: Pet) -> None:
        super().__init__(
            coordinator, pet, "battery-charging", "collar_battery_charging"
        )

    @property
    def is_on(self) -> bool:
        return self.collar.charging
