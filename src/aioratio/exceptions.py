"""Exception hierarchy for aioratio."""

from __future__ import annotations


class RatioError(Exception):
    """Base error for aioratio."""


class RatioAuthError(RatioError):
    """Authentication / authorization failure."""


class RatioApiError(RatioError):
    """API returned an error response.

    The optional ``status`` attribute carries the HTTP status code of
    the failing response when raised by the transport layer; callers may
    use it to differentiate ``404 Not Found`` from ``500`` etc. It is
    ``None`` when the error did not originate from an HTTP response.
    """

    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.status: int | None = status


class RatioRateLimitError(RatioApiError):
    """API rate limit exceeded."""


class RatioConnectionError(RatioError):
    """Network / connection failure."""


class RatioBleError(RatioError):
    """Base error for the optional BLE client (``aioratio[ble]``)."""


class RatioBleConnectionError(RatioBleError):
    """BLE transport-level failure: scan, connect, GATT, bond."""


class RatioBleProtocolError(RatioBleError):
    """Inspiro IPC framing or response error (bad classname, decode, missing transaction)."""


class RatioBleNotBondedError(RatioBleError):
    """Operation requires a bonded link but the device is not bonded."""


class RatioBleUnsupportedCommandError(RatioBleError):
    """Command is not supported by the charger's reported protocol version."""
