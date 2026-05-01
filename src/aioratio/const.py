"""Constants for the Ratio EV Charging cloud API."""
from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version as _meta_version

COGNITO_REGION: str = "eu-west-1"
COGNITO_CLIENT_ID: str = "78cs05mc0hc5ibqv1tui22n962"
COGNITO_USER_POOL_ID: str = "eu-west-1_mH4sFjLoF"
COGNITO_IDENTITY_POOL_ID: str = "eu-west-1:893982c4-6d19-4180-b7d2-468a03595496"

API_BASE_URL: str = "https://8q4y72fwo3.execute-api.eu-west-1.amazonaws.com/prod"

try:
    _VERSION = _meta_version("aioratio")
except PackageNotFoundError:
    _VERSION = "0.0.0"

USER_AGENT: str = f"aioratio/{_VERSION}"
