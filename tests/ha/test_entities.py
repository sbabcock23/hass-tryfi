"""Entities, as Home Assistant records and shows them."""

from __future__ import annotations

import json
import logging
from datetime import timedelta
from pathlib import Path

import pytest
from fakes import BASE_ID, PET_ID, FakeCloud
from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_UNKNOWN, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

# Every unique id upstream 0.0.26 created for one pet and one base, in its own
# formats. If one of these changes, the entity behind it is orphaned and a new
# one appears with a _2 suffix, breaking every automation that named it.
UPSTREAM_UNIQUE_IDS = {
    f"{PET_ID}-tracker",
    f"{PET_ID}-battery",
    f"{PET_ID}-battery-charging",
    f"{PET_ID}-light",
    f"{PET_ID}-lost",
    *(
        f"{PET_ID}-{period}-{stat}"
        for period in ("daily", "weekly", "monthly")
        for stat in ("steps", "distance", "sleep", "nap")
    ),
    f"{PET_ID}-activity-type",
    f"{PET_ID}-current-place-name",
    f"{PET_ID}-current-place-address",
    f"{PET_ID}-connected-to",
    BASE_ID,
}

# The entity ids upstream's names produced for a pet called Biscuit and a base
# called Kitchen Base. A fresh install has to land on the same ones.
UPSTREAM_ENTITY_IDS = {
    "device_tracker.biscuit_tracker",
    "sensor.biscuit_collar_battery_level",
    "binary_sensor.biscuit_collar_battery_charging",
    "light.biscuit_collar_light",
    "select.biscuit_lost_mode",
    *(
        f"sensor.biscuit_{period}_{stat}"
        for period in ("daily", "weekly", "monthly")
        for stat in ("steps", "distance", "sleep", "nap")
    ),
    "sensor.biscuit_activity_type",
    "sensor.biscuit_current_place_name",
    "sensor.biscuit_current_place_address",
    "sensor.biscuit_connected_to",
    "sensor.kitchen_base",
}


ICONS = json.loads(
    (Path(__file__).parents[2] / "custom_components/tryfi/icons.json").read_text()
)["entity"]


async def _advance(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    """Move the clock past one polling interval and let the refresh run."""
    freezer.tick(timedelta(seconds=61))
    async_fire_time_changed(hass)
    # The coordinator's timed refresh runs as a background task, which the
    # plain wait does not cover: without this the assertions raced it.
    await hass.async_block_till_done(wait_background_tasks=True)


def _registry(hass: HomeAssistant, entry: MockConfigEntry) -> list[er.RegistryEntry]:
    return er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)


async def test_unique_ids_and_entity_ids_match_upstream(
    hass: HomeAssistant, entry: MockConfigEntry, loaded: FakeCloud
) -> None:
    by_unique = {e.unique_id: e.entity_id for e in _registry(hass, entry)}
    # The upstream set, plus the one new sensor 0.1.0 adds.
    assert set(by_unique) == UPSTREAM_UNIQUE_IDS | {f"{PET_ID}-signal-strength"}
    assert {by_unique[u] for u in UPSTREAM_UNIQUE_IDS} == UPSTREAM_ENTITY_IDS


async def test_every_entity_has_a_translated_name(
    hass: HomeAssistant, entry: MockConfigEntry, loaded: FakeCloud
) -> None:
    english = json.loads(
        (
            Path(__file__).parents[2] / "custom_components/tryfi/translations/en.json"
        ).read_text()
    )["entity"]
    for registered in _registry(hass, entry):
        key = registered.translation_key
        assert key in english[registered.domain], registered.entity_id
        icons_or_class = key in ICONS.get(registered.domain, {}) or (
            registered.original_device_class is not None
        )
        assert icons_or_class, registered.entity_id


async def test_friendly_names(hass: HomeAssistant, loaded: FakeCloud) -> None:
    def name(entity_id: str) -> str:
        return str(hass.states.get(entity_id).attributes["friendly_name"])

    assert name("sensor.biscuit_daily_steps") == "Biscuit Daily steps"
    assert name("light.biscuit_collar_light") == "Biscuit Collar light"
    assert name("sensor.kitchen_base") == "Kitchen Base"


async def test_an_existing_entity_keeps_its_id_and_stays_enabled(
    hass: HomeAssistant, entry: MockConfigEntry, cloud: FakeCloud
) -> None:
    # Registry entries left by upstream: one the user renamed, and a monthly
    # stat, which a new install would create disabled.
    registry = er.async_get(hass)
    registry.async_get_or_create(
        "device_tracker",
        "tryfi",
        f"{PET_ID}-tracker",
        config_entry=entry,
        suggested_object_id="renamed_tracker",
    )
    registry.async_get_or_create(
        "sensor",
        "tryfi",
        f"{PET_ID}-monthly-steps",
        config_entry=entry,
        suggested_object_id="biscuit_monthly_steps",
    )
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get("device_tracker.renamed_tracker") is not None
    assert hass.states.get("device_tracker.biscuit_tracker") is None
    assert hass.states.get("sensor.biscuit_monthly_steps").state == "120000"


