"""``aioratio`` must not import ``bleak`` for cloud-only installs."""

from __future__ import annotations

import importlib.util
import subprocess
import sys

import pytest


def test_top_level_import_does_not_import_bleak() -> None:
    """A fresh interpreter that imports aioratio should not load bleak."""
    code = (
        "import sys\n"
        "import aioratio  # noqa: F401\n"
        "assert 'bleak' not in sys.modules, 'aioratio top-level import pulled in bleak'\n"
    )
    res = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.returncode == 0, (
        f"subprocess failed (rc={res.returncode}):\nstdout: {res.stdout}\nstderr: {res.stderr}"
    )


@pytest.mark.skipif(
    importlib.util.find_spec("bleak") is None,
    reason="bleak not installed; the missing-bleak path is covered by the sibling test",
)
def test_ble_client_resolves_when_bleak_installed() -> None:
    """``aioratio.BleClient`` must be importable when bleak is present."""
    import aioratio

    assert aioratio.BleClient is not None
    assert aioratio.BleClient.__name__ == "BleClient"


def _drop_ble_modules() -> None:
    """Evict cached ``aioratio.ble*`` modules so the import-time guard re-runs."""
    for name in list(sys.modules):
        if name == "aioratio.ble" or name.startswith("aioratio.ble."):
            del sys.modules[name]


def test_ble_client_raises_without_bleak(monkeypatch) -> None:
    """When bleak is missing the lazy lookup must surface a helpful hint.

    Works in two scenarios:
      - bleak is genuinely uninstalled: ``aioratio.BleClient`` raises on
        first access because ``aioratio.ble`` import fails ``require_bleak()``.
      - bleak is installed: we evict any cached ``aioratio.ble`` modules and
        patch ``importlib.util.find_spec`` *before* triggering the lazy
        import, so the guard sees ``find_spec('bleak') is None``.
    """
    import aioratio

    _drop_ble_modules()

    # ``aioratio.ble._bleak_check.require_bleak`` calls
    # ``importlib.util.find_spec("bleak")``; pretending bleak is absent here
    # is sufficient to trigger the install-hint error path.
    def _no_spec(*args, **kwargs):  # noqa: ANN001, ANN002, ARG001
        return None

    monkeypatch.setattr(importlib.util, "find_spec", _no_spec)

    with pytest.raises(RuntimeError, match=r"aioratio\[ble\]"):
        _ = aioratio.BleClient

    # Evict the failed-import state so subsequent tests re-import cleanly.
    monkeypatch.undo()
    _drop_ble_modules()
