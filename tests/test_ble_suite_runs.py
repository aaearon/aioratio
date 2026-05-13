"""Fail loudly if ``bleak`` is missing rather than silently skipping BLE tests.

Lives outside ``tests/ble/`` so the subtree-level ``importorskip("bleak")`` in
``tests/ble/conftest.py`` cannot itself skip this guard.
"""

from __future__ import annotations

import importlib.util


def test_bleak_is_installed() -> None:
    assert importlib.util.find_spec("bleak") is not None, (
        "bleak is not installed — the BLE test suite would silently skip. "
        "Install dev extras: pip install -e '.[dev,ble]'."
    )
