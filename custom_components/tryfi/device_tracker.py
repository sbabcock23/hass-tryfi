"""Where each pet's collar last reported itself."""

from __future__ import annotations

# From the package, not from .config_entry: that path is deprecated and goes
# in 2027.6 (upstream sbabcock23/hass-tryfi#109).
from homeassistant.components.device_tracker import SourceType, TrackerEntity
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
        entry, async_add_entities, lambda pet: [TryFiPetTracker(coordinator, pet)]
    )


class TryFiPetTracker(TryFiPetEntity, TrackerEntity):
    # Battery is not reported here: battery_level on a tracker is unsupported
    # from 2027.7, and the collar battery already has its own sensor.

    # Trackers default to the diagnostic category, which files the pet's
    # location at the bottom of its device page under housekeeping. Where the
    # pet is, is the point.
    # Core types the attribute without None, though Entity reads it as optional.
    _attr_entity_category = None  # type: ignore[assignment]

    def __init__(self, coordinator: TryFiDataUpdateCoordinator, pet: Pet) -> None:
        super().__init__(coordinator, pet, "tracker", "tracker")

    @property
    def entity_picture(self) -> str | None:
        # Read even while the entity is unavailable, so it has to cope with
        # the pet having gone.
        pet = self._lookup()
        return pet.photo_url if pet is not None else None

    @property
    def latitude(self) -> float | None:
        # None until the collar has a fix. Upstream returned float(None) here,
        # which raised on every update for a pet with no location yet.
        return self.pet.latitude

    @property
    def longitude(self) -> float | None:
        return self.pet.longitude

    @property
    def source_type(self) -> SourceType:
        return SourceType.GPS
