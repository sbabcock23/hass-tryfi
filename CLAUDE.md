# Working on this repository

sbabcock23/hass-tryfi, co-maintained by willbeeching: a Home Assistant custom
integration for TryFi dog collars. One domain, `tryfi`, in `custom_components/tryfi/`, with
its own typed async TryFi client in `custom_components/tryfi/client/`. It is
self-assessed at Home Assistant's Platinum quality scale, rule by rule in
`quality_scale.yaml`; keep that file true when a change touches a rule.

## Non-negotiables

**Send nothing anywhere but `api.tryfi.com`.** 0.1.0 replaced pytryfi
because its only release reported every error in Home Assistant to a
third-party error-reporting service. `tests/test_no_telemetry.py` fails if any file in the
integration names that library or any other host. Do not add an endpoint.

**Never commit secrets.** No emails, passwords, pet names, place names,
addresses or coordinates from a real account, in code, tests, fixtures, commit
messages or issue replies. The fake cloud in `tests/fakes.py` uses made-up
values of the same shape; keep it that way. Diagnostics redact the same list;
extend `diagnostics.py` rather than working around it.

**Entity ids and unique ids are frozen.** Every unique id format is upstream's,
byte for byte, and entity names are chosen so Home Assistant builds the same
entity ids upstream's names did. Users moved over with their history and
automations intact. `tests/ha/test_entities.py` holds both lists; if one of
them has to change, it is a breaking change and needs a migration.

**Be a polite client.** TryFi's cloud is not ours. The polling floor is 60
seconds, a failed poll signs in again at most once, and one households query
serves both pets and bases. A change that talks to TryFi more often needs a
reason better than responsiveness.

**Releases happen only when the maintainer asks.** Merging is not releasing.

## The TryFi client

`client/` replaced the vendored pytryfi it was derived from (Apache 2.0;
`client/ORIGIN.md` has the history and every change). It is aiohttp on a
session the integration creates per account with `async_create_clientsession`
(TryFi signs in with a cookie, so not the shared session), strictly typed, and
raises `TryFiAuthError`, `TryFiConnectionError` or `TryFiCommandError` rather
than swallowing anything. Nothing runs in the executor.

Do not change the GraphQL in `client/queries.py` without an account to test it
against: it is pytryfi's text, character for character, because that is what
works against TryFi today, and a broken query breaks every install at once.
`tests/test_queries.py` pins a hash of each composed query; a failure there is
the cue to test against a real account, not to update the hash.

Devices are removed only when a *complete* listing (`listing_complete`) leaves
a pet or base out of `listed_pet_ids` / `listed_base_ids`, never because one
refresh could not read it or answered with errors: a removed device takes the
user's entity ids with it.

TryFi can send null for any field. Read objects through `models.obj` / `dig`;
`tests/test_client_nulls.py` nulls every field of every answer in turn, and a
new field read without care fails it.

Sessions from Home Assistant are detached, never `close()`d: on them close()
is a wrapper that only warns. `FakeSession.close()` fails the test.

## What is settled about TryFi's data

Learned from upstream's issue tracker; see `docs/UPSTREAM_ISSUES.md`.

- **A pet's `device` is `null`, not `"None"`,** for a pet with no collar (a
  Nano chip, a cat, a shared pet). One such pet used to hide every other.
- **Collars report different fields.** The Fi Mini and Series 3+ leave some
  out. Every collar attribute defaults to `None` and entities show unknown.
- **Connection types grow.** `ConnectedToWifi` appeared after upstream was
  written. An unknown type reads as unknown, not as the raw API name.
- **`place` is `null`** when resting somewhere unsaved, and a walk can start
  before it has positions.
- **Ids go through `models.identity`.** Null or empty is no id: never a
  device, and an entry listed without one makes the listing incomplete so it
  cannot remove anything. Ids are text, whatever type TryFi sends.
- **TryFi returns 0 for distance** on days with thousands of steps, and 0 for
  daily rest for hours at a time. Those are TryFi's figures; do not "fix" them.

## Local development

Four virtualenvs, one per CI lane, gitignored. Upgrade `uv` first
(`pip install --user --upgrade uv`): the container's old one builds 3.14 on a
release candidate.

```sh
UV=~/.local/bin/uv
$UV venv --python 3.14 .venv-ha
$UV venv --python 3.13 .venv-ha-min
$UV venv --python 3.14 .venv-lint
$UV venv --python 3.14 .venv-types

$UV pip install --python .venv-ha/bin/python     -r requirements-test.txt
$UV pip install --python .venv-ha-min/bin/python -r requirements-test-min.txt
$UV pip install --python .venv-lint/bin/python   -r requirements-lint.txt
$UV pip install --python .venv-types/bin/python  -r requirements-types.txt homeassistant
```

## The checks

Eight CI checks gate a merge. Run the first four locally before pushing.

```sh
.venv-lint/bin/black --check custom_components/ tests/
.venv-lint/bin/isort --check-only custom_components/ tests/
.venv-lint/bin/ruff check custom_components/ tests/
.venv-lint/bin/flake8 custom_components/ tests/

.venv-ha/bin/python -m pytest -q \
  --cov=custom_components/tryfi \
  --cov-report=term-missing --cov-report=json --cov-fail-under=95
.venv-ha/bin/python scripts/coverage_gate.py
.venv-ha-min/bin/python -m pytest -q

.venv-types/bin/mypy custom_components/tryfi/
```

The minimum lane runs the behaviour against core 2025.1.0, the version
`hacs.json` claims, with pycares held below 4.9 (see the requirements file).
`scripts/coverage_gate.py` enforces 95% per module, the client included.

A refresh driven by `async_fire_time_changed` runs as a background task: wait
with `async_block_till_done(wait_background_tasks=True)`, or the assertions race
it.

## Versions and releases

- `manifest.json` carries the version, and the release workflow fails on a
  mismatch with the tag. Bump it in the same commit as the change.
- Release by `workflow_dispatch` on `release.yaml` with `version` (`v0.1.0`)
  and optional `notes`. A commit body line starting `BREAKING:` is lifted into
  a warning section at the top of the notes.
- Two archives ship: `tryfi.zip` wraps the directory for manual installs,
  `tryfi-hacs.zip` has the files at its root for HACS. They are not
  interchangeable.

## Code conventions

As in willbeeching/ha-jlr-incontrol: comments explain why, usually by naming
the upstream issue; line length 88, black, isort (black profile), ruff with
`E F W I UP B SIM C4 RET PTH`; strict mypy spelled out in `pyproject.toml`;
flow schemas import `probatio` as `vol` on core 2026.10+ and `voluptuous`
before it. Tests in `tests/` drive the real client against the fake cloud;
tests in `tests/ha/` drive a running Home Assistant, and `test_wire.py` runs
the client through real aiohttp. Widen
`tests/fakes.py` rather than hand-rolling a payload per test.
