"""An async client for TryFi's cloud, on a session Home Assistant provides.

It talks to api.tryfi.com and nothing else. It replaces pytryfi, which
reported every error in the host process to its author's error-reporting
service, blocked a thread on every request, and set no timeout on any of them
(upstream #56, #91: data that stopped updating until a reload).
"""

from __future__ import annotations

import logging
from typing import Any, Final

import aiohttp

from . import queries
from .errors import (
    TryFiAuthError,
    TryFiCommandError,
    TryFiConnectionError,
    TryFiError,
)
from .models import (
    JSON,
    MODE_LOST,
    MODE_NORMAL,
    Base,
    NoCollar,
    Pet,
    dig,
    identity,
)

LOGGER = logging.getLogger(__name__)

HOST: Final = "https://api.tryfi.com"
LOGIN_URL: Final = f"{HOST}/auth/login"
GRAPHQL_URL: Final = f"{HOST}/graphql"

# Long enough for TryFi on a slow day; short enough that a connection which
# died silently costs one poll rather than every poll after it.
TIMEOUT: Final = aiohttp.ClientTimeout(total=30)

# Statuses TryFi could plausibly use for rejected credentials or an expired
# session. pytryfi treated any non-2xx login as a failure before reading it.
_AUTH_STATUSES: Final = frozenset({400, 401, 403})


