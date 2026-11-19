"""Lost Mode on the collar."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .client import Pet
from .coordinator import TryFiConfigEntry, TryFiDataUpdateCoordinator
from .entity import TryFiPetEntity, async_add_per_pet

SAFE = "Safe"
LOST = "Lost"

# One command at a time to a collar.
PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TryFiConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_per_pet(
        entry, async_add_entities, lambda pet: [TryFiLostMode(coordinator, pet)]
    )


class TryFiLostMode(TryFiPetEntity, SelectEntity):
    _attr_options = [SAFE, LOST]

    def __init__(self, coordinator: TryFiDataUpdateCoordinator, pet: Pet) -> None:
        super().__init__(coordinator, pet, "lost", "lost_mode")

    @property
    def current_option(self) -> str | None:
        # Unknown, rather than "Safe", when the collar did not report a mode.
        lost = self.collar.is_lost
        if lost is None:
            return None
        return LOST if lost else SAFE

    async def async_select_option(self, option: str) -> None:
        pet = self.pet
        await self._async_command(
            lambda: self.client.async_set_lost_mode(pet, option == LOST)
        )
