"""Pets, collars and bases, read from TryFi's answers.

Everything here is parsed defensively, because TryFi describes the same
things differently from one collar or account to the next. Each rule below
is an incident from upstream's issue tracker (sbabcock23/hass-tryfi), and
docs/UPSTREAM_ISSUES.md has the full list.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

LOGGER = logging.getLogger(__name__)

PERIODS = ("daily", "weekly", "monthly")
MODE_NORMAL = "NORMAL"
MODE_LOST = "LOST_DOG"
ACTIVITY_WALK = "OngoingWalk"

JSON = dict[str, Any]


def obj(value: Any) -> JSON:
    """The value as an object, or TypeError: TryFi sends null for any field.

    Reading .get() off a null raised AttributeError, which nothing expected,
    and `info: null` failed the whole integration at setup.
    """
    if not isinstance(value, dict):
        raise TypeError(f"expected an object, got {type(value).__name__}")
    return value


def identity(value: Any) -> str | None:
    """A pet, collar or base id as text, or None when there is no usable one.

    Ids are what devices are matched on, so they are compared as text: an id
    sent as a number one time and a string the next is the same id. Null, an
    empty string or anything else is no id at all, and must never stand in
    for one: it once became a device called "None", and its absence once
    removed the real device (review of c2adf91).
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str) and value.strip():
        return value
    return None


def dig(value: Any, *keys: str) -> Any:
    """value[k1][k2]..., or None as soon as a level is not an object."""
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


@dataclass(frozen=True, slots=True)
class LedColor:
    code: int
    hex: str
    name: str


@dataclass(slots=True)
class Collar:
    """The collar's state. Every field defaults to None: "not reported".

    Upstream set these one by one inside a single try, so the first field a
    collar did not report left every later one undefined, and Home Assistant
    raised AttributeError on each refresh (#69 `_ledOn`, #100 `_mode`).
    """

    device_id: str
    module_id: str | None = None
    build_id: str | None = None
    battery_percent: int | None = None
    # Older collars do not report it at all; upstream read that as not charging.
    charging: bool = False
    mode: str | None = None
    led_enabled: bool | None = None
    led_off_at: datetime | None = None
    led_color_name: str | None = None
    led_color_hex: str | None = None
    available_led_colors: list[LedColor] = field(default_factory=list)
    connection_type: str | None = None
    connection_date: datetime | None = None
    signal_strength: int | None = None
    connected_base_id: str | None = None
    connected_person: str | None = None

    @property
    def is_lost(self) -> bool | None:
        return None if self.mode is None else self.mode == MODE_LOST

    @property
    def led_on(self) -> bool | None:
        """Whether the LED is lit now.

        TryFi keeps reporting the LED as enabled after it has switched itself
        off at its off time, so the time decides. No off time counts as off,
        as it did in pytryfi.
        """
        if self.led_enabled is None:
            return None
        if not self.led_enabled or self.led_off_at is None:
            return False
        return datetime.now(UTC) < self.led_off_at

    def update(self, device: JSON) -> None:
        """Take what TryFi reported; a group of fields it left out keeps its
        previous values. The Fi Mini and Series 3+ report less than others."""
        for group in (
            self._read_module,
            self._read_info,
            self._read_operation,
            self._read_led_color,
            self._read_connection,
            self._read_led_colors,
        ):
            try:
                group(device)
            except (KeyError, TypeError, ValueError) as err:
                LOGGER.debug(
                    "Collar %s: %s not reported (%r)",
                    self.device_id,
                    group.__name__,
                    err,
                )

    def _read_module(self, device: JSON) -> None:
        self.module_id = device["moduleId"]

    def _read_info(self, device: JSON) -> None:
        info = obj(device["info"])
        self.build_id = info.get("buildId")
        battery = info.get("batteryPercent")
        self.battery_percent = None if battery is None else int(battery)
        self.charging = bool(info.get("isCharging", False))

    def _read_operation(self, device: JSON) -> None:
        params = obj(device["operationParams"])
        self.mode = params.get("mode")
        self.led_enabled = bool(params.get("ledEnabled"))
        self.led_off_at = parse_time(params.get("ledOffAt"))

    def _read_led_color(self, device: JSON) -> None:
        color = obj(device["ledColor"])
        self.led_color_name = color["name"]
        self.led_color_hex = color["hexCode"]

    def _read_connection(self, device: JSON) -> None:
        state = obj(device["lastConnectionState"])
        self.connection_type = state["__typename"]
        # The detail behind the type, which upstream flattened into one string
        # or dropped: which base, whose phone, what signal (#60).
        self.signal_strength = state.get("signalStrengthPercent")
        self.connected_base_id = identity(dig(state, "chargingBase", "id"))
        self.connected_person = (state.get("user") or {}).get("firstName")
        self.connection_date = parse_time(state.get("date"))

    def _read_led_colors(self, device: JSON) -> None:
        self.available_led_colors = [
            LedColor(int(color["ledColorCode"]), color["hexCode"], color["name"])
            for color in device["availableLedColors"] or []
        ]


