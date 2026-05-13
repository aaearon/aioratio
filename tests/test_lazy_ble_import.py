"""``aioratio`` must not import ``bleak`` for cloud-only installs."""

from __future__ import annotations

import importlib
import subprocess
import sys


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


def test_ble_client_resolves_when_bleak_installed() -> None:
    """``aioratio.BleClient`` must be importable when bleak is present."""
    if importlib.util.find_spec("bleak") is None:
        # In CI without the [ble] extras this branch is exercised by
        # ``test_ble_client_raises_without_bleak`` below.
        return
    import aioratio

    assert aioratio.BleClient is not None
    assert aioratio.BleClient.__name__ == "BleClient"


def test_ble_client_raises_without_bleak(monkeypatch) -> None:
    """When bleak is missing the lazy lookup must surface a helpful hint."""
    import aioratio
    from aioratio.ble import _bleak_check

    monkeypatch.setattr(_bleak_check.importlib.util, "find_spec", lambda name: None)
    # Re-load aioratio.ble so the import-time check sees the patched find_spec.
    if "aioratio.ble" in sys.modules:
        del sys.modules["aioratio.ble"]
    if "aioratio.ble.client" in sys.modules:
        del sys.modules["aioratio.ble.client"]

    try:
        _ = aioratio.BleClient
    except RuntimeError as exc:
        assert "aioratio[ble]" in str(exc)
    else:  # pragma: no cover — defensive
        raise AssertionError("expected RuntimeError when bleak is absent")
