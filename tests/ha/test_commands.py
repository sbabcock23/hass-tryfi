"""The collar light and Lost Mode: what they send, and how fast the UI follows."""

from __future__ import annotations

import pytest
from fakes import MODULE_ID, FakeCloud
from homeassistant.components.light import ATTR_RGB_COLOR
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from custom_components.tryfi.light import find_closest_color_code, hex_to_rgb

LIGHT = "light.biscuit_collar_light"
LOST = "select.biscuit_lost_mode"


async def test_turning_the_light_on_shows_at_once(
    hass: HomeAssistant, loaded: FakeCloud
) -> None:
    # Upstream left the UI a poll behind ("# Fix later"). The state must be
    # right as soon as the service call returns, not after the next poll.
    assert hass.states.get(LIGHT).state == "off"
    await hass.services.async_call(
        "light", "turn_on", {"entity_id": LIGHT}, blocking=True
    )
    assert hass.states.get(LIGHT).state == "on"
    assert loaded.mutations == [{"input": {"moduleId": MODULE_ID, "ledEnabled": True}}]

    await hass.services.async_call(
        "light", "turn_off", {"entity_id": LIGHT}, blocking=True
    )
    assert hass.states.get(LIGHT).state == "off"


async def test_choosing_a_colour_picks_the_nearest_the_collar_has(
    hass: HomeAssistant, loaded: FakeCloud
) -> None:
    await hass.services.async_call(
        "light",
        "turn_on",
        {"entity_id": LIGHT, ATTR_RGB_COLOR: (10, 20, 250)},
        blocking=True,
    )
    assert loaded.mutations[-1] == {"moduleId": MODULE_ID, "ledColorCode": 3}
    state = hass.states.get(LIGHT)
    assert state.attributes["rgb_color"] == (0, 0, 255)


async def test_the_ui_still_follows_when_the_answer_is_empty(
    hass: HomeAssistant, loaded: FakeCloud
) -> None:
    # The mutation answer carries the collar state; when it does not, the
    # refresh requested straight after brings it in.
    loaded.mutations_answer_empty = True
    await hass.services.async_call(
        "light", "turn_on", {"entity_id": LIGHT}, blocking=True
    )
    await hass.async_block_till_done()
    assert hass.states.get(LIGHT).state == "on"


async def test_a_refused_light_command_says_so(
    hass: HomeAssistant, loaded: FakeCloud
) -> None:
    loaded.mutations_fail = True
    with pytest.raises(HomeAssistantError, match="did not accept"):
        await hass.services.async_call(
            "light", "turn_on", {"entity_id": LIGHT}, blocking=True
        )
    assert hass.states.get(LIGHT).state == "off"


async def test_lost_mode_shows_at_once(hass: HomeAssistant, loaded: FakeCloud) -> None:
    # And it is the select service, not input_select (upstream #71).
    assert hass.states.get(LOST).state == "Safe"
    await hass.services.async_call(
        "select", "select_option", {"entity_id": LOST, "option": "Lost"}, blocking=True
    )
    assert hass.states.get(LOST).state == "Lost"
    assert loaded.mutations == [{"input": {"moduleId": MODULE_ID, "mode": "LOST_DOG"}}]

    await hass.services.async_call(
        "select", "select_option", {"entity_id": LOST, "option": "Safe"}, blocking=True
    )
    assert hass.states.get(LOST).state == "Safe"


async def test_a_refused_lost_mode_says_so(
    hass: HomeAssistant, loaded: FakeCloud
) -> None:
    loaded.mutations_fail = True
    with pytest.raises(HomeAssistantError, match="did not accept"):
        await hass.services.async_call(
            "select",
            "select_option",
            {"entity_id": LOST, "option": "Lost"},
            blocking=True,
        )
    assert hass.states.get(LOST).state == "Safe"


def test_colour_helpers() -> None:
    assert hex_to_rgb("#00FF7f") == (0, 255, 127)
    assert hex_to_rgb("FFFFFF") == (255, 255, 255)
    assert (
        find_closest_color_code((250, 0, 240), {1: (255, 0, 255), 3: (0, 0, 255)}) == 1
    )
    # No colours offered: white.
    assert find_closest_color_code((1, 2, 3), {}) == 8
