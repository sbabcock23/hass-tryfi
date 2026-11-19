"""The client through a real aiohttp session, as Home Assistant creates it.

Every other test hands the client a fake session. This one goes through
aiohttp itself, via Home Assistant's own request mocker, so the requests are
built the way they will be on the wire: the sign-in as a form, queries as a
GET parameter, changes as a JSON body.
"""

from __future__ import annotations

from typing import Any

from fakes import FakeCloud
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)

from custom_components.tryfi.api import async_connect

LOGIN = "https://api.tryfi.com/auth/login"
GRAPHQL = "https://api.tryfi.com/graphql"


async def test_requests_on_the_wire(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    cloud = FakeCloud()
    aioclient_mock.post(
        LOGIN, json={"userId": "user-0001", "sessionId": "session-0001"}
    )

    async def graphql(method: str, url: Any, data: Any) -> Any:
        from pytest_homeassistant_custom_component.test_util.aiohttp import (
            AiohttpClientMockResponse,
        )

        if method == "GET":
            query = url.query["query"]
            answer = cloud.query(query)
        else:
            answer = cloud.mutate(data)
        return AiohttpClientMockResponse(method, url, json=answer._body)

    aioclient_mock.get(GRAPHQL, side_effect=graphql)
    aioclient_mock.post(GRAPHQL, side_effect=graphql)

    client = await async_connect(hass, "someone@example.com", "correct-horse")
    assert [pet.name for pet in client.pets] == ["Biscuit"]
    assert client.pets[0].steps["daily"] == 4321

    method, url, data, headers = aioclient_mock.mock_calls[0]
    assert (method, str(url)) == ("POST", LOGIN)
    assert data == {"email": "someone@example.com", "password": "correct-horse"}

    method, url, data, headers = aioclient_mock.mock_calls[1]
    assert method == "GET"
    assert "UserFullDetails" in url.query["query"]
    assert headers["content-type"] == "application/json"

    await client.async_set_lost_mode(client.pets[0], True)
    method, url, data, headers = aioclient_mock.mock_calls[-1]
    assert method == "POST"
    assert data["variables"] == {
        "input": {"moduleId": "module-0001", "mode": "LOST_DOG"}
    }
    assert client.pets[0].collar.is_lost is True
    client.detach()
