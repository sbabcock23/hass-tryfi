"""Fixtures that set the integration up against a real Home Assistant.

Everything is real except TryFi's servers: the vendored pytryfi runs, and its
requests.Session is the fake in tests/fakes.py.
"""

from __future__ import annotations

from typing import Any

import pytest

pytest.importorskip("pytest_homeassistant_custom_component")

from fakes import FakeCloud  # noqa: E402
from homeassistant.core import HomeAssistant  # noqa: E402
from pytest_homeassistant_custom_component.common import (  # noqa: E402
    MockConfigEntry,
)

from custom_components.tryfi.const import DOMAIN  # noqa: E402


@pytest.fixture(autouse=True)
def custom_integrations(enable_custom_integrations: Any) -> None:
    """Let Home Assistant find this repo's custom_components directory."""


@pytest.fixture
def entry(hass: HomeAssistant) -> MockConfigEntry:
    # Shaped like an entry made by upstream 0.0.26: polling stored as text, at
    # upstream's ten-second default, and no options.
    created = MockConfigEntry(
        domain=DOMAIN,
        title="someone@example.com",
        data={
            "username": "someone@example.com",
            "password": "correct-horse",
            "polling": "10",
        },
    )
    created.add_to_hass(hass)
    return created


@pytest.fixture
async def loaded(
    hass: HomeAssistant, entry: MockConfigEntry, cloud: FakeCloud
) -> FakeCloud:
    """A fully set-up integration with one pet and one base."""
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return cloud
