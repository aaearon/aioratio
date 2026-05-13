"""Fail loudly if ``bleak`` is missing rather than silently skipping BLE tests."""

from __future__ import annotations

import importlib.util


def test_bleak_is_installed() -> None:
    assert importlib.util.find_spec("bleak") is not None, (
        "bleak is not installed — the BLE test suite would silently skip. "
        "Install dev extras: pip install -e '.[dev,ble]'."
    )