async def test_new_installs_start_with_the_daily_stats_only(
    hass: HomeAssistant, entry: MockConfigEntry, loaded: FakeCloud
) -> None:
    disabled = {e.unique_id for e in _registry(hass, entry) if e.disabled_by}
    assert disabled == {
        *(
            f"{PET_ID}-{period}-{stat}"
            for period in ("weekly", "monthly")
            for stat in ("steps", "distance", "sleep", "nap")
        ),
        f"{PET_ID}-signal-strength",
    }


async def test_diagnostic_entities(
    hass: HomeAssistant, entry: MockConfigEntry, loaded: FakeCloud
) -> None:
    diagnostic = {
        e.unique_id
        for e in _registry(hass, entry)
        if e.entity_category is EntityCategory.DIAGNOSTIC
    }
    assert diagnostic == {
        f"{PET_ID}-battery",
        f"{PET_ID}-battery-charging",
        f"{PET_ID}-connected-to",
        f"{PET_ID}-signal-strength",
    }


async def test_statistics_sensors(hass: HomeAssistant, loaded: FakeCloud) -> None:
    battery = hass.states.get("sensor.biscuit_collar_battery_level")
    assert battery.state == "87"
    assert battery.attributes["state_class"] == "measurement"
    assert battery.attributes["device_class"] == "battery"
    assert battery.attributes["unit_of_measurement"] == "%"

    steps = hass.states.get("sensor.biscuit_daily_steps")
    assert steps.state == "4321"
    assert steps.attributes["state_class"] == "total_increasing"
    assert steps.attributes["unit_of_measurement"] == "steps"

    distance = hass.states.get("sensor.biscuit_daily_distance")
    assert float(distance.state) == pytest.approx(3.456)
    assert distance.attributes["state_class"] == "total_increasing"
    assert distance.attributes["device_class"] == "distance"
    assert distance.attributes["unit_of_measurement"] == "km"

    sleep = hass.states.get("sensor.biscuit_daily_sleep")
    assert float(sleep.state) == pytest.approx(500.0)
    assert sleep.attributes["state_class"] == "total_increasing"
    assert sleep.attributes["device_class"] == "duration"
    assert sleep.attributes["unit_of_measurement"] == "min"

    assert float(hass.states.get("sensor.biscuit_daily_nap").state) == 50.0

    # Minutes shown whole and kilometres to two places, without rounding what
    # is recorded.
    registry = er.async_get(hass)
    sleep_options = registry.async_get("sensor.biscuit_daily_sleep").options
    assert sleep_options["sensor"]["suggested_display_precision"] == 0
    distance_options = registry.async_get("sensor.biscuit_daily_distance").options
    assert distance_options["sensor"]["suggested_display_precision"] == 2


async def test_activity_and_place(hass: HomeAssistant, loaded: FakeCloud) -> None:
    activity = hass.states.get("sensor.biscuit_activity_type")
    assert activity.state == "resting"
    assert activity.attributes["options"] == ["resting", "walking"]
    assert hass.states.get("sensor.biscuit_current_place_name").state == "Home"
    address = hass.states.get("sensor.biscuit_current_place_address")
    assert address.state == "1 Example Road"
    assert hass.states.get("sensor.kitchen_base").state == "Online"


async def test_walking(
    hass: HomeAssistant, loaded: FakeCloud, freezer: FrozenDateTimeFactory
) -> None:
    loaded.location_mode = "walk"
    await _advance(hass, freezer)
    assert hass.states.get("sensor.biscuit_activity_type").state == "walking"
    place = hass.states.get("sensor.biscuit_current_place_name")
    assert place.state == STATE_UNKNOWN
    tracker = hass.states.get("device_tracker.biscuit_tracker")
    assert tracker.attributes["latitude"] == pytest.approx(10.101)


@pytest.mark.parametrize(
    ("typename", "state", "attributes"),
    [
        ("ConnectedToBase", "base", {"base_id": BASE_ID, "base_name": "Kitchen Base"}),
        ("ConnectedToWifi", "wifi", {}),
        ("ConnectedToCellular", "cellular", {"signal_strength": 70}),
        ("ConnectedToUser", "phone", {"person": "Sam"}),
        ("UnknownConnectivity", STATE_UNKNOWN, {}),
        ("SomethingTryFiAddsLater", STATE_UNKNOWN, {}),
    ],
)
async def test_connection(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    cloud: FakeCloud,
    typename: str,
    state: str,
    attributes: dict[str, object],
) -> None:
    cloud.connection = typename
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    sensor = hass.states.get("sensor.biscuit_connected_to")
    assert sensor.state == state
    assert sensor.attributes["options"] == ["base", "wifi", "cellular", "phone"]
    detail = {
        key: value
        for key, value in sensor.attributes.items()
        if key in {"base_id", "base_name", "person", "signal_strength"}
    }
    assert detail == attributes


