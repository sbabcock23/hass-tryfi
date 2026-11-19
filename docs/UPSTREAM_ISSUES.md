# Upstream issues

Every open issue on [sbabcock23/hass-tryfi](https://github.com/sbabcock23/hass-tryfi/issues)
as of 10 November 2026, and what 0.1.0 does about it. Where an issue traced
back to pytryfi rather than the integration, the fix is in the integration's own
TryFi client, which replaces pytryfi; every change from it is listed in
[`client/ORIGIN.md`](../custom_components/tryfi/client/ORIGIN.md).
Most have a test named after the failure.

## Fixed

| Issue | Report | Cause | Fix |
| --- | --- | --- | --- |
| [#115](https://github.com/sbabcock23/hass-tryfi/issues/115) | Does this integration exfiltrate data? | pytryfi 0.0.21 starts a third-party error reporter that captures every error in Home Assistant. | pytryfi replaced by the integration's own client, which has none of it; a test fails if any file names it. |
| [#113](https://github.com/sbabcock23/hass-tryfi/issues/113), [#111](https://github.com/sbabcock23/hass-tryfi/issues/111) | Options flow: 500 error | The handler assigned the now read-only `config_entry`. | Rewritten options flow. |
| [#109](https://github.com/sbabcock23/hass-tryfi/issues/109) | Deprecated `TrackerEntity` alias | Imported from `.config_entry`. | Imported from the package. |
| [#104](https://github.com/sbabcock23/hass-tryfi/issues/104), [#91](https://github.com/sbabcock23/hass-tryfi/issues/91), [#56](https://github.com/sbabcock23/hass-tryfi/issues/56) | Data stops updating until a reload | No timeout on any request, so a connection that died silently hung the poll for ever; failures were swallowed so data went stale without a sign; no way to sign in again. | 30-second timeouts; failures reach the coordinator, so entities go unavailable; one fresh sign-in per failed poll; a rejected password starts re-authentication. |
| [#102](https://github.com/sbabcock23/hass-tryfi/issues/102), [#99](https://github.com/sbabcock23/hass-tryfi/issues/99), [#96](https://github.com/sbabcock23/hass-tryfi/issues/96), [#87](https://github.com/sbabcock23/hass-tryfi/issues/87), [#67](https://github.com/sbabcock23/hass-tryfi/issues/67), [#62](https://github.com/sbabcock23/hass-tryfi/issues/62), [#61](https://github.com/sbabcock23/hass-tryfi/issues/61) | Only the bases show up / a collar missing | pytryfi compared a pet's device with the string `"None"`, but TryFi sends `null`; one pet without a collar (a Nano chip, a cat, a shared pet) abandoned every pet. Any other odd pet did the same. | Collarless pets skipped; each pet loaded on its own; one that fails cannot hide the others. |
| [#100](https://github.com/sbabcock23/hass-tryfi/issues/100), [#69](https://github.com/sbabcock23/hass-tryfi/issues/69) | `FiDevice` has no `_mode` / `_ledOn` | Collar fields were read in one block; the first missing one left the rest undefined. | Every field defaults; fields read in independent groups; entities show unknown. |
| [#93](https://github.com/sbabcock23/hass-tryfi/issues/93) | Base missing attributes breaks setup | Same pattern in `FiBase`. | Defaults, and fields read with `.get`. |
| [#107](https://github.com/sbabcock23/hass-tryfi/issues/107) | "Could not set place" log spam | Logged by a later pytryfi on every poll while walking. | Not present in the new client; `place: null` handled quietly. |
| [#106](https://github.com/sbabcock23/hass-tryfi/issues/106) | Cannot sign in on a fresh install | Every failure surfaced as `CannotConnect` with a traceback. | Wrong password and unreachable cloud are told apart (`invalid_auth`, `cannot_connect`). |
| [#86](https://github.com/sbabcock23/hass-tryfi/issues/86), [#80](https://github.com/sbabcock23/hass-tryfi/issues/80) | `async_forward_entry_setup` | Fixed in upstream 0.0.26. | Kept (`async_forward_entry_setups`). |
| [#79](https://github.com/sbabcock23/hass-tryfi/issues/79), [#52](https://github.com/sbabcock23/hass-tryfi/issues/52) | Polling rate ignored | Only `entry.data` was read. | Options first, then data; saving reloads; floor of 60 s. |
| [#78](https://github.com/sbabcock23/hass-tryfi/issues/78), [#77](https://github.com/sbabcock23/hass-tryfi/issues/77), [#59](https://github.com/sbabcock23/hass-tryfi/issues/59) | Deprecated constants | | Enums throughout. |
| [#71](https://github.com/sbabcock23/hass-tryfi/issues/71) | How to change Lost Mode from an automation | `input_select.select_option` was used. | Documented: `select.select_option`. Commands now raise an error when TryFi refuses them. |
| [#60](https://github.com/sbabcock23/hass-tryfi/issues/60) | Which base is the collar on? | Not exposed. | `base_id` and `base_name` attributes on Connected to. |
| [#35](https://github.com/sbabcock23/hass-tryfi/issues/35) | Dog's current state | Activity type showed `OngoingRest`. | An enum sensor: Resting / Walking; plus Connected to (phone = with a person). |
| [#24](https://github.com/sbabcock23/hass-tryfi/issues/24) | Change LED colour | Already supported. | Kept; nearest colour the collar offers. |
| [#23](https://github.com/sbabcock23/hass-tryfi/issues/23) | km or miles | No device class, so no unit conversion. | Distance and duration device classes: change the unit per entity, and new installs follow the unit system. |

## Not fixable here

| Issue | Report | Why |
| --- | --- | --- |
| [#89](https://github.com/sbabcock23/hass-tryfi/issues/89) | Sleep/nap stopped updating | The reporter's own debugging showed TryFi returning zero for the daily rest summary while the app had data. Documented in [ENTITIES.md](ENTITIES.md). |
| [#83](https://github.com/sbabcock23/hass-tryfi/issues/83) | Tap shows history, not a map | Home Assistant's card and dialog behaviour, set in the dashboard. The tracker is no longer filed under Diagnostic, which puts it at the top of the device page. |
| [#51](https://github.com/sbabcock23/hass-tryfi/issues/51) | MySQL "illegal mix of collations" | A database character-set setting meeting an emoji in a pet's name. |
| [#57](https://github.com/sbabcock23/hass-tryfi/issues/57) | Homebridge | Out of scope. |
