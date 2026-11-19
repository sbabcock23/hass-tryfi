"""Findings from the review of ad0329c, each reproduced before it was fixed."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest
from fakes import PET_ID, FakeCloud
from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import SOURCE_USER, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.tryfi import async_remove_config_entry_device
from custom_components.tryfi.client import TryFiClient
from custom_components.tryfi.const import DOMAIN

TRACKER = "device_tracker.biscuit_tracker"


async def _poll(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    freezer.tick(timedelta(seconds=61))
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)


def _device(hass: HomeAssistant, entry: MockConfigEntry) -> dr.DeviceEntry | None:
    for device in dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id):
        if (DOMAIN, PET_ID) in device.identifiers:
            return device
    return None


# [P1] A partial account answer must not delete anything.
async def test_a_partial_account_answer_removes_nothing(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    cloud: FakeCloud,
    freezer: FrozenDateTimeFactory,
) -> None:
    # A renamed tracker: what a removal would destroy for good.
    er.async_get(hass).async_get_or_create(
        "device_tracker",
        DOMAIN,
        f"{PET_ID}-tracker",
        config_entry=entry,
        suggested_object_id="renamed_tracker",
    )
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    cloud.households_partial = True
    await _poll(hass, freezer)
    assert _device(hass, entry) is not None
    assert er.async_get(hass).async_get("device_tracker.renamed_tracker") is not None

    cloud.households_partial = False
    await _poll(hass, freezer)
    assert hass.states.get("device_tracker.renamed_tracker").state != "unavailable"


# [P2] Entries given an email-based unique id by 2b0fb15 move to the user id.
async def test_an_email_unique_id_moves_to_the_user_id(
    hass: HomeAssistant, cloud: FakeCloud
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="someone@example.com",
        unique_id="someone@example.com",
        data={"username": "Someone@Example.com", "password": "correct-horse"},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.unique_id == "user-0001"

    result = await entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"username": "someone@example.com", "password": "correct-horse"},
    )
    assert result["reason"] == "reconfigure_successful"


async def test_a_unique_id_that_is_not_the_email_is_left_alone(
    hass: HomeAssistant, cloud: FakeCloud
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="user-0001",
        data={"username": "someone@example.com", "password": "correct-horse"},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    assert entry.unique_id == "user-0001"


# [P2] Null collar groups leave readings unknown, not the integration unloaded.
@pytest.mark.parametrize("group", ["info", "operationParams", "ledColor"])
async def test_a_null_collar_group_still_loads(
    hass: HomeAssistant, entry: MockConfigEntry, cloud: FakeCloud, group: str
) -> None:
    original = cloud.device

    def device() -> dict[str, Any]:
        described = original()
        described[group] = None
        return described

    cloud.device = device  # type: ignore[method-assign]
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert hass.states.get(TRACKER) is not None


# [P2] A device deleted by hand comes back when its pet does.
async def test_a_device_deleted_by_hand_comes_back(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    loaded: FakeCloud,
    freezer: FrozenDateTimeFactory,
) -> None:
    loaded.pet_overrides = {"device": None}
    await _poll(hass, freezer)
    device = _device(hass, entry)
    assert device is not None
    # What the delete button does: ask the integration, then remove.
    assert await async_remove_config_entry_device(hass, entry, device)
    dr.async_get(hass).async_remove_device(device.id)
    await hass.async_block_till_done()
    assert hass.states.get(TRACKER) is None

    loaded.pet_overrides = {}
    await _poll(hass, freezer)
    # Every platform's entities, not only the first to notice: that one
    # brings the device back, which once hid the pet from the rest.
    for entity_id in (
        TRACKER,
        "light.biscuit_collar_light",
        "select.biscuit_lost_mode",
        "sensor.biscuit_daily_steps",
        "binary_sensor.biscuit_collar_battery_charging",
    ):
        assert hass.states.get(entity_id) is not None, entity_id


# [P2] Home Assistant's sessions are detached, never close()d.
async def test_validating_in_the_flow_detaches_its_session(
    hass: HomeAssistant, cloud: FakeCloud
) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"username": "someone@example.com", "password": "wrong", "polling": 60},
    )
    await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"username": "someone@example.com", "password": "correct-horse", "polling": 60},
    )
    await hass.async_block_till_done()
    flow_sessions = cloud.sessions[:2]
    assert [session.detached for session in flow_sessions] == [True, True]


async def test_a_failed_setup_detaches_its_session(
    hass: HomeAssistant, entry: MockConfigEntry, cloud: FakeCloud
) -> None:
    cloud.login_mode = "unreachable"
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert cloud.sessions[0].detached


async def test_unloading_detaches_the_session(
    hass: HomeAssistant, entry: MockConfigEntry, loaded: FakeCloud
) -> None:
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert loaded.sessions[0].detached


async def test_a_real_home_assistant_session_ends_up_closed(
    hass: HomeAssistant,
) -> None:
    # The fake cannot show this: on a real session from Home Assistant,
    # close() is a wrapper that only warns, so the client must detach.
    session = async_create_clientsession(hass, auto_cleanup=False)
    client = TryFiClient(session, "someone@example.com", "x")
    client.detach()
    assert session.closed
