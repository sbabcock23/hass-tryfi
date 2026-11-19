"""The collar's LED."""

from __future__ import annotations

import math
from typing import Any

from homeassistant.components.light import ATTR_RGB_COLOR, ColorMode, LightEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .client import Pet
from .coordinator import TryFiConfigEntry, TryFiDataUpdateCoordinator
from .entity import TryFiPetEntity, async_add_per_pet

RGB = tuple[int, int, int]

# TryFi's code for white, used when the collar offers no colours to match.
_WHITE = 8

# One command at a time to a collar.
PARALLEL_UPDATES = 1


def hex_to_rgb(hex_color: str) -> RGB:
    """Turn "#RRGGBB" or "RRGGBB" into a tuple of three ints."""
    hex_color = hex_color.lstrip("#")
    return (
        int(hex_color[0:2], 16),
        int(hex_color[2:4], 16),
        int(hex_color[4:6], 16),
    )


def find_closest_color_code(target: RGB, colors: dict[int, RGB]) -> int:
    """The collar's code for whichever of its colours is nearest the target."""
    return min(
        colors,
        key=lambda code: math.dist(target, colors[code]),
        default=_WHITE,
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TryFiConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_per_pet(
        entry, async_add_entities, lambda pet: [TryFiPetLight(coordinator, pet)]
    )


class TryFiPetLight(TryFiPetEntity, LightEntity):
    _attr_color_mode = ColorMode.RGB
    _attr_supported_color_modes = {ColorMode.RGB}

    def __init__(self, coordinator: TryFiDataUpdateCoordinator, pet: Pet) -> None:
        super().__init__(coordinator, pet, "light", "collar_light")
        self._color_map = {
            color.code: hex_to_rgb(color.hex)
            for color in pet.collar.available_led_colors
        }

    @property
    def is_on(self) -> bool | None:
        # None, shown as unknown, when the collar did not report its LED.
        return self.collar.led_on

    @property
    def rgb_color(self) -> RGB | None:
        color = self.collar.led_color_hex
        return hex_to_rgb(color) if color else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        pet = self.pet
        changes = [lambda: self.client.async_set_led(pet, True)]
        # Only present when the colour was changed; a brightness change, which
        # the collar cannot do anyway, arrives without it.
        if ATTR_RGB_COLOR in kwargs:
            code = find_closest_color_code(kwargs[ATTR_RGB_COLOR], self._color_map)
            changes.append(lambda: self.client.async_set_led_color(pet, code))
        await self._async_command(*changes)

    async def async_turn_off(self, **kwargs: Any) -> None:
        pet = self.pet
        await self._async_command(lambda: self.client.async_set_led(pet, False))
