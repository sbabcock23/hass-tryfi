"""Shared fixtures: TryFi's cloud, replaced at the HTTP session."""

from __future__ import annotations

from typing import Any

import pytest
from fakes import FakeCloud, FakeSession


@pytest.fixture
def cloud(monkeypatch: pytest.MonkeyPatch) -> FakeCloud:
    """Every session the integration creates talks to this instead of TryFi."""
    fake = FakeCloud()

    def create(hass: Any, **kwargs: Any) -> FakeSession:
        return FakeSession(fake)

    monkeypatch.setattr(
        "custom_components.tryfi.api.async_create_clientsession", create
    )
    return fake
