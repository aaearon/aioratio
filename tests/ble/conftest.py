"""BLE test fixtures.

If ``bleak`` isn't installed the entire ``tests/ble/`` subtree is skipped;
``tests/ble/test_suite_runs.py`` then fails loudly so a CI environment that
forgot the ``[ble]`` / ``[dev]`` extras cannot silently merge with the BLE
suite missing.
"""

from __future__ import annotations

import pytest

pytest.importorskip("bleak")
