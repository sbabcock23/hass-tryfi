"""A typed async client for TryFi, written for this integration.

Derived from pytryfi by Steve Babcock (Apache 2.0); see ORIGIN.md for what
was kept, what changed, and why.
"""

from .client import TryFiClient
from .errors import (
    TryFiAuthError,
    TryFiCommandError,
    TryFiConnectionError,
    TryFiError,
)
from .models import Base, Collar, LedColor, Pet

__all__ = [
    "Base",
    "Collar",
    "LedColor",
    "Pet",
    "TryFiAuthError",
    "TryFiClient",
    "TryFiCommandError",
    "TryFiConnectionError",
    "TryFiError",
]
