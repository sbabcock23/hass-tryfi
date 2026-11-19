"""Translations and icons cover every key the code uses, and agree with each other."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

INTEGRATION = Path(__file__).resolve().parents[1] / "custom_components" / "tryfi"


def _load(name: str) -> dict[str, Any]:
    return json.loads((INTEGRATION / name).read_text())  # type: ignore[no-any-return]


def test_english_matches_strings_for_every_entity() -> None:
    assert _load("strings.json")["entity"] == _load("translations/en.json")["entity"]


def test_every_named_entity_has_an_icon_or_a_device_class() -> None:
    icons = {
        key for platform in _load("icons.json")["entity"].values() for key in platform
    }
    # These take their icon from the device class.
    by_device_class = {"collar_battery_level", "collar_battery_charging"}
    names = {
        key
        for platform in _load("translations/en.json")["entity"].values()
        for key in platform
    }
    assert names - by_device_class <= icons


def test_enum_states_are_translated() -> None:
    from custom_components.tryfi.sensor import ACTIVITY_STATES, CONNECTION_STATES

    sensors = _load("translations/en.json")["entity"]["sensor"]
    assert set(sensors["activity_type"]["state"]) == set(ACTIVITY_STATES.values())
    assert set(sensors["connected_to"]["state"]) == set(CONNECTION_STATES.values())
