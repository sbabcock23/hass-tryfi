# TryFi for Home Assistant

[![CI](https://github.com/sbabcock23/hass-tryfi/actions/workflows/ci.yaml/badge.svg)](https://github.com/sbabcock23/hass-tryfi/actions/workflows/ci.yaml)
[![GitHub Release](https://img.shields.io/github/v/release/sbabcock23/hass-tryfi?include_prereleases)](https://github.com/sbabcock23/hass-tryfi/releases)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://github.com/sbabcock23/hass-tryfi/blob/master/LICENSE)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![vibe-coded](https://img.shields.io/badge/vibe-coded-ff69b4?logo=musicbrainz&logoColor=white)](https://en.wikipedia.org/wiki/Vibe_coding)
[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20me%20AI%20tokens-ffdd00?logo=buymeacoffee&logoColor=black)](https://buymeacoffee.com/willbeeching)

Get your dog's (or cat's) TryFi collar into Home Assistant: where they are, whether they're out
on a walk, steps, distance, sleep, the collar's battery, its light, and Lost Mode.

Written by [Steve Babcock](https://github.com/sbabcock23) and co-maintained with
[Will Beeching](https://github.com/willbeeching). Version 0.1.0 rebuilds it and keeps the same
domain, the same entity ids and the same unique ids, so updating keeps your entities, history and
automations.

## What changed in 0.1.0

**Earlier versions sent data to a third party.** The only release of their library on PyPI,
pytryfi 0.0.21, starts an error-reporting client (Sentry) the moment it signs in. That client hooks Home Assistant's root logger, so every error from anything in your
Home Assistant goes off-box, not just TryFi's. And when a sign-in fails, the report it sends
can include the frame holding your email and password, which its scrubber does not reach. The call was
removed from pytryfi in April 2025, but that change was never released
([#115](https://github.com/sbabcock23/hass-tryfi/issues/115)).

0.1.0 has its own TryFi client instead, rewritten from pytryfi as a typed async client with
none of that in it. It sends nothing anywhere but `api.tryfi.com`, and a test fails if any file in
the integration names the reporting library or any other host. It still sends TryFi exactly the
queries pytryfi did, down to the character, because those are known to work.

**It also fixes what was broken.** Every issue open before 0.1.0 is listed in
[docs/UPSTREAM_ISSUES.md](docs/UPSTREAM_ISSUES.md) with its cause and what was done. The big
ones:

- **"Only the bases show up."** One pet without a collar on the account (a Nano chip, a cat, a
  pet shared with you, a collar you retired) made the library abandon every pet. Each pet now
  loads on its own.
- **"Data stops updating until I reload."** No request had a timeout, so a connection that died
  quietly (a router failing over, say) hung the poll for ever. Now requests time out, a failed
  poll signs in again on a fresh connection, and the entities show unavailable while TryFi is
  unreachable instead of silently going stale.
- **The options dialog failed with a 500**, and the polling rate it saved was never read.
- **A wrong password was accepted at setup**, then retried in the background for ever. Now the
  form says so, and a password changed later asks you for the new one.
- **Ready for the 2027 removals** in Home Assistant, with no deprecation warnings on 2026.11.
- **Built to Home Assistant's Platinum quality standard**: an async client on a session Home
  Assistant provides, strict typing throughout, and every Bronze, Silver and Gold rule met or
  exempt with a reason. This is a self-assessment, recorded rule by rule in
  [`quality_scale.yaml`](custom_components/tryfi/quality_scale.yaml); a custom integration is not
  reviewed by Home Assistant.

## What you get

For each pet with a collar, a device named after the pet:

- **Tracker**, with the pet's photo, resolving to your zones. Unknown, not an error, until the
  collar has its first fix.
- **Activity**: Resting or Walking, and the saved place they're at.
- **Today's steps, distance, sleep and nap**, with long-term statistics. Weekly and monthly
  totals are there too, disabled by default.
- **Collar light**, colour included, and **Lost Mode**. Both update the moment you change them.
- **Diagnostics**: battery level and charging, and how the collar last connected (base, Wi-Fi,
  cellular or a phone), with which base, whose phone or the signal strength.

Each charging base shows as online or offline. Every entity is described in
[docs/ENTITIES.md](docs/ENTITIES.md).

## Requirements

- Home Assistant 2025.1 or newer.
- A TryFi account with at least one collar, and its email and password.

## Supported devices

Any collar on your TryFi account, as TryFi reports it. Owners on the upstream tracker report the
Fi Series 3 and Series 3+ collars and the Fi Mini, with Series 2 and Series 3 charging bases. Collars
report different things: a Fi Mini or Series 3+ leaves some fields out, and older collars do not
say whether they are charging; whatever a collar does not report shows as unknown rather than as
an error.

Pets with only a microchip (a Fi Nano, say) have no collar to read and are left out.

## Installation

### HACS (recommended)

1. In HACS, open **⋮** → **Custom repositories** and add `https://github.com/sbabcock23/hass-tryfi`
   with category **Integration**.
2. Install **TryFi Dog Monitor**.
3. Restart Home Assistant.

### Manual

Download `tryfi.zip` from the [latest release](https://github.com/sbabcock23/hass-tryfi/releases),
extract it into `config/custom_components/`, and restart.

### Updating from 0.0.x

Your entities, their history and your automations are kept. In this order:

1. **Disable the existing TryFi entry and restart Home Assistant.** Settings → Devices & Services
   → TryFi → ⋮ → Disable. The old library's reporting client is loaded into the running process;
   only a restart unloads it.
2. **Change your TryFi password** in the TryFi app. If the old library ever sent a failed sign-in,
   the password went with it.
3. In HACS, **update TryFi Dog Monitor** to 0.1.0, and restart.
4. **Re-enable the TryFi entry.** Home Assistant will ask for your password again, because you
   changed it: enter the new one.
5. Check your tracker updates, and look over anything that used the two sensors whose states
   changed (below).

## Setup

**Settings → Devices & Services → Add Integration → TryFi.** If Home Assistant has Bluetooth (a
proxy will do) and a Fi collar is in range, TryFi may already be waiting under **Discovered**;
either way it leads to the same form:

| Field | What to enter |
| --- | --- |
| Email | The email you sign in to the TryFi app with. |
| Password | Its password. A wrong one says so straight away. |
| Polling interval | Seconds between refreshes; 60 is the default and the minimum. |

One entry per TryFi account; adding the same account again is refused. To change the email or
password later without losing anything, use **⋮ → Reconfigure** on the entry. It refuses details
that sign in to a different account.

### Options

**Settings → Devices & Services → TryFi → Configure.**

| Option | Default | What it does |
| --- | --- | --- |
| Polling interval | 60 seconds | How often TryFi is asked for new readings. At least 60. Saving reloads the integration; entity ids and history are kept. |

Versions before 0.1.0 defaulted to 10 seconds. Each poll is one request for the account and three per pet,
and a collar reports far less often than that, so a faster poll mostly fetches the same answer
again. An entry carried over at 10 seconds is raised to 60.

## Breaking changes in 0.1.0

- **Activity type** reads `resting` / `walking`, not `OngoingRest` / `OngoingWalk`.
- **Connected to** reads `base` / `wifi` / `cellular` / `phone`, not `ConnectedToBase` and so on.
  TryFi's `UnknownConnectivity` is now plain unknown.
- The tracker's `battery_level` attribute is gone (Home Assistant stops supporting it in 2027.7).
  Use `sensor.<pet>_collar_battery_level`.

The full old-to-new table is in [docs/ENTITIES.md](docs/ENTITIES.md#moving-from-00x-states-that-changed).
Entity ids, unique ids and long-term statistics are unchanged.

## How it works

It signs in with your email and password, the way the TryFi app does, and asks TryFi's cloud for
each pet's position, activity and totals on a timer. TryFi has no push or token sign-in for
third parties, so the password has to be kept, in your Home Assistant config entry and nowhere
else, to sign in again when TryFi's session lapses.

- **Every polling interval** (60 seconds by default) it reads the account's pets and bases, then
  each pet's position, activity totals and rest. Every entity updates from that one read.
- **Turning the light on or off, or changing Lost Mode,** shows at once: TryFi's answer carries
  the collar's new state. A refresh follows straight after to catch anything else.
- **Location is where the collar last reported**, which it does on its own schedule.
- **If one of a pet's reads fails**, that pet keeps its last readings for that part until the next
  poll; the other pets are unaffected.
- **If TryFi stops answering**, the poll gives up after 30 seconds, signs in once more, and
  otherwise marks the entities unavailable until TryFi is back. It does not retry in a loop.
- **If TryFi rejects the password**, the TryFi entry asks you to sign in again, rather than
  retrying the old password in the background.
- **A pet or base added to the account** appears on the next poll. **One removed from it** has its
  device removed on the next poll. A pet still on the account but without its collar is kept, and
  can be deleted from its device page.

## Known limitations

- **Not live.** A collar reports when it chooses to, and TryFi is read once a polling interval,
  so a position can be some minutes old. It suits "is the dog home" far better than following a
  walk.
- **TryFi's own figures.** Distance can read 0 on a day with thousands of steps, and daily sleep
  can read 0 for hours while the weekly figure grows. Those are what TryFi returns.
- **Undocumented API.** TryFi publishes no API for third parties. This uses the one the app does,
  which TryFi could change at any time.
- **The password is stored** in the Home Assistant config entry, because TryFi offers no other
  way to sign in again when its session lapses.
- **The light's brightness** cannot be set; the collar's LED is on or off, in one of the colours
  it offers. A colour you choose is matched to the nearest of those.
- **Bluetooth discovery** only says a collar is near; it cannot tell whose account it is on, so it
  still asks you to sign in.

## What people use it for

- **"The dog's got out."** The tracker leaving home, or Activity type turning to Walking with
  nobody out with them, as a notification.
- **Charge reminders.** Collar battery level under a threshold while not charging.
- **A daily summary.** Steps, distance and sleep at the end of the day, or a weekly trend.
- **Finding the dog at night.** The collar light on when the dog goes out after dark, and Lost
  Mode from a dashboard button when it matters.

Examples for each are in [docs/RECIPES.md](docs/RECIPES.md).

## Removing the integration

**Settings → Devices & Services → TryFi → ⋮ → Delete.** The email and password go with the entry,
along with every device and entity it made; nothing is stored anywhere else. If you installed
through HACS, remove it there too and restart. To cut off access at TryFi's end as well, change
your TryFi password in the app.

## Troubleshooting

| Symptom | What to do |
| --- | --- |
| A pet is missing | Pets with no collar are skipped on purpose. A pet added to the account recently appears on the next poll. For a collared pet that never appears, download diagnostics (below) and open an issue. |
| Entities unavailable | TryFi isn't answering. They come back on their own; the log says why. |
| A pet's entities unavailable, the rest fine | The pet is still on the account but its collar is not. Delete its device if it is not coming back. |
| A device disappeared | TryFi stopped listing that pet or base on the account. It comes back, with the same entity ids, if TryFi lists it again. |
| The light or Lost Mode says TryFi did not accept the change | TryFi refused it; the message says why. Nothing changed on the collar. |
| Setup says the account is already configured | Each TryFi account can be added once. |
| TryFi asks you to sign in again | Your TryFi password changed. Enter the current one in the prompt on the TryFi entry. |
| Distance reads 0 while steps climb | That's the figure TryFi returns; see [ENTITIES.md](docs/ENTITIES.md#what-the-numbers-mean). |
| Something else | **Settings → Devices & Services → TryFi → ⋮ → Download diagnostics**. Your email, password, pet and place names and coordinates are already removed, so it can go straight into an issue. |

## Documentation

| | |
| --- | --- |
| [Entities](docs/ENTITIES.md) | Every entity, what it means, and what changed from upstream |
| [Upstream issues](docs/UPSTREAM_ISSUES.md) | Every issue open before 0.1.0, its cause, and what was done |
| [Recipes](docs/RECIPES.md) | Automations and dashboard examples |
| [The TryFi client](custom_components/tryfi/client/ORIGIN.md) | Where the client came from, what it kept from pytryfi, and every change |

## Credits

Written by **Steve Babcock** ([sbabcock23](https://github.com/sbabcock23)), who also wrote the
pytryfi library the TryFi client is derived from, and co-maintained by **Will Beeching**
([willbeeching](https://github.com/willbeeching)). Thanks to
**[disruptivepatternmaterial](https://github.com/disruptivepatternmaterial)**, whose fork first
removed the third-party reporting from pytryfi and was the starting point for 0.1.0. Licensed under
the Apache License 2.0, as the originals are; see [LICENSE](LICENSE).

## Disclaimer

An unofficial community project, with no affiliation to or endorsement from TryFi. "TryFi" and "Fi" are their trademarks, used here only to say what this connects to. It talks
to TryFi's undocumented API, which can change without notice. It was developed with AI assistance,
comes with no warranty, and you use it with your own account at your own risk.

It reads your own pets' data from your own account into your own Home Assistant, and changes only
the collar light and Lost Mode when you ask it to. Nothing goes through us or anyone else.

## Support

If this saved you a walk round the garden looking for the cat, consider
[buying me some AI tokens](https://buymeacoffee.com/willbeeching) ☕🤖. Entirely optional; bug
reports and stars are appreciated just as much.
