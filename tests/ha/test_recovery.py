"""Recovering from a failed refresh without a reload (upstream #56, #91, #104)."""

from __future__ import annotations

from datetime import timedelta

from fakes import FakeCloud
from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

BATTERY = "sensor.biscuit_collar_battery_level"


async def _poll(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    freezer.tick(timedelta(seconds=61))
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)


async def test_a_lapsed_session_signs_in_again_and_carries_on(
    hass: HomeAssistant, loaded: FakeCloud, freezer: FrozenDateTimeFactory
) -> None:
    loaded.graphql_errors = True
    loaded.battery = 55
    original = loaded.query

    def recover_after_sign_in(text: str):  # type: ignore[no-untyped-def]
        # TryFi answers again once there has been a fresh sign-in.
        if loaded.requests.count("login") > 1:
            loaded.graphql_errors = False
        return original(text)

    loaded.query = recover_after_sign_in  # type: ignore[method-assign]
    await _poll(hass, freezer)

    assert loaded.requests.count("login") == 2
    assert hass.states.get(BATTERY).state == "55"
    # Signed in afresh: the lapsed session cookie is gone first.
    assert loaded.sessions[0].cookie_jar.cleared == 2
    assert not loaded.sessions[0].closed


async def test_an_outage_marks_entities_unavailable_then_recovers(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    loaded: FakeCloud,
    freezer: FrozenDateTimeFactory,
) -> None:
    loaded.graphql_down = True
    await _poll(hass, freezer)
    assert hass.states.get(BATTERY).state == STATE_UNAVAILABLE
    # One sign-in for the failed poll, not a burst.
    assert loaded.requests.count("login") == 2

    loaded.graphql_down = False
    await _poll(hass, freezer)
    assert hass.states.get(BATTERY).state == "87"
    assert entry.state is ConfigEntryState.LOADED


async def test_an_unreachable_sign_in_marks_entities_unavailable(
    hass: HomeAssistant, loaded: FakeCloud, freezer: FrozenDateTimeFactory
) -> None:
    loaded.graphql_down = True
    loaded.login_mode = "unreachable"
    await _poll(hass, freezer)
    assert hass.states.get(BATTERY).state == STATE_UNAVAILABLE
    assert not hass.config_entries.flow.async_progress()


async def test_a_changed_password_mid_run_asks_for_the_new_one(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    loaded: FakeCloud,
    freezer: FrozenDateTimeFactory,
) -> None:
    loaded.graphql_errors = True
    loaded.password = "changed-in-the-app"
    await _poll(hass, freezer)

    flows = hass.config_entries.flow.async_progress()
    assert [flow["context"]["source"] for flow in flows] == ["reauth"]
