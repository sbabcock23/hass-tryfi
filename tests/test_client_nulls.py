"""Any field TryFi sends as null costs at most that reading.

Review of ad0329c found `info: null` and `operationParams: null` failing the
whole integration at setup. Rather than fix those two and wait for the next,
this sets every field of every answer the client reads to null, one at a
time, and requires the refresh either to succeed or to raise a TryFiError,
which the integration handles. Anything else is a crash at setup.
"""

from __future__ import annotations

import copy
from collections.abc import Iterator
from typing import Any

import pytest
from fakes import FakeCloud, FakeResponse, FakeSession

from custom_components.tryfi.client import TryFiClient, TryFiError


def _paths(value: Any, prefix: tuple[Any, ...] = ()) -> Iterator[tuple[Any, ...]]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield (*prefix, key)
            yield from _paths(child, (*prefix, key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield (*prefix, index)
            yield from _paths(child, (*prefix, index))


def _nulled(body: Any, path: tuple[Any, ...]) -> Any:
    body = copy.deepcopy(body)
    target = body
    for step in path[:-1]:
        target = target[step]
    target[path[-1]] = None
    return body


def _answers(cloud: FakeCloud) -> dict[str, Any]:
    return {
        "households": cloud.households_answer(),
        "location": {"data": {"pet": {"ongoingActivity": cloud.location()}}},
        "activity": {"data": {"pet": cloud.stats()}},
        "rest": {"data": {"pet": cloud.rest()}},
    }


def _cases() -> Iterator[tuple[str, tuple[Any, ...]]]:
    cloud = FakeCloud()
    cloud.location_mode = "walk"
    for kind, body in _answers(cloud).items():
        for path in _paths(body):
            yield kind, path
    # And the resting shape, with its position and place.
    rest_shape = {"data": {"pet": {"ongoingActivity": FakeCloud().location()}}}
    for path in _paths(rest_shape):
        yield "location", path


CASES = sorted(set(_cases()), key=repr)


@pytest.mark.parametrize(("kind", "path"), CASES, ids=[f"{k}:{p}" for k, p in CASES])
async def test_a_null_anywhere_is_never_a_crash(
    cloud: FakeCloud, kind: str, path: tuple[Any, ...]
) -> None:
    original = cloud.query

    def query(text: str) -> FakeResponse:
        response = original(text)
        # The fake records which query it answered just before returning.
        if _kind(cloud.requests[-1]) == kind:
            response._body = _nulled(response._body, path)
        return response

    cloud.query = query  # type: ignore[method-assign]
    client = TryFiClient(
        FakeSession(cloud),  # type: ignore[arg-type]
        "someone@example.com",
        cloud.password,
    )
    await client.async_login()
    try:
        await client.async_refresh()
    except TryFiError:
        return
    # Read every property the integration reads, which must not raise either.
    for pet in client.pets:
        collar = pet.collar
        _ = (
            collar.led_on,
            collar.is_lost,
            collar.battery_percent,
            collar.connection_type,
            pet.latitude,
            pet.place_name,
            pet.steps.get("daily"),
            pet.sleep_s.get("daily"),
        )


def _kind(request: str) -> str:
    return "activity" if request == "stats" else request
