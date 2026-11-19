"""The TryFi client against the fake cloud: one test per upstream failure.

Each reproduces a report on sbabcock23/hass-tryfi that traced back to the
library rather than the integration, or a finding from review.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

import pytest
from fakes import BASE_ID, MODULE_ID, PET_ID, FakeCloud, FakeSession

from custom_components.tryfi.client import (
    Collar,
    TryFiAuthError,
    TryFiClient,
    TryFiCommandError,
    TryFiConnectionError,
    TryFiError,
)

COLLARLESS = {"id": "pet-nano", "name": "Whiskers", "device": None}


def _client(cloud: FakeCloud, password: str | None = None) -> TryFiClient:
    return TryFiClient(
        FakeSession(cloud),  # type: ignore[arg-type]
        "someone@example.com",
        cloud.password if password is None else password,
    )


async def _signed_in(cloud: FakeCloud) -> TryFiClient:
    client = _client(cloud)
    await client.async_login()
    await client.async_refresh()
    return client


# ---------------------------------------------------------------- signing in
async def test_a_good_sign_in_reads_the_whole_account(cloud: FakeCloud) -> None:
    client = await _signed_in(cloud)
    assert client.user_id == "user-0001"
    assert [pet.pet_id for pet in client.pets] == [PET_ID]
    assert [base.name for base in client.bases] == ["Kitchen Base"]
    # Only what the integration uses: no separate query for the user's
    # profile, which pytryfi made and nothing read.
    assert cloud.requests == ["login", "households", "location", "stats", "rest"]


async def test_signing_in_starts_from_a_clean_cookie_jar(cloud: FakeCloud) -> None:
    client = _client(cloud)
    await client.async_login()
    await client.async_login()
    assert cloud.sessions[0].cookie_jar.cleared == 2


@pytest.mark.parametrize(
    ("mode", "password", "error"),
    [
        ("ok", "wrong", TryFiAuthError),
        # TryFi's 200 with an error body, pytryfi's TryFiLoginError path.
        ("reject_body", None, TryFiAuthError),
        ("reject_401", None, TryFiAuthError),
        ("unreachable", None, TryFiConnectionError),
        ("timeout", None, TryFiConnectionError),
        ("error_500", None, TryFiConnectionError),
    ],
)
async def test_a_failed_sign_in_says_why(
    cloud: FakeCloud, mode: str, password: str | None, error: type[Exception]
) -> None:
    cloud.login_mode = mode
    with pytest.raises(error):
        await _client(cloud, password).async_login()


async def test_a_sign_in_answer_that_is_not_json(cloud: FakeCloud) -> None:
    original = cloud.login

    def garbage(data: dict[str, str]):  # type: ignore[no-untyped-def]
        response = original(data)
        response._body = ValueError("not json")
        return response

    cloud.login = garbage  # type: ignore[method-assign]
    with pytest.raises(TryFiConnectionError):
        await _client(cloud).async_login()


@pytest.mark.parametrize("body", [[], {}, {"userId": None}])
async def test_a_sign_in_answer_without_a_user(cloud: FakeCloud, body: object) -> None:
    original = cloud.login

    def odd(data: dict[str, str]):  # type: ignore[no-untyped-def]
        response = original(data)
        response._body = body
        return response

    cloud.login = odd  # type: ignore[method-assign]
    with pytest.raises(TryFiConnectionError):
        await _client(cloud).async_login()


# ----------------------------------------------------------------- reading
@pytest.mark.parametrize(
    "extra",
    [COLLARLESS, {"id": "pet-shared", "name": "Owl"}],
)
async def test_a_pet_without_a_collar_does_not_hide_the_others(
    cloud: FakeCloud, extra: dict[str, object]
) -> None:
    # #61, #62, #67, #87, #96, #99, #102: "only the bases show up". Upstream
    # compared the device with the string "None" while TryFi sends null.
    cloud.extra_pets = [extra]
    client = await _signed_in(cloud)
    assert [pet.pet_id for pet in client.pets] == [PET_ID]
    # Listed, so not taken for a pet that left the account.
    assert client.listed_pet_ids == {PET_ID, extra["id"]}


async def test_a_pet_that_cannot_be_read_does_not_hide_the_others(
    cloud: FakeCloud,
) -> None:
    # A device with no id is no collar; a pet with no id cannot be read at all.
    cloud.extra_pets = [
        {"id": "pet-odd", "name": "Odd", "device": {"moduleId": "m"}},
        {"name": "Nameless", "device": {"id": "d"}},
    ]
    client = await _signed_in(cloud)
    assert [pet.pet_id for pet in client.pets] == [PET_ID]


@pytest.mark.parametrize(
    "overrides",
    [
        {"weight": None},
        {"breed": None, "photos": None, "name": None},
        {"breed": "not an object", "photos": {"first": None}},
    ],
)
async def test_optional_profile_fields_cannot_hide_a_pet(
    cloud: FakeCloud, overrides: dict[str, object]
) -> None:
    cloud.pet_overrides = overrides
    client = await _signed_in(cloud)
    assert len(client.pets) == 1


@pytest.mark.parametrize(
    "missing",
    [
        "operationParams",
        "ledColor",
        "info",
        "availableLedColors",
        "lastConnectionState",
    ],
)
async def test_a_collar_reporting_less_still_reads(
    cloud: FakeCloud, missing: str
) -> None:
    # #69 `_ledOn`, #100 `_mode`: the first missing field left every later
    # attribute undefined.
    cloud.device_missing = {missing}
    collar = (await _signed_in(cloud)).pets[0].collar
    assert collar.module_id == MODULE_ID
    if missing == "info":
        assert collar.battery_percent is None
    else:
        assert collar.battery_percent == 87


async def test_a_partial_answer_keeps_what_it_leaves_out(cloud: FakeCloud) -> None:
    collar = (await _signed_in(cloud)).pets[0].collar
    collar.update({"moduleId": MODULE_ID})
    assert collar.battery_percent == 87
    assert collar.mode == "NORMAL"


def test_led_state_follows_its_off_time() -> None:
    collar = Collar("device")
    assert collar.led_on is None
    collar.led_enabled = True
    # TryFi still reports an LED it has switched off itself as enabled.
    collar.led_off_at = datetime.now(UTC) - timedelta(minutes=1)
    assert collar.led_on is False
    collar.led_off_at = datetime.now(UTC) + timedelta(minutes=1)
    assert collar.led_on is True
    collar.led_off_at = None
    assert collar.led_on is False
    collar.led_enabled = False
    assert collar.led_on is False
    assert collar.is_lost is None


async def test_a_base_missing_fields_still_loads(cloud: FakeCloud) -> None:
    # #93: a base without infoLastUpdated failed the whole sensor platform.
    cloud.base_missing = {"infoLastUpdated", "position", "name", "networkName"}
    base = (await _signed_in(cloud)).bases[0]
    assert base.base_id == BASE_ID
    assert base.name == BASE_ID
    assert base.latitude is None


async def test_a_base_without_an_id_is_skipped(
    cloud: FakeCloud, caplog: pytest.LogCaptureFixture
) -> None:
    cloud.base_missing = {"baseId"}
    client = await _signed_in(cloud)
    assert client.bases == []
    assert client.listed_base_ids == set()


async def test_resting_somewhere_unsaved(cloud: FakeCloud) -> None:
    cloud.location_mode = "rest_unsaved_place"
    pet = (await _signed_in(cloud)).pets[0]
    assert pet.latitude == pytest.approx(10.001)
    assert pet.place_name is None
    assert pet.activity_start is not None


async def test_a_walk_reads_its_latest_position(cloud: FakeCloud) -> None:
    cloud.location_mode = "walk"
    pet = (await _signed_in(cloud)).pets[0]
    assert pet.activity_type == "OngoingWalk"
    assert pet.latitude == pytest.approx(10.101)
    assert pet.place_name is None


async def test_a_walk_with_no_positions_yet_uses_its_path(cloud: FakeCloud) -> None:
    cloud.location_mode = "walk_no_positions"
    assert (await _signed_in(cloud)).pets[0].latitude == pytest.approx(10.101)


async def test_no_fix_yet_is_no_position(cloud: FakeCloud) -> None:
    cloud.has_location = False
    pet = (await _signed_in(cloud)).pets[0]
    assert pet.activity_type == "OngoingRest"
    assert pet.latitude is None


async def test_a_failed_location_keeps_the_last_one(cloud: FakeCloud) -> None:
    client = await _signed_in(cloud)
    cloud.location_fails = True
    cloud.daily_steps = 9999
    await client.async_refresh()
    pet = client.pets[0]
    assert pet.latitude == pytest.approx(10.001)
    assert pet.place_name == "Home"
    # Only the failed group is carried over; the rest is fresh.
    assert pet.steps["daily"] == 9999


async def test_a_failed_group_on_a_new_pet_is_simply_absent(cloud: FakeCloud) -> None:
    cloud.location_fails = True
    pet = (await _signed_in(cloud)).pets[0]
    assert pet.latitude is None
    assert pet.steps["daily"] == 4321


async def test_rest_missing_is_unknown_and_present_but_empty_is_zero(
    cloud: FakeCloud,
) -> None:
    # A false 0 for a missing summary made total_increasing count a reset.
    cloud.has_rest_stats = False
    pet = (await _signed_in(cloud)).pets[0]
    assert pet.sleep_s == {"daily": None, "weekly": None, "monthly": None}
    original = cloud.rest

    def empty_amounts():  # type: ignore[no-untyped-def]
        body = original()
        body["dailyStat"] = {"restSummaries": [{"data": {"sleepAmounts": []}}]}
        return body

    cloud.has_rest_stats = True
    cloud.rest = empty_amounts  # type: ignore[method-assign]
    client = await _signed_in(cloud)
    assert client.pets[0].sleep_s["daily"] == 0
    assert client.pets[0].nap_s["weekly"] == 20000


async def test_a_failed_account_fetch_raises_and_keeps_the_last_data(
    cloud: FakeCloud,
) -> None:
    # #56, #91: upstream swallowed this and the data silently went stale.
    client = await _signed_in(cloud)
    cloud.graphql_down = True
    with pytest.raises(TryFiConnectionError, match="graphql unreachable"):
        await client.async_refresh()
    assert [pet.pet_id for pet in client.pets] == [PET_ID]


async def test_a_graphql_error_raises_with_its_message(cloud: FakeCloud) -> None:
    client = await _signed_in(cloud)
    cloud.graphql_errors = True
    with pytest.raises(TryFiError, match="Not authenticated"):
        await client.async_refresh()


@pytest.mark.parametrize("body", [[], {"data": None}, {"data": []}])
async def test_an_answer_that_is_not_graphql_raises(
    cloud: FakeCloud, body: object
) -> None:
    from fakes import FakeResponse

    client = await _signed_in(cloud)
    cloud.query = lambda text: FakeResponse(200, body)  # type: ignore[method-assign]
    with pytest.raises(TryFiError):
        await client.async_refresh()


async def test_an_expired_session_is_an_auth_error(cloud: FakeCloud) -> None:
    from fakes import FakeResponse

    client = await _signed_in(cloud)
    cloud.query = lambda text: FakeResponse(401, {})  # type: ignore[method-assign]
    with pytest.raises(TryFiAuthError):
        await client.async_refresh()


async def test_one_households_query_per_refresh(cloud: FakeCloud) -> None:
    client = await _signed_in(cloud)
    cloud.requests.clear()
    await client.async_refresh()
    assert cloud.requests.count("households") == 1


@pytest.mark.parametrize(
    ("typename", "base", "person", "signal"),
    [
        ("ConnectedToBase", BASE_ID, None, None),
        ("ConnectedToUser", None, "Sam", None),
        ("ConnectedToCellular", None, None, 70),
        ("ConnectedToWifi", None, None, None),
        ("UnknownConnectivity", None, None, None),
    ],
)
async def test_connection_detail(
    cloud: FakeCloud,
    typename: str,
    base: str | None,
    person: str | None,
    signal: int | None,
) -> None:
    cloud.connection = typename
    collar = (await _signed_in(cloud)).pets[0].collar
    assert collar.connection_type == typename
    assert collar.connected_base_id == base
    assert collar.connected_person == person
    assert collar.signal_strength == signal


async def test_a_pet_that_left_is_not_an_error(
    cloud: FakeCloud, caplog: pytest.LogCaptureFixture
) -> None:
    client = await _signed_in(cloud)
    assert client.get_pet("gone") is None
    assert client.get_base("gone") is None
    assert not [r for r in caplog.records if r.levelno >= logging.ERROR]


# ---------------------------------------------------------------- changing
async def test_commands_send_what_upstream_sent(cloud: FakeCloud) -> None:
    client = await _signed_in(cloud)
    pet = client.pets[0]
    await client.async_set_led(pet, True)
    await client.async_set_led_color(pet, 3)
    await client.async_set_lost_mode(pet, True)
    await client.async_set_lost_mode(pet, False)
    assert cloud.mutations == [
        {"input": {"moduleId": MODULE_ID, "ledEnabled": True}},
        {"moduleId": MODULE_ID, "ledColorCode": 3},
        {"input": {"moduleId": MODULE_ID, "mode": "LOST_DOG"}},
        {"input": {"moduleId": MODULE_ID, "mode": "NORMAL"}},
    ]
    # Each answer's collar state was taken.
    assert pet.collar.led_on is True
    assert pet.collar.led_color_hex == "#0000FF"
    assert pet.collar.is_lost is False


async def test_a_refused_command_raises(cloud: FakeCloud) -> None:
    client = await _signed_in(cloud)
    cloud.mutations_rejected = True
    with pytest.raises(TryFiCommandError, match="Not allowed"):
        await client.async_set_lost_mode(client.pets[0], True)
    assert client.pets[0].collar.is_lost is False


async def test_an_unreachable_command_raises(cloud: FakeCloud) -> None:
    client = await _signed_in(cloud)
    cloud.mutations_fail = True
    with pytest.raises(TryFiConnectionError):
        await client.async_set_led(client.pets[0], True)


async def test_an_empty_answer_changes_nothing_yet(cloud: FakeCloud) -> None:
    client = await _signed_in(cloud)
    cloud.mutations_answer_empty = True
    await client.async_set_led(client.pets[0], True)
    assert client.pets[0].collar.led_on is False


async def test_a_command_to_a_collar_without_a_module(cloud: FakeCloud) -> None:
    cloud.device_missing = {"moduleId"}
    client = await _signed_in(cloud)
    with pytest.raises(TryFiCommandError):
        await client.async_set_led(client.pets[0], True)
    assert cloud.mutations == []


async def test_detaching_lets_go_of_the_session(cloud: FakeCloud) -> None:
    client = await _signed_in(cloud)
    client.detach()
    assert cloud.sessions[0].detached


@pytest.mark.parametrize("pet_id", [None, "", "  ", True, [], {}])
def test_a_pet_needs_a_usable_id(pet_id: object) -> None:
    from custom_components.tryfi.client import Pet

    with pytest.raises(TypeError):
        Pet.from_profile({"id": pet_id, "device": {"id": "device"}})


@pytest.mark.parametrize(("raw", "expected"), [(42, "42"), ("pet-1", "pet-1")])
def test_ids_are_compared_as_text(raw: object, expected: str) -> None:
    from custom_components.tryfi.client import Pet

    assert Pet.from_profile({"id": raw, "device": {"id": raw}}).pet_id == expected
