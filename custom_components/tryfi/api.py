"""Creating a session and a signed-in client for one TryFi account."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .client import (
    TryFiAuthError,
    TryFiClient,
    TryFiCommandError,
    TryFiConnectionError,
    TryFiError,
)

__all__ = [
    "TryFiAuthError",
    "TryFiClient",
    "TryFiCommandError",
    "TryFiConnectionError",
    "TryFiError",
    "async_check",
    "async_connect",
]


async def async_connect(
    hass: HomeAssistant, username: str, password: str, *, auto_cleanup: bool = True
) -> TryFiClient:
    """Sign in and read the account, on a session of the account's own.

    Its own rather than Home Assistant's shared one, because TryFi's sign-in
    is a cookie and the shared session's cookie jar is every integration's.
    Created during an entry's setup, Home Assistant detaches it when the entry
    unloads; it is detached here at once if signing in or the first read fails,
    rather than relying on what a failed setup does with it.
    """
    session = async_create_clientsession(hass, auto_cleanup=auto_cleanup)
    client = TryFiClient(session, username, password)
    try:
        await client.async_login()
        await client.async_refresh()
    except BaseException:
        client.detach()
        raise
    return client


async def async_check(hass: HomeAssistant, username: str, password: str) -> str | None:
    """Sign in once to prove the credentials, and return TryFi's user id.

    For the flows, which belong to no entry: Home Assistant would keep their
    session until it stops, so it is made without auto-cleanup and detached
    here whatever happens.
    """
    client = await async_connect(hass, username, password, auto_cleanup=False)
    client.detach()
    return client.user_id