@dataclass(slots=True)
class Pet:
    pet_id: str
    collar: Collar
    name: str | None = None
    breed: str | None = None
    photo_url: str | None = None
    activity_type: str | None = None
    area_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    activity_start: datetime | None = None
    place_name: str | None = None
    place_address: str | None = None
    # By period ("daily", "weekly", "monthly"). A period TryFi did not report
    # is absent, which reads as unknown.
    steps: dict[str, int] = field(default_factory=dict)
    step_goal: dict[str, int] = field(default_factory=dict)
    distance_m: dict[str, float] = field(default_factory=dict)
    # None when TryFi sent no summary for the period: 0 there would make a
    # running total look like a reset to Home Assistant's statistics.
    sleep_s: dict[str, int | None] = field(default_factory=dict)
    nap_s: dict[str, int | None] = field(default_factory=dict)

    @classmethod
    def from_profile(cls, profile: JSON) -> Pet:
        """A pet from the households answer. Raises when there is no collar.

        Upstream compared `device` with the string "None", but TryFi sends
        null for a pet without a collar (a Nano chip, a cat, a shared pet),
        and the TypeError abandoned every pet on the account: "only the
        bases show up" (#61, #62, #67, #87, #96, #99, #102).
        """
        pet_id = identity(profile.get("id"))
        if pet_id is None:
            raise TypeError("a pet without an id")
        device = profile.get("device")
        device_id = identity(dig(device, "id"))
        if not isinstance(device, dict) or device_id is None:
            raise NoCollar(profile.get("name"))
        collar = Collar(device_id=device_id)
        collar.update(device)
        photo = dig(profile, "photos", "first", "image", "fullSize")
        return cls(
            pet_id=pet_id,
            collar=collar,
            name=profile.get("name"),
            breed=dig(profile, "breed", "name"),
            photo_url=photo or None,
        )

    def take_location(self, activity: JSON) -> None:
        activity = obj(activity)
        self.activity_type = activity["__typename"]
        self.area_name = activity.get("areaName")
        try:
            if self.activity_type == ACTIVITY_WALK:
                # A walk can start before its first position is in; the end of
                # its path is a better fix than none.
                positions = activity.get("positions") or []
                if positions:
                    position = positions[-1]["position"]
                else:
                    position = (activity.get("path") or [])[-1]
            else:
                position = activity["position"]
            self.latitude = float(position["latitude"])
            self.longitude = float(position["longitude"])
            self.activity_start = parse_time(activity.get("start"))
        except (KeyError, TypeError, ValueError, IndexError):
            # No fix yet: the tracker shows unknown, not an error.
            LOGGER.debug("Pet %s has no position yet", self.pet_id)
        # "place": null while resting somewhere that is not a saved place.
        place = activity.get("place")
        if isinstance(place, dict):
            self.place_name = place.get("name")
            self.place_address = place.get("address")
        else:
            self.place_name = self.place_address = None

    def take_activity(self, summary: JSON) -> None:
        # Distance in metres. Each period on its own, so one TryFi leaves out
        # does not cost the other two.
        summary = obj(summary)
        for period in PERIODS:
            stat = summary.get(f"{period}Stat")
            if not stat:
                continue
            self.step_goal[period] = int(stat["stepGoal"])
            self.steps[period] = int(stat["totalSteps"])
            self.distance_m[period] = float(stat["totalDistance"])

    def take_rest(self, summary: JSON) -> None:
        # Seconds. A summary with no SLEEP or NAP entry is 0; no summary at all
        # is None.
        for period in PERIODS:
            sleep: int | None = None
            nap: int | None = None
            try:
                amounts = summary[f"{period}Stat"]["restSummaries"][0]["data"][
                    "sleepAmounts"
                ]
            except (KeyError, TypeError, IndexError):
                pass
            else:
                sleep = nap = 0
                for amount in amounts or []:
                    if amount["type"] == "SLEEP":
                        sleep = int(amount["duration"])
                    elif amount["type"] == "NAP":
                        nap = int(amount["duration"])
            self.sleep_s[period] = sleep
            self.nap_s[period] = nap

    def carry_over(self, previous: Pet, group: str) -> None:
        """Keep the previous refresh's readings for a group whose query failed."""
        for name in _GROUPS[group]:
            setattr(self, name, getattr(previous, name))


_GROUPS = {
    "location": (
        "activity_type",
        "area_name",
        "latitude",
        "longitude",
        "activity_start",
        "place_name",
        "place_address",
    ),
    "activity": ("steps", "step_goal", "distance_m"),
    "rest": ("sleep_s", "nap_s"),
}


@dataclass(slots=True)
class Base:
    """A charging base. Fields read with .get: a base without some of them
    failed the whole sensor platform upstream (#93)."""

    base_id: str
    name: str
    online: bool | None = None
    online_quality: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    network_name: str | None = None

    @classmethod
    def from_json(cls, base: JSON) -> Base:
        base = obj(base)
        base_id = identity(base.get("baseId"))
        if base_id is None:
            raise TypeError("a base without an id")
        position = base.get("position")
        position = position if isinstance(position, dict) else {}
        return cls(
            base_id=base_id,
            name=base.get("name") or base_id,
            online=base.get("online"),
            online_quality=base.get("onlineQuality"),
            latitude=position.get("latitude"),
            longitude=position.get("longitude"),
            network_name=base.get("networkName"),
        )


class NoCollar(Exception):
    """A pet on the account with no collar to read."""
