"""Cross-cutting BLE response helpers + ``SettableValue`` wrapper.

Inspiro IPC ``Get*Settings`` responses wrap every field in a "settable
value" envelope with metadata. The exact shape varies by field type:

* Enum field   : ``{value: str, isChangeAllowed: bool, allowedValues: [...]}``
* Numeric field: ``{value: int, isChangeAllowed: bool, lowerLimit: int, upperLimit: int}``
* String field : ``{value: str, isChangeAllowed: bool}``

This file exposes a single ``SettableValue`` dataclass that captures all
three shapes via optional fields. Each ``Get*Settings`` model decodes its
fields into ``SettableValue`` instances; ``Set*Update`` payloads still send
flat values (the wire is asymmetric).

Also exposes ``IPC_RESULT_SUCCESS`` / ``IPC_RESULT_FAILED`` / ``is_success``.
The real wire uses lowercase ``"success"`` (the v3.13.2 firmware hardware
walk on 2026-05-13 confirms this); the helper is case-insensitive for
future-firmware robustness.

Plus base64 helpers for the fields the charger encodes opaquely on the
wire (Wi-Fi SSID, OCPP central-system name + URL).
"""

from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
from typing import Any, Final, Self

IPC_RESULT_SUCCESS: Final[str] = "success"
IPC_RESULT_FAILED: Final[str] = "failed"


def is_success(result: str) -> bool:
    return result.lower() == IPC_RESULT_SUCCESS


@dataclass(slots=True)
class SettableValue:
    """Envelope used by every field in ``Get*Settings`` responses.

    See ``ChargePointIdentifierV2$$serializer.java`` for the closest
    structurally-similar Kotlin type in the decompile.
    """

    value: Any
    is_change_allowed: bool
    allowed_values: list[Any] | None = None
    lower_limit: int | None = None
    upper_limit: int | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            value=data.get("value"),
            is_change_allowed=bool(data.get("isChangeAllowed", False)),
            allowed_values=data.get("allowedValues"),
            lower_limit=data.get("lowerLimit"),
            upper_limit=data.get("upperLimit"),
        )


def b64_decode_text(value: str | None) -> str | None:
    """Decode a base64 string (e.g. Wi-Fi SSID, CPMS URL) to plain text.

    Returns ``None`` for ``None`` input, and falls back to the raw input
    when decoding fails (some firmware revisions may emit plain text).
    """
    if value is None:
        return None
    try:
        return base64.b64decode(value, validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError, ValueError):
        return value


def b64_encode_text(value: str | None) -> str | None:
    """Inverse of ``b64_decode_text`` — used when writing SSID/URL fields."""
    if value is None:
        return None
    return base64.b64encode(value.encode("utf-8")).decode("ascii")


__all__ = [
    "IPC_RESULT_SUCCESS",
    "IPC_RESULT_FAILED",
    "is_success",
    "SettableValue",
    "b64_decode_text",
    "b64_encode_text",
]
