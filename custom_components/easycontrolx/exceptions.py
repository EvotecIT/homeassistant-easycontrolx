from __future__ import annotations


class EasyControlXError(Exception):
    """Base EasyControlX integration exception."""


class CannotConnect(EasyControlXError):
    """Raised when the host cannot be reached."""


class InvalidAuth(EasyControlXError):
    """Raised when the stored token is invalid."""


class ApiError(EasyControlXError):
    """Raised when the host returns an unexpected API error."""


class PairingPending(EasyControlXError):
    """Raised when pairing is still waiting for host-side approval."""


class PairingExpired(EasyControlXError):
    """Raised when the pairing session is no longer valid."""

