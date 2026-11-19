"""Every form the integration shows can be drawn by the core it runs on.

The flow tests drive the steps from Python and never turn a schema into what
the frontend receives. Core 2026.10 moved from voluptuous to probatio and
serialises forms with probatio's own converter, so a schema it could not read
would pass every other test and leave the dialog blank in the browser.
"""

from __future__ import annotations

from typing import Any

import pytest
from fakes import FakeCloud
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tryfi import config_flow
from custom_components.tryfi.const import DOMAIN

try:  # Home Assistant 2026.10 onwards
    from probatio import to_field_list

    def render(schema: Any) -> list[dict[str, Any]]:
        return to_field_list(schema, custom_serializer=cv.custom_serializer)

except ImportError:  # the cores before it
    import voluptuous_serialize

    def render(schema: Any) -> list[dict[str, Any]]:
        return voluptuous_serialize.convert(  # type: ignore[no-any-return]
            schema, custom_serializer=cv.custom_serializer
        )


@pytest.mark.parametrize("schema", ["STEP_USER_SCHEMA", "STEP_REAUTH_SCHEMA"])
def test_each_schema_converts(schema: str) -> None:
    assert render(getattr(config_flow, schema)), f"{schema} rendered empty"


async def test_the_sign_in_form_as_the_frontend_gets_it(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    names = {field["name"] for field in render(result["data_schema"])}
    assert names == {"username", "password", "polling"}


async def test_the_options_form_as_the_frontend_gets_it(
    hass: HomeAssistant, entry: MockConfigEntry, loaded: FakeCloud
) -> None:
    result = await hass.config_entries.options.async_init(entry.entry_id)
    fields = render(result["data_schema"])
    assert [field["name"] for field in fields] == ["polling"]
    assert fields[0]["default"] == 60
