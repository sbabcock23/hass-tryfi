"""Stale devices, reconfiguration, discovery and translated errors."""

from __future__ import annotations

from datetime import timedelta

from fakes import BASE_ID, PET_ID, FakeCloud
from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import SOURCE_BLUETOOTH, ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.service_info.bluetooth import BluetoothServiceInfo
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.tryfi import async_remove_config_entry_device
from custom_components.tryfi.const import DOMAIN

TRACKER = "device_tracker.biscuit_tracker"
FI_COLLAR = BluetoothServiceInfo(
    name="Fi-EXAMPLE0001",
    address="AA:BB:CC:DD:EE:FF",
    rssi=-60,
    manufacturer_data={},
    service_data={},
    service_uuids=["57b40001-2528-d6bc-b043-b49af0ec06c1"],
    source="local",
)


async def _poll(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    freezer.tick(timedelta(seconds=61))
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)


def _device(hass: HomeAssistant, identifier: str) -> dr.DeviceEntry | None:
    # Not async_get_device: deprecated from 2026.10, while its replacement does
    # not exist on 2025.1. The entries' own device lists work on both.
    for entry in hass.config_entries.async_entries(DOMAIN):
        for device in dr.async_entries_for_config_entry(
            dr.async_get(hass), entry.entry_id
        ):
            if (DOMAIN, identifier) in device.identifiers:
                return device
    return None


# ------------------------------------------------------------ stale devices
async def test_a_pet_leaving_the_account_is_removed_and_can_return(
    hass: HomeAssistant, loaded: FakeCloud, freezer: FrozenDateTimeFactory
) -> None:
    loaded.pet_present = False
    await _poll(hass, freezer)
    assert _device(hass, PET_ID) is None
    assert hass.states.get(TRACKER) is None
    assert er.async_get(hass).async_get(TRACKER) is None
    assert hass.states.get("sensor.kitchen_base") is not None

    loaded.pet_present = True
    await _poll(hass, freezer)
    assert _device(hass, PET_ID) is not None
    assert hass.states.get(TRACKER) is not None


async def test_a_base_leaving_the_account_is_removed(
    hass: HomeAssistant, loaded: FakeCloud, freezer: FrozenDateTimeFactory
) -> None:
    loaded.base_present = False
    await _poll(hass, freezer)
    assert _device(hass, BASE_ID) is None
    assert _device(hass, PET_ID) is not None


async def test_a_base_described_without_an_id_is_not_taken_as_gone(
    hass: HomeAssistant, loaded: FakeCloud, freezer: FrozenDateTimeFactory
) -> None:
    # Unreadable is not absent: the listing is incomplete, so nothing goes.
    loaded.base_missing = {"baseId"}
    await _poll(hass, freezer)
    assert _device(hass, BASE_ID) is not None


async def test_a_pet_whose_collar_comes_off_stays_until_deleted(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    loaded: FakeCloud,
    freezer: FrozenDateTimeFactory,
) -> None:
    # Still on the account, so it may come back: unavailable, not removed.
    loaded.pet_overrides = {"device": None}
    await _poll(hass, freezer)
    device = _device(hass, PET_ID)
    assert device is not None
    assert hass.states.get(TRACKER).state == STATE_UNAVAILABLE
    # And the delete button works for it, but not for a device still reporting.
    assert await async_remove_config_entry_device(hass, entry, device)
    base = _device(hass, BASE_ID)
    assert base is not None
    assert not await async_remove_config_entry_device(hass, entry, base)


async def test_an_empty_account_answer_removes_nothing(
    hass: HomeAssistant, loaded: FakeCloud, freezer: FrozenDateTimeFactory
) -> None:
    loaded.pet_present = False
    loaded.base_present = False
    await _poll(hass, freezer)
    assert _device(hass, PET_ID) is not None
    assert _device(hass, BASE_ID) is not None


# -------------------------------------------------------------- reconfigure
async def _reconfigure(
    hass: HomeAssistant, entry: MockConfigEntry, username: str, password: str
) -> dict[str, object]:
    result = await entry.start_reconfigure_flow(hass)
    assert result["type"] is FlowResultType.FORM
    return await hass.config_entries.flow.async_configure(  # type: ignore[return-value]
        result["flow_id"], {"username": username, "password": password}
    )


async def test_reconfigure_changes_the_login_of_the_same_account(
    hass: HomeAssistant, entry: MockConfigEntry, loaded: FakeCloud
) -> None:
    loaded.password = "new-password"
    result = await _reconfigure(hass, entry, "renamed@example.com", "new-password")
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data["username"] == "renamed@example.com"
    assert entry.data["password"] == "new-password"
    assert entry.title == "renamed@example.com"
    assert entry.state is ConfigEntryState.LOADED


async def test_reconfigure_refuses_a_different_account(
    hass: HomeAssistant, entry: MockConfigEntry, loaded: FakeCloud
) -> None:
    result = await _reconfigure(hass, entry, "other@example.com", "correct-horse")
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "wrong_account"
    assert entry.data["username"] == "someone@example.com"


async def test_reconfigure_reports_a_wrong_password(
    hass: HomeAssistant, entry: MockConfigEntry, loaded: FakeCloud
) -> None:
    result = await _reconfigure(hass, entry, "someone@example.com", "wrong")
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


# ---------------------------------------------------------------- discovery
async def test_a_collar_heard_over_bluetooth_leads_to_sign_in(
    hass: HomeAssistant, cloud: FakeCloud
) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_BLUETOOTH}, data=FI_COLLAR
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "bluetooth_confirm"

    # Another collar in range does not start a second discovery.
    second = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_BLUETOOTH}, data=FI_COLLAR
    )
    assert second["type"] is FlowResultType.ABORT
    assert second["reason"] == "already_in_progress"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["step_id"] == "user"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"username": "someone@example.com", "password": "correct-horse", "polling": 60},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == "user-0001"


async def test_no_discovery_once_an_account_is_set_up(
    hass: HomeAssistant, entry: MockConfigEntry, cloud: FakeCloud
) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_BLUETOOTH}, data=FI_COLLAR
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


# ---------------------------------------------------------- translated errors
async def test_setup_errors_are_translated(
    hass: HomeAssistant, entry: MockConfigEntry, cloud: FakeCloud
) -> None:
    cloud.login_mode = "unreachable"
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_RETRY
    assert entry.error_reason_translation_key == "cannot_connect"


async def test_update_errors_are_translated(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    loaded: FakeCloud,
    freezer: FrozenDateTimeFactory,
) -> None:
    loaded.graphql_down = True
    await _poll(hass, freezer)
    error = entry.runtime_data.last_exception
    assert error is not None
    assert error.translation_key == "update_failed"
