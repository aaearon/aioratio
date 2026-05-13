"""``OcppStatusResponse`` + ``BackendStatusResponse``."""

from __future__ import annotations

from aioratio.ble.models import (
    BackendStatusResponse,
    OcppStatusResponse,
    b64_encode_text,
)


def test_ocpp_status_decodes_base64_cpms() -> None:
    cs_plain = "TestCpms"
    url_plain = "wss://ocpp.example.com"
    cs_b64 = b64_encode_text(cs_plain)
    url_b64 = b64_encode_text(url_plain)
    raw = {
        "transaction": "t",
        "result": "success",
        "enabled": True,
        "cpms": {"centralSystem": cs_b64, "url": url_b64},
        "connected": True,
    }
    parsed = OcppStatusResponse.from_dict(raw)
    assert parsed.enabled is True
    assert parsed.connected is True
    assert parsed.cpms is not None
    assert parsed.cpms.central_system == cs_plain
    assert parsed.cpms.url == url_plain
    # Raw stays available for callers who want it.
    assert parsed.cpms.central_system_raw == cs_b64


def test_backend_status_response() -> None:
    raw = {"transaction": "t", "result": "success", "connected": True}
    parsed = BackendStatusResponse.from_dict(raw)
    assert parsed.connected is True
