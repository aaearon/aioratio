"""Lazy guard so the cloud-only install path doesn't pull in bleak."""

from __future__ import annotations

import importlib.util

_INSTALL_HINT = "aioratio[ble] extras are not installed. Install with: pip install 'aioratio[ble]'"


def require_bleak() -> None:
    """Raise ``RuntimeError`` with an install hint if ``bleak`` is missing."""
    if importlib.util.find_spec("bleak") is None:
        raise RuntimeError(_INSTALL_HINT)
