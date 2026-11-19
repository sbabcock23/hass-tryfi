"""What can go wrong talking to TryFi, told apart so each is handled right."""

from __future__ import annotations


class TryFiError(Exception):
    """Anything that stopped a request to TryFi from giving an answer."""


class TryFiAuthError(TryFiError):
    """TryFi refused the email and password, or the session they opened."""


class TryFiConnectionError(TryFiError):
    """TryFi could not be reached, timed out, or answered with a server error."""


class TryFiCommandError(TryFiError):
    """TryFi answered a change to the collar with an error: it was not made."""