async def test_a_connection_to_an_unlisted_base_has_no_name(
    hass: HomeAssistant, entry: MockConfigEntry, cloud: FakeCloud
) -> None:
    cloud.connection = "ConnectedToBase"
    cloud.base_missing = {"baseId"}
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    sensor = hass.states.get("sensor.biscuit_connected_to")
    assert sensor.attributes["base_id"] == BASE_ID
    assert "base_name" not in sensor.attributes


async def test_signal_strength_sensor(
    hass: HomeAssistant, entry: MockConfigEntry, cloud: FakeCloud
) -> None:
    er.async_get(hass).async_get_or_create(
        "sensor",
        "tryfi",
        f"{PET_ID}-signal-strength",
        config_entry=entry,
        suggested_object_id="biscuit_collar_signal_strength",
    )
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    signal = hass.states.get("sensor.biscuit_collar_signal_strength")
    assert signal.state == "70"
    assert signal.attributes["unit_of_measurement"] == "%"


async def test_charging(
    hass: HomeAssistant, loaded: FakeCloud, freezer: FrozenDateTimeFactory
) -> None:
    sensor = "binary_sensor.biscuit_collar_battery_charging"
    assert hass.states.get(sensor).state == "off"
    loaded.charging = True
    await _advance(hass, freezer)
    assert hass.states.get(sensor).state == "on"


async def test_tracker(hass: HomeAssistant, loaded: FakeCloud) -> None:
    state = hass.states.get("device_tracker.biscuit_tracker")
    assert state.attributes["latitude"] == pytest.approx(10.001)
    assert state.attributes["longitude"] == pytest.approx(20.002)
    assert state.attributes["source_type"] == "gps"
    assert state.attributes["entity_picture"] == "https://example.com/p.jpg"
    # Not on the tracker any more; the battery sensor carries it.
    assert "battery_level" not in state.attributes


async def test_tracker_without_a_fix_is_unknown_not_an_error(
    hass: HomeAssistant,
    loaded: FakeCloud,
    caplog: pytest.LogCaptureFixture,
    freezer: FrozenDateTimeFactory,
) -> None:
    loaded.has_location = False
    await _advance(hass, freezer)

    state = hass.states.get("device_tracker.biscuit_tracker")
    assert state.state == STATE_UNKNOWN
    assert "latitude" not in state.attributes
    assert not [r for r in caplog.records if r.levelno >= logging.ERROR]


async def test_a_collar_reporting_less_shows_unknown_not_errors(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    cloud: FakeCloud,
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Upstream #69 and #100: an AttributeError on every refresh.
    cloud.device_missing = {"operationParams", "ledColor", "info"}
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get("select.biscuit_lost_mode").state == STATE_UNKNOWN
    assert hass.states.get("light.biscuit_collar_light").state == STATE_UNKNOWN
    battery = hass.states.get("sensor.biscuit_collar_battery_level")
    assert battery.state == STATE_UNKNOWN
    assert not [r for r in caplog.records if r.levelno >= logging.ERROR]


async def test_a_collarless_pet_does_not_hide_the_collared_one(
    hass: HomeAssistant, entry: MockConfigEntry, cloud: FakeCloud
) -> None:
    # Upstream's "only the bases show up".
    cloud.extra_pets = [{"id": "pet-nano", "name": "Whiskers", "device": None}]
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get("device_tracker.biscuit_tracker") is not None
    assert hass.states.get("sensor.kitchen_base") is not None


async def test_new_readings_arrive_on_the_next_poll(
    hass: HomeAssistant, loaded: FakeCloud, freezer: FrozenDateTimeFactory
) -> None:
    loaded.daily_steps = 5000
    loaded.base_online = False
    await _advance(hass, freezer)
    assert hass.states.get("sensor.biscuit_daily_steps").state == "5000"
    assert hass.states.get("sensor.kitchen_base").state == "Offline"


async def test_a_base_without_a_status_is_unknown(
    hass: HomeAssistant, loaded: FakeCloud, freezer: FrozenDateTimeFactory
) -> None:
    loaded.base_missing = {"online"}
    await _advance(hass, freezer)
    assert hass.states.get("sensor.kitchen_base").state == STATE_UNKNOWN


async def test_loads_without_warnings(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    cloud: FakeCloud,
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Home Assistant reports deprecated usage by logging a warning that names
    # the integration, so a clean log is the check that none is left.
    caplog.set_level(logging.WARNING)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED

    noisy = [
        record.getMessage()
        for record in caplog.records
        if record.levelno >= logging.WARNING
        and "tryfi" in f"{record.name} {record.getMessage()}"
        # Logged for every custom integration, whatever it does.
        and not record.getMessage().startswith("We found a custom integration")
    ]
    assert noisy == []
