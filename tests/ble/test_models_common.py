"""``SettableValue`` wrapper + base64 helpers + result-case helper."""

from __future__ import annotations

from aioratio.ble.models import (
    IPC_RESULT_FAILED,
    IPC_RESULT_SUCCESS,
    SettableValue,
    b64_decode_text,
    b64_encode_text,
    is_success,
)


def test_result_constants_are_lowercase() -> None:
    assert IPC_RESULT_SUCCESS == "success"
    assert IPC_RESULT_FAILED == "failed"


def test_is_success_is_case_insensitive() -> None:
    # Real wire is lowercase per 2026-05-13 walk, but stay defensive.
    assert is_success("success") is True
    assert is_success("Success") is True
    assert is_success("SUCCESS") is True
    assert is_success("failed") is False
    assert is_success("anything") is False


def test_settable_value_enum_shape() -> None:
    raw = {
        "value": "Auto",
        "isChangeAllowed": True,
        "allowedValues": ["Manual", "Auto"],
    }
    sv = SettableValue.from_dict(raw)
    assert sv.value == "Auto"
    assert sv.is_change_allowed is True
    assert sv.allowed_values == ["Manual", "Auto"]
    assert sv.lower_limit is None
    assert sv.upper_limit is None


def test_settable_value_numeric_shape() -> None:
    raw = {"value": 6, "isChangeAllowed": True, "lowerLimit": 6, "upperLimit": 16}
    sv = SettableValue.from_dict(raw)
    assert sv.value == 6
    assert sv.lower_limit == 6
    assert sv.upper_limit == 16
    assert sv.allowed_values is None


def test_settable_value_string_shape() -> None:
    raw = {"value": "Europe/Amsterdam", "isChangeAllowed": True}
    sv = SettableValue.from_dict(raw)
    assert sv.value == "Europe/Amsterdam"
    assert sv.is_change_allowed is True
    assert sv.allowed_values is None
    assert sv.lower_limit is None


def test_b64_roundtrip() -> None:
    # Known base64 fixture — "TestNet" round-trips to "VGVzdE5ldA==".
    assert b64_decode_text("VGVzdE5ldA==") == "TestNet"
    assert b64_encode_text("TestNet") == "VGVzdE5ldA=="
    assert b64_decode_text(None) is None
    assert b64_encode_text(None) is None


def test_b64_decode_raises_on_invalid_input_in_strict_mode() -> None:
    """Default ``strict=True`` surfaces firmware drift instead of masking it."""
    import pytest

    from aioratio.exceptions import RatioBleProtocolError

    with pytest.raises(RatioBleProtocolError):
        b64_decode_text("plain-text")


def test_b64_decode_falls_back_to_raw_when_not_strict() -> None:
    """Permissive mode accepts plain text (older / divergent firmware)."""
    assert b64_decode_text("plain-text", strict=False) == "plain-text"
