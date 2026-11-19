# Entities

Each pet with a collar becomes a device named after the pet, with the breed as
its model. Each charging base becomes a device of its own. Pets with no collar
(a Nano chip, a shared pet, a retired collar) are skipped.

Entity ids are built from the pet's name, so for a pet called Rex:

## On the device page

| Entity | Example id | State | Notes |
| --- | --- | --- | --- |
| Tracker | `device_tracker.rex_tracker` | `home`, `not_home`, a zone, or `unknown` | Where the collar last reported. `unknown` when it has no fix yet, rather than an error. Shows the pet's photo. |
| Collar light | `light.rex_collar_light` | `on` / `off` | Colour picks the nearest the collar offers. The state changes as soon as the command returns. |
| Lost mode | `select.rex_lost_mode` | `Safe` / `Lost` | Set it with `select.select_option` (not `input_select`). |
| Activity type | `sensor.rex_activity_type` | `resting` / `walking` | An enum sensor; shown as Resting / Walking. |
| Current place name | `sensor.rex_current_place_name` | e.g. `Home` | The saved place in the TryFi app; `unknown` when the pet is somewhere unsaved or walking. |
| Current place address | `sensor.rex_current_place_address` | e.g. `1 Example Road` | As above. |
| Daily steps | `sensor.rex_daily_steps` | steps | `total_increasing`, so it has long-term statistics. |
| Daily distance | `sensor.rex_daily_distance` | km | As above. |
| Daily sleep | `sensor.rex_daily_sleep` | min | As above. |
| Daily nap | `sensor.rex_daily_nap` | min | As above. |

## Diagnostic

| Entity | Example id | State | Notes |
| --- | --- | --- | --- |
| Collar battery level | `sensor.rex_collar_battery_level` | % | `measurement`, with statistics. |
| Collar battery charging | `binary_sensor.rex_collar_battery_charging` | `on` / `off` | Older collars do not report it and read `off`. |
| Connected to | `sensor.rex_connected_to` | `base` / `wifi` / `cellular` / `phone` | How the collar last reached TryFi. `unknown` for TryFi's own "unknown connectivity", and for any type TryFi adds later. Attributes say which base (`base_id`, `base_name`), whose phone (`person`, first name only), or the cellular `signal_strength`. |
| Collar signal strength | `sensor.rex_collar_signal_strength` | % | Disabled by default. Only has a value while the collar is on cellular. |

## Disabled by default on a new install

The weekly and monthly totals for steps, distance, sleep and nap
(`sensor.rex_weekly_steps`, `sensor.rex_monthly_distance`, and so on).
Enable any of them from the device page. Entities that already existed before
0.1.0 keep whatever state they had, enabled included.

## Bases

| Entity | Example id | State |
| --- | --- | --- |
| The base's name | `sensor.kitchen_base` | `Online` / `Offline` |

## What the numbers mean

- **Totals reset** at the start of each day, week or month. Home Assistant's
  statistics read the drop as a new cycle, not a fall.
- **Distance can read 0** while steps climb into the thousands. That is the
  figure TryFi returns (seen on real collars, a cat's and a dog's), not a fault
  here.
- **Sleep and nap read unknown** when TryFi sends no rest summary for the
  period, rather than 0: a false 0 would make Home Assistant's statistics count
  a reset, and then count the same minutes again when the summary came back.
- **Daily sleep can read 0 for part of the day.** When TryFi does send a daily
  summary, it sometimes reports zero for hours while the weekly one has data
  (upstream #89). That is TryFi's figure.
- **A pet or base that appears later**, a collar fitted after setup, say, gets
  its entities on the next refresh, without a reload.
- **A pet or base removed from the account** has its device, and its entities,
  removed on the next refresh. A pet still on the account without its collar
  is kept, unavailable, and can be deleted from its device page.
- **Location is where the collar last reported**, which it does on its own
  schedule.

## Moving from 0.0.x: states that changed

Two sensors used to show TryFi's raw API names. If an automation compares
against one of them, update it:

| Sensor | Was | Now |
| --- | --- | --- |
| Activity type | `OngoingRest` | `resting` |
| | `OngoingWalk` | `walking` |
| Connected to | `ConnectedToBase` | `base` |
| | `ConnectedToWifi` | `wifi` |
| | `ConnectedToCellular` | `cellular` |
| | `ConnectedToUser` | `phone` |
| | `UnknownConnectivity` | `unknown` |

The tracker no longer has a `battery_level` attribute; use
`sensor.<pet>_collar_battery_level`.
