"""Signing in, re-authenticating, and changing the polling interval."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest
from fakes import FakeCloud
from homeassistant.config_entries import SOURCE_USER, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tryfi.const import DOMAIN

GOOD = {
    "username": "someone@example.com",
    "password": "correct-horse",
    "polling": 120,
}


async def _start(hass: HomeAssistant) -> dict[str, Any]:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    return result  # type: ignore[return-value]


async def test_a_good_sign_in_creates_the_entry(
    hass: HomeAssistant, cloud: FakeCloud
) -> None:
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], GOOD)
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "someone@example.com"
    assert result["data"] == GOOD
    # The session opened to check the password is not left behind.
    assert cloud.sessions[0].detached


@pytest.mark.parametrize(
    ("mode", "password", "error"),
    [
        ("ok", "wrong", "invalid_auth"),
        ("reject_body", "correct-horse", "invalid_auth"),
        ("unreachable", "correct-horse", "cannot_connect"),
    ],
)
async def test_a_failed_sign_in_says_why(
    hass: HomeAssistant, cloud: FakeCloud, mode: str, password: str, error: str
) -> None:
    # Upstream accepted a wrong password and created an entry that then
    # retried for ever.
    cloud.login_mode = mode
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**GOOD, "password": password}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}

    # And it can be corrected in the same form.
    cloud.login_mode = "ok"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], GOOD)
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_an_unexpected_error_is_logged_and_reported(
    hass: HomeAssistant, cloud: FakeCloud, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def explode(*_: object) -> None:
        raise RuntimeError("surprise")

    monkeypatch.setattr("custom_components.tryfi.config_flow.async_check", explode)
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], GOOD)
    assert result["errors"] == {"base": "unknown"}


async def test_a_wrong_password_at_startup_asks_for_the_new_one(
    hass: HomeAssistant, entry: MockConfigEntry, cloud: FakeCloud
) -> None:
    # The install steps: change the password in the app, re-enable the entry,
    # and Home Assistant asks for it.
    cloud.password = "changed-in-the-app"
    assert not await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_ERROR

    flows = hass.config_entries.flow.async_progress()
    assert [flow["context"]["source"] for flow in flows] == ["reauth"]
    flow_id = flows[0]["flow_id"]

    result = await hass.config_entries.flow.async_configure(
        flow_id, {"password": "still-wrong"}
    )
    assert result["errors"] == {"base": "invalid_auth"}

    result = await hass.config_entries.flow.async_configure(
        flow_id, {"password": "changed-in-the-app"}
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data["password"] == "changed-in-the-app"
    assert entry.state is ConfigEntryState.LOADED


async def test_an_unreachable_cloud_at_startup_retries(
    hass: HomeAssistant, entry: MockConfigEntry, cloud: FakeCloud
) -> None:
    cloud.login_mode = "unreachable"
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_RETRY
    assert not hass.config_entries.flow.async_progress()


async def test_the_options_form_opens_and_applies_without_a_restart(
    hass: HomeAssistant, entry: MockConfigEntry, loaded: FakeCloud
) -> None:
    # Upstream #113: the form failed to open at all. #79 and #52: what it
    # saved was never read.
    coordinator = entry.runtime_data
    # Upstream's entry held "10"; it is raised to the floor.
    assert coordinator.update_interval == timedelta(seconds=60)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"polling": 300}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {"polling": 300}
    assert entry.state is ConfigEntryState.LOADED
    # Reloaded, so a new coordinator with the new interval.
    assert entry.runtime_data is not coordinator
    assert entry.runtime_data.update_interval == timedelta(seconds=300)


@pytest.mark.parametrize(
    ("data", "options", "seconds"),
    [
        ({"polling": "10"}, {}, 60),
        ({"polling": "132"}, {}, 132),
        ({"polling": "10"}, {"polling": "132"}, 132),
        ({}, {}, 60),
        ({"polling": "not a number"}, {}, 60),
    ],
)
def test_polling_rate(
    data: dict[str, str], options: dict[str, str], seconds: int
) -> None:
    from custom_components.tryfi.coordinator import polling_rate

    entry = MockConfigEntry(domain=DOMAIN, data=data, options=options)
    assert polling_rate(entry) == seconds


async def test_unloading_closes_the_session(
    hass: HomeAssistant, entry: MockConfigEntry, loaded: FakeCloud
) -> None:
    session = loaded.sessions[0]
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED
    assert session.detached