class TryFiClient:
    """One TryFi account: sign in, refresh pets and bases, change a collar.

    The session is passed in and keeps TryFi's session cookie, so it should be
    one created for this client (Home Assistant's async_create_clientsession)
    rather than the shared one, whose cookie jar every integration uses.
    """

    def __init__(
        self, session: aiohttp.ClientSession, username: str, password: str
    ) -> None:
        self._session = session
        self._username = username
        self._password = password
        self.user_id: str | None = None
        self.pets: list[Pet] = []
        self.bases: list[Base] = []
        # Every pet and base id the account listed in the last refresh,
        # including pets skipped for having no collar. Something absent from
        # these has left the account; something merely unreadable has not.
        self.listed_pet_ids: set[str] = set()
        self.listed_base_ids: set[str] = set()
        # Whether the last refresh's listing can be trusted as the whole
        # account: no error beside the data, and every household's pets and
        # bases present as lists. Devices are removed only on a complete one.
        self.listing_complete = False

    # ------------------------------------------------------------- session
    async def async_login(self) -> None:
        """Sign in, starting from a clean cookie jar.

        Raises TryFiAuthError when TryFi rejects the email and password, and
        TryFiConnectionError for anything else.
        """
        self._session.cookie_jar.clear()
        form = {"email": self._username, "password": self._password}
        body = await self._request("POST", LOGIN_URL, data=form, login=True)
        if not isinstance(body, dict):
            raise TryFiConnectionError("TryFi's sign-in answer was not an object")
        if body.get("error"):
            # TryFi answers a wrong password with 200 and an error body.
            raise TryFiAuthError("TryFi refused the email and password")
        user_id = body.get("userId")
        if not user_id:
            raise TryFiConnectionError("TryFi's sign-in answer had no user id")
        self.user_id = str(user_id)

    def detach(self) -> None:
        """Let go of the session.

        Not close(): on a session Home Assistant created, close() is replaced
        by a wrapper that only logs a warning, and the session stays open.
        """
        self._session.detach()

    # ------------------------------------------------------------- reading
    async def async_refresh(self) -> None:
        """Read every pet and base.

        One households query serves both; pytryfi made the same request twice
        a poll. A failure to fetch it raises, so the caller can tell the data
        is stale rather than serving it as fresh, as pytryfi did. A failure
        for one pet keeps that pet's last readings, and cannot hide the
        others.
        """
        data, complete = await self._query(queries.households())
        households = dig(data, "currentUser", "userHouseholds")
        if not isinstance(households, list):
            raise TryFiError("TryFi's answer listed no households")
        previous = {pet.pet_id: pet for pet in self.pets}
        pets: list[Pet] = []
        bases: list[Base] = []
        listed_pets: set[str] = set()
        listed_bases: set[str] = set()
        for house in households:
            household = dig(house, "household")
            house_pets = dig(household, "pets")
            house_bases = dig(household, "bases")
            # null in place of a list is TryFi failing to say, not saying none.
            if not isinstance(house_pets, list) or not isinstance(house_bases, list):
                complete = False
            for profile in house_pets if isinstance(house_pets, list) else []:
                pet_id = identity(dig(profile, "id"))
                if pet_id is None:
                    # Listed without an id: whichever pet it is cannot be
                    # matched, so the listing cannot show any pet is gone.
                    complete = False
                    continue
                listed_pets.add(pet_id)
                pet = await self._read_pet(profile, previous)
                if pet is not None:
                    pets.append(pet)
            for raw in house_bases if isinstance(house_bases, list) else []:
                try:
                    base = Base.from_json(raw)
                except (KeyError, TypeError) as err:
                    complete = False
                    LOGGER.warning(
                        "Skipping a base TryFi described without an id: %r", err
                    )
                    continue
                listed_bases.add(base.base_id)
                bases.append(base)
        self.pets, self.bases = pets, bases
        self.listed_pet_ids, self.listed_base_ids = listed_pets, listed_bases
        self.listing_complete = complete

    async def _read_pet(self, profile: JSON, previous: dict[str, Pet]) -> Pet | None:
        try:
            pet = Pet.from_profile(profile)
        except NoCollar:
            # The refresh has already set aside pets without an id, so a pet
            # here can only lack a collar.
            LOGGER.debug("Pet %s has no collar; skipping it", profile.get("name"))
            return None
        old = previous.get(pet.pet_id)
        # Each group on its own: one failed query costs that group, carried
        # over from the last refresh, not the whole pet.
        for group, query, take in (
            ("location", queries.location, self._take_location),
            ("activity", queries.activity, self._take_activity),
            ("rest", queries.rest, self._take_rest),
        ):
            try:
                take(pet, await self._graphql(query(pet.pet_id)))
            except (TryFiError, KeyError, TypeError, ValueError) as err:
                LOGGER.debug("Pet %s: %s not refreshed (%r)", pet.pet_id, group, err)
                if old is not None:
                    pet.carry_over(old, group)
        return pet

    # Each answer is {"pet": {...}}; the parsers take what is inside.
    @staticmethod
    def _take_location(pet: Pet, data: JSON) -> None:
        pet.take_location(data["pet"]["ongoingActivity"])

    @staticmethod
    def _take_activity(pet: Pet, data: JSON) -> None:
        pet.take_activity(data["pet"])

    @staticmethod
    def _take_rest(pet: Pet, data: JSON) -> None:
        pet.take_rest(data["pet"])

    def get_pet(self, pet_id: str) -> Pet | None:
        return next((pet for pet in self.pets if pet.pet_id == pet_id), None)

    def get_base(self, base_id: str) -> Base | None:
        return next((base for base in self.bases if base.base_id == base_id), None)

    # ------------------------------------------------------------- changing
    async def async_set_led(self, pet: Pet, on: bool) -> None:
        await self._operate(pet, {"ledEnabled": on})

    async def async_set_lost_mode(self, pet: Pet, lost: bool) -> None:
        await self._operate(pet, {"mode": MODE_LOST if lost else MODE_NORMAL})

    async def async_set_led_color(self, pet: Pet, code: int) -> None:
        variables = {"moduleId": self._module(pet), "ledColorCode": int(code)}
        data = await self._mutate(queries.set_led_color(), variables)
        self._take_collar(pet, data.get("setDeviceLed"))

    async def _operate(self, pet: Pet, change: dict[str, Any]) -> None:
        variables = {"input": {"moduleId": self._module(pet), **change}}
        data = await self._mutate(queries.device_operation(), variables)
        self._take_collar(pet, data.get("updateDeviceOperationParams"))

    @staticmethod
    def _module(pet: Pet) -> str:
        if not pet.collar.module_id:
            raise TryFiCommandError(f"TryFi has not reported a module for {pet.name}")
        return pet.collar.module_id

    @staticmethod
    def _take_collar(pet: Pet, device: Any) -> None:
        # The answer carries the collar's new state; take it so the change
        # shows at once. An empty answer is left to the next refresh.
        if isinstance(device, dict):
            pet.collar.update(device)

    # ------------------------------------------------------------- transport
    async def _graphql(self, query: str) -> JSON:
        data, _ = await self._query(query)
        return data

    async def _query(self, query: str) -> tuple[JSON, bool]:
        """TryFi's data, and whether it came without errors.

        GraphQL can answer with data and errors together, the errored fields
        null. The data is still used; the flag says it is not the whole story.
        """
        body = await self._request("GET", GRAPHQL_URL, params={"query": query})
        if not isinstance(body, dict):
            raise TryFiError("TryFi's answer was not an object")
        data = body.get("data")
        if body.get("errors") and not data:
            raise TryFiError(f"TryFi returned an error: {_messages(body)}")
        if not isinstance(data, dict):
            raise TryFiError("TryFi's answer had no data")
        return data, not body.get("errors")

    async def _mutate(self, query: str, variables: JSON) -> JSON:
        body = await self._request(
            "POST", GRAPHQL_URL, json={"query": query, "variables": variables}
        )
        if not isinstance(body, dict):
            raise TryFiCommandError("TryFi's answer was not an object")
        # Any error is a refusal. TryFi answers one with the mutation's field
        # null beside the errors, so a data object is no sign of success.
        if body.get("errors"):
            raise TryFiCommandError(f"TryFi refused the change: {_messages(body)}")
        data = body.get("data")
        return data if isinstance(data, dict) else {}

    async def _request(
        self,
        method: str,
        url: str,
        *,
        login: bool = False,
        **kwargs: Any,
    ) -> Any:
        headers = None if login else {"content-type": "application/json"}
        try:
            async with self._session.request(
                method, url, headers=headers, timeout=TIMEOUT, **kwargs
            ) as response:
                if response.status in _AUTH_STATUSES:
                    raise TryFiAuthError(
                        f"TryFi refused the request ({response.status})"
                    )
                if response.status >= 400:
                    raise TryFiConnectionError(f"TryFi answered {response.status}")
                return await response.json(content_type=None)
        except TryFiError:
            raise
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise TryFiConnectionError(f"TryFi could not be reached: {err!r}") from err


def _messages(body: JSON) -> str:
    return "; ".join(
        str(error.get("message", error)) if isinstance(error, dict) else str(error)
        for error in body.get("errors") or []
    )
