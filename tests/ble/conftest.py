"""BLE test fixtures.

If ``bleak`` isn't installed the entire ``tests/ble/`` subtree is skipped.
The fail-loud guard against a silent skip lives at
``tests/test_ble_suite_runs.py`` (outside this subtree) so the
``importorskip`` below cannot suppress it.
"""

from __future__ import annotations

import pytest

pytest.importorskip("bleak")
