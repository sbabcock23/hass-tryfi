"""Review of c2adf91: an entry without a usable id is not proof of absence.

A pet or base TryFi lists without an id cannot be matched to its device, so
the listing it is in cannot show that device is gone. Each of these used to
leave the listing complete and delete the device, and the user's entity ids
with it.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest
from fakes import BASE_ID, PET_ID, FakeCloud
from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.tryfi.const import DOMAIN


async def _poll(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    freezer.tick(timedelta(seconds=61))
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)


def _identifiers(hass: HomeAssistant, entry: MockConfigEntry) -> set[str]:
    return {
        value
        for device in dr.async_entries_for_config_entry(
            dr.async_get(hass), entry.entry_id
        )
        for domain, value in device.identifiers
        if domain == DOMAIN
    }


@pytest.mark.parametrize(
    "change",
    [
        {"pet_missing": {"id"}},
        {"pet_overrides": {"id": None}},
        {"pet_overrides": {"id": ""}},
        {"base_missing": {"baseId"}},
        {"base_overrides": {"baseId": None}},
        {"base_overrides": {"baseId": ""}},
    ],
    ids=lambda change: repr(change),
)
async def test_an_entry_without_an_id_removes_nothing(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    loaded: FakeCloud,
    freezer: FrozenDateTimeFactory,
    change: dict[str, Any],
) -> None:
    assert _identifiers(hass, entry) == {PET_ID, BASE_ID}
    for attribute, value in change.items():
        setattr(loaded, attribute, value)
    await _poll(hass, freezer)
    assert _identifiers(hass, entry) == {PET_ID, BASE_ID}


async def test_a_numeric_id_matches_its_device(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    cloud: FakeCloud,
    freezer: FrozenDateTimeFactory,
) -> None:
    # The same base, its id sent as a number one time and text the next, is
    # still the same base: ids are compared as text.
    cloud.base_overrides = {"baseId": 1234}
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert "1234" in _identifiers(hass, entry)
    cloud.base_overrides = {"baseId": "1234"}
    await _poll(hass, freezer)
    assert "1234" in _identifiers(hass, entry)
    assert hass.states.get("sensor.kitchen_base").state == "Online"
