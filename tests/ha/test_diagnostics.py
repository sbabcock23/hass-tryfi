"""The diagnostics download carries the shape of the data and nothing personal."""

from __future__ import annotations

import json

from fakes import FakeCloud
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tryfi.diagnostics import async_get_config_entry_diagnostics


async def test_diagnostics(
    hass: HomeAssistant, entry: MockConfigEntry, loaded: FakeCloud
) -> None:
    result = await async_get_config_entry_diagnostics(hass, entry)
    text = json.dumps(result, default=str)

    # Everything that identifies the owner, the pet or where they live.
    for secret in (
        "someone@example.com",
        "correct-horse",
        "Biscuit",
        "Kitchen Base",
        "1 Example Road",
        "10.001",
        "20.002",
        "example-wifi",
        "pet-0001",
        "module-0001",
        "https://example.com/p.jpg",
    ):
        assert secret not in text, secret

    assert result["entry"]["polling_seconds"] == 60
    pet = result["pets"][0]
    assert pet["has_position"] is True
    assert pet["at_saved_place"] is True
    assert pet["collar"]["battery_percent"] == 87
    assert pet["collar"]["connection_type"] == "ConnectedToCellular"
    assert pet["stats"]["daily_steps"] == 4321
    assert result["bases"] == [
        {"index": 0, "online": True, "online_quality": "GOOD", "has_position": True}
    ]
