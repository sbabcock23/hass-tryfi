# Where this client comes from

A typed async client for TryFi, written for this integration. It is derived
from [pytryfi](https://github.com/sbabcock23/pytryfi) by Steve Babcock (Apache
2.0, see `LICENSE` here), by way of
[disruptivepatternmaterial/pytryfi](https://github.com/disruptivepatternmaterial/pytryfi)
at commit `cc31b965d408794a8cb4311a9d8695b622f1e5cc`, which this integration
vendored before replacing it.

## What is kept exactly

**The GraphQL.** Every query and mutation in `queries.py` is pytryfi's text,
character for character, composed in the same order. These are the queries
that work against TryFi on every install today, and a changed one cannot be
checked without a real account. `tests/test_queries.py` pins a hash of each
composed query, taken from pytryfi itself before it was removed.

**The requests.** The sign-in is the same form post to `/auth/login`; queries
are the same GET to `/graphql` with the query as a parameter; changes are the
same JSON post with the same variables. Only api.tryfi.com is ever contacted.

## What changed, and why

| Change | Why |
| --- | --- |
| aiohttp, on a session Home Assistant creates | pytryfi used `requests`, blocking a worker thread on every call. Home Assistant's async-dependency and inject-websession rules. The session is the account's own (`async_create_clientsession`), because TryFi's sign-in is a cookie and the shared session's cookie jar is every integration's. |
| Fully typed, checked by strict mypy with the integration | The strict-typing rule asks for a typed library; pytryfi had no annotations. |
| No error reporting to anyone | pytryfi 0.0.21 sent every error in Home Assistant to its author's service (upstream #115). |
| A 30-second timeout on every request | pytryfi set none, so a connection that died silently hung the poll until a reload (#56, #91). |
| Errors raised, not swallowed, and told apart | pytryfi caught everything, so a wrong password and an outage looked the same and stale data looked fresh. Now `TryFiAuthError`, `TryFiConnectionError`, `TryFiCommandError`. |
| A mutation answered with any error is a refusal | TryFi refuses with the mutation's field null beside the errors; pytryfi read the non-empty data as success. |
| No user-profile query | pytryfi fetched it at sign-in; nothing used it. |
| One households query per refresh for pets and bases | pytryfi made the same request twice. |
| Pets and bases read one at a time; a pet with no collar skipped | pytryfi compared `device` with `"None"` while TryFi sends `null`, and one such pet hid every other (#61, #62, #67, #87, #96, #99, #102). |
| A failed location, activity or rest query keeps that group's last readings | Rather than losing the pet. |
| Every collar field defaults to `None`, read in independent groups | A field one collar leaves out left every later one undefined (#69, #100). |
| Bases read with defaults | A base missing a field failed the sensor platform (#93). |
| `place: null`, a walk with no positions yet, `weight: null`, no connection state | Each of these failed the pet or its location. |
| A rest period with no summary is unknown, not 0 | A false 0 is a reset to Home Assistant's statistics, which then counted the same minutes twice. |
| Connection detail kept structured | Which base, whose phone, what signal (#60). |
| The pets and bases the account lists are recorded, and whether the listing was complete | So a device is removed only when a complete listing leaves it out, never because one refresh could not read it or TryFi answered with errors. |
| Every object read through a check that it is one | TryFi can send null for any field; `.get()` on a null failed setup. `tests/test_client_nulls.py` nulls every field of every answer in turn. |
| Ids validated and compared as text | A null or empty id became a device called "None", and its absence removed the real device. An id sent as a number one time and text the next is the same id. |
| The session is detached, never closed | On a session Home Assistant created, `close()` only logs a warning. |

Issue numbers are on [sbabcock23/hass-tryfi](https://github.com/sbabcock23/hass-tryfi/issues).
