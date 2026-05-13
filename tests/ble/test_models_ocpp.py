"""``OcppStatusResponse`` + ``BackendStatusResponse``."""

from __future__ import annotations

import pytest

from aioratio.ble.models import (
    BackendStatusResponse,
    OcppCpms,
    OcppStatusResponse,
    b64_encode_text,
)

from ._serializer_refs import SERIALIZER_KEYS


def _attr_path(obj: object, path: str) -> object:
    for name in path.split("."):
        obj = getattr(obj, name)
    return obj


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


@pytest.mark.parametrize(
    ("serializer_name", "model", "sample", "attribute_path", "expected"),
    [
        (
            "GetOcppStatusResponse",
            OcppStatusResponse,
            {
                "transaction": "t",
                "result": "success",
                "connected": True,
                "enabled": True,
                "cpms": {
                    "centralSystem": b64_encode_text("TestCpms"),
                    "url": b64_encode_text("wss://ocpp.example.com"),
                },
            },
            "cpms.central_system",
            "TestCpms",
        ),
        (
            "InstallerOcppSettingsV2Cpms",
            OcppCpms,
            {
                "centralSystem": b64_encode_text("TestCpms"),
                "url": b64_encode_text("wss://ocpp.example.com"),
            },
            "url",
            "wss://ocpp.example.com",
        ),
        (
            "GetBackendStatusResponse",
            BackendStatusResponse,
            {"transaction": "t", "result": "success", "connected": True},
            "connected",
            True,
        ),
    ],
)
def test_ocpp_backend_keys_match_serializer(
    serializer_name: str,
    model: object,
    sample: dict[str, object],
    attribute_path: str,
    expected: object,
) -> None:
    assert tuple(sample) == SERIALIZER_KEYS[serializer_name]

    parsed = model.from_dict(sample)

    assert _attr_path(parsed, attribute_path) == expected
