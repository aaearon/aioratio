"""aioratio — async Python client for the Ratio EV Charging cloud API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .client import RatioClient
from .const import __version__
from .exceptions import (
    RatioApiError,
    RatioAuthError,
    RatioBleConnectionError,
    RatioBleError,
    RatioBleNotBondedError,
    RatioBleProtocolError,
    RatioBleUnsupportedCommandError,
    RatioConnectionError,
    RatioError,
    RatioRateLimitError,
)
from .token_store import JsonFileTokenStore, MemoryTokenStore, TokenBundle, TokenStore

if TYPE_CHECKING:
    from .ble import BleClient  # re-export for type checkers

__all__ = [
    "RatioClient",
    "RatioError",
    "RatioAuthError",
    "RatioApiError",
    "RatioRateLimitError",
    "RatioConnectionError",
    "RatioBleError",
    "RatioBleConnectionError",
    "RatioBleProtocolError",
    "RatioBleNotBondedError",
    "RatioBleUnsupportedCommandError",
    "BleClient",
    "TokenStore",
    "TokenBundle",
    "MemoryTokenStore",
    "JsonFileTokenStore",
    "__version__",
]


def __getattr__(name: str) -> Any:
    """Lazy re-export of ``BleClient`` so importing :mod:`aioratio` does not
    pull in ``bleak`` for cloud-only installs.

    Raises ``RuntimeError`` with an install hint if the ``[ble]`` extras are
    missing.
    """

    if name == "BleClient":
        from .ble import BleClient as _BleClient

        return _BleClient
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
