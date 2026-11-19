"""Constants for the TryFi integration."""

from __future__ import annotations

from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "tryfi"
PLATFORMS: Final = [
    Platform.BINARY_SENSOR,
    Platform.DEVICE_TRACKER,
    Platform.LIGHT,
    Platform.SELECT,
    Platform.SENSOR,
]

CONF_USERNAME: Final = "username"
CONF_PASSWORD: Final = "password"
CONF_POLLING_RATE: Final = "polling"


def account_id(username: str) -> str:
    """A login email as compared between entries: case and spaces aside."""
    return username.strip().lower()


# Upstream defaulted to 10 seconds, which is six full refreshes a minute against
# TryFi's cloud: a pet list, then a location, activity and rest query per pet.
# The collar itself reports far less often than that, so a faster poll mostly
# fetches the same answer again. Entries created upstream with a lower value
# are raised to the floor rather than rejected, so they keep loading.
DEFAULT_POLLING_RATE: Final = 60
MIN_POLLING_RATE: Final = 60

SENSOR_STATS_BY_TIME: Final = ["DAILY", "WEEKLY", "MONTHLY"]
SENSOR_STATS_BY_TYPE: Final = ["STEPS", "DISTANCE", "SLEEP", "NAP"]
