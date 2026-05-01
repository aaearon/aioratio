"""aioratio — async Python client for the Ratio EV Charging cloud API."""
from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version as _meta_version

from .client import RatioClient
from .exceptions import (
    RatioApiError,
    RatioAuthError,
    RatioConnectionError,
    RatioError,
    RatioRateLimitError,
)
from .token_store import JsonFileTokenStore, MemoryTokenStore, TokenBundle, TokenStore

__all__ = [
    "RatioClient",
    "RatioError",
    "RatioAuthError",
    "RatioApiError",
    "RatioRateLimitError",
    "RatioConnectionError",
    "TokenStore",
    "TokenBundle",
    "MemoryTokenStore",
    "JsonFileTokenStore",
]

try:
    __version__ = _meta_version("aioratio")
except PackageNotFoundError:
    __version__ = "0.0.0"
