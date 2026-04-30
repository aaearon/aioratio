"""Exception hierarchy for aioratio."""
from __future__ import annotations


class RatioError(Exception):
    """Base error for aioratio."""


class RatioAuthError(RatioError):
    """Authentication / authorization failure."""


class RatioApiError(RatioError):
    """API returned an error response."""


class RatioRateLimitError(RatioApiError):
    """API rate limit exceeded."""


class RatioConnectionError(RatioError):
    """Network / connection failure."""
