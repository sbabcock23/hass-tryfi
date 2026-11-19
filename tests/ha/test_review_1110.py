"""Findings from the review of 361088f, each reproduced before it was fixed."""

from __future__ import annotations

from datetime import timedelta

import pytest
from fakes import FakeCloud
from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import SOURCE_USER, ConfigEntryState
from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.tryfi.const import DOMAIN

SLEEP = "sensor.biscuit_daily_sleep"


async def _poll(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    freezer.tick(timedelta(seconds=61))
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)


@pytest.mark.parametrize(
    ("domain", "service", "data", "entity_id", "before"),
    [
        (
            "select",
            "select_option",
            {"option": "Lost"},
            "select.biscuit_lost_mode",
            "Safe",
        ),
        ("light", "turn_on", {}, "light.biscuit_collar_light", "off"),
    ],
)
async def test_a_refused_mutation_is_a_failure(
    hass: HomeAssistant,
    loaded: FakeCloud,
    domain: str,
    service: str,
    data: dict[str, str],
    entity_id: str,
    before: str,
) -> None:
    # TryFi answers {"data": {"updateDeviceOperationParams": null}, "errors":
    # [...]}. The data object is not empty, which slipped past the check.
    loaded.mutations_rejected = True
    with pytest.raises(HomeAssistantError, match="did not accept"):
        await hass.services.async_call(
            domain, service, {"entity_id": entity_id, **data}, blocking=True
        )
    assert hass.states.get(entity_id).state == before


async def test_a_missing_rest_summary_is_unknown_not_a_reset(
    hass: HomeAssistant, loaded: FakeCloud, freezer: FrozenDateTimeFactory
) -> None:
    # Reading 0 here made total_increasing count a reset, and the same 500
    # minutes again when the summary came back.
    assert float(hass.states.get(SLEEP).state) == 500
    loaded.has_rest_stats = False
    await _poll(hass, freezer)
    assert hass.states.get(SLEEP).state == STATE_UNKNOWN
    loaded.has_rest_stats = True
    await _poll(hass, freezer)
    assert float(hass.states.get(SLEEP).state) == 500


async def test_a_pet_that_arrives_after_setup_gets_its_entities(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    cloud: FakeCloud,
    freezer: FrozenDateTimeFactory,
) -> None:
    # Skipped at setup (no collar yet, or a failed first read), then present.
    cloud.pet_present = False
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get("device_tracker.biscuit_tracker") is None

    cloud.pet_present = True
    await _poll(hass, freezer)
    for entity_id in (
        "device_tracker.biscuit_tracker",
        "sensor.biscuit_daily_steps",
        "binary_sensor.biscuit_collar_battery_charging",
        "light.biscuit_collar_light",
        "select.biscuit_lost_mode",
    ):
        assert hass.states.get(entity_id) is not None, entity_id

    # And not a second time on the next refresh.
    await _poll(hass, freezer)
    assert len(hass.states.async_entity_ids("device_tracker")) == 1


async def test_a_base_that_arrives_after_setup_gets_its_entity(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    cloud: FakeCloud,
    freezer: FrozenDateTimeFactory,
) -> None:
    cloud.base_missing = {"baseId"}
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get("sensor.kitchen_base") is None

    cloud.base_missing = set()
    await _poll(hass, freezer)
    assert hass.states.get("sensor.kitchen_base") is not None


@pytest.mark.parametrize(
    ("overrides", "device_missing"),
    [
        ({"weight": None}, set()),
        ({"breed": None, "photos": None, "name": None}, set()),
        ({}, {"lastConnectionState"}),
    ],
)
async def test_optional_profile_fields_cannot_hide_a_pet(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    cloud: FakeCloud,
    overrides: dict[str, object],
    device_missing: set[str],
) -> None:
    cloud.pet_overrides = overrides
    cloud.device_missing = device_missing
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    trackers = hass.states.async_entity_ids("device_tracker")
    assert len(trackers) == 1


async def test_the_same_account_cannot_be_added_twice(
    hass: HomeAssistant, entry: MockConfigEntry, loaded: FakeCloud
) -> None:
    # The fixture's entry is upstream-shaped: no unique id. Setup gives it the
    # account's TryFi user id.
    assert entry.unique_id == "user-0001"

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"username": "Someone@Example.com", "password": "correct-horse", "polling": 60},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1


async def test_an_upstream_entry_not_yet_loaded_still_blocks_a_duplicate(
    hass: HomeAssistant, entry: MockConfigEntry, cloud: FakeCloud
) -> None:
    # Disabled, say, so setup never gave it a unique id.
    assert entry.unique_id is None
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"username": "someone@example.com", "password": "correct-horse", "polling": 60},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_a_second_account_is_still_allowed(
    hass: HomeAssistant, entry: MockConfigEntry, loaded: FakeCloud
) -> None:
    loaded.password = "correct-horse"
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"username": "other@example.com", "password": "correct-horse", "polling": 60},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == "user-other@example.com"
