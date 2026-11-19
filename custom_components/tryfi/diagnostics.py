"""Diagnostics download: what the integration sees, with nothing personal in it.

Upstream's issues mostly stalled at "please post debug logs". This is the
answer to that: the shape of what TryFi returned for each pet and base, with
every credential, name, place and coordinate removed, so it can be pasted into
a public issue as it is.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .client import Pet
from .client.models import PERIODS
from .const import CONF_PASSWORD, CONF_USERNAME
from .coordinator import TryFiConfigEntry, polling_rate

TO_REDACT = {CONF_USERNAME, CONF_PASSWORD}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: TryFiConfigEntry
) -> dict[str, Any]:
    coordinator = entry.runtime_data
    client = coordinator.data
    return {
        "entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": dict(entry.options),
            "polling_seconds": polling_rate(entry),
        },
        "last_update_success": coordinator.last_update_success,
        "pets_listed": len(client.listed_pet_ids),
        "pets": [_pet(index, pet) for index, pet in enumerate(client.pets)],
        "bases": [
            {
                "index": index,
                "online": base.online,
                "online_quality": base.online_quality,
                "has_position": base.latitude is not None,
            }
            for index, base in enumerate(client.bases)
        ],
    }


def _pet(index: int, pet: Pet) -> dict[str, Any]:
    collar = pet.collar
    stats = {
        f"{period}_{name}": values.get(period)
        for period in PERIODS
        for name, values in (
            ("steps", pet.steps),
            ("distance_m", pet.distance_m),
            ("sleep_s", pet.sleep_s),
            ("nap_s", pet.nap_s),
        )
    }
    return {
        "index": index,
        "breed": pet.breed,
        "activity_type": pet.activity_type,
        "has_position": pet.latitude is not None,
        "at_saved_place": pet.place_name is not None,
        "stats": stats,
        "collar": {
            "build": collar.build_id,
            "battery_percent": collar.battery_percent,
            "charging": collar.charging,
            "mode": collar.mode,
            "led_on": collar.led_on,
            "led_color": collar.led_color_name,
            "led_colors_offered": len(collar.available_led_colors),
            "connection_type": collar.connection_type,
            "connection_signal_percent": collar.signal_strength,
            "connected_to_a_base": collar.connected_base_id is not None,
        },
    }
