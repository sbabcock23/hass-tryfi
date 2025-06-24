"""Constants for the TryFi integration."""
from __future__ import annotations

from typing import Final

DOMAIN: Final = "tryfi"

# Configuration
CONF_USERNAME: Final = "username"
CONF_PASSWORD: Final = "password"
CONF_POLLING_RATE: Final = "polling"
DEFAULT_POLLING_RATE: Final = 10

# Sensor constants
SENSOR_STATS_BY_TIME: Final = ["DAILY", "WEEKLY", "MONTHLY"]
SENSOR_STATS_BY_TYPE: Final = ["STEPS", "DISTANCE", "SLEEP", "NAP"]

# Device info
MANUFACTURER: Final = "TryFi"
MODEL: Final = "Smart Dog Collar"