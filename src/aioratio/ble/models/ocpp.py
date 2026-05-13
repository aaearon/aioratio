"""``GetOcppStatus`` + ``GetBackendStatus`` responses.

Sources:
  - ``charger/data/data_source/ble/GetOcppStatusResponse$$serializer.java``
    — transaction, result, connected, enabled, cpms
  - ``charger/data/data_source/ble/GetBackendStatusResponse$$serializer.java``
    — transaction, result, connected

The 2026-05-13 v3.13.2 wire capture confirms ``cpms`` has nested
``centralSystem`` and ``url`` fields, both base64-encoded
(e.g. ``"SG9tZUFzc2lzdGFudA=="`` decodes to ``"HomeAssistant"``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Self

from .common import b64_decode_text


@dataclass(slots=True)
class OcppCpms:
    """Central-system identity for the active OCPP backend.

    Wire keys: ``centralSystem``, ``url`` — both base64-encoded.
    Decoded plain text surfaces on ``central_system`` / ``url``; raw wire
    bytes live in the ``*_raw`` companions.
    """

    central_system: str | None = None
    central_system_raw: str | None = None
    url: str | None = None
    url_raw: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        cs = data.get("centralSystem")
        u = data.get("url")
        return cls(
            central_system=b64_decode_text(cs),
            central_system_raw=cs,
            url=b64_decode_text(u),
            url_raw=u,
        )


@dataclass(slots=True)
class OcppStatusResponse:
    transaction: str
    result: str
    enabled: bool = False
    connected: bool = False
    cpms: OcppCpms | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        cpms = data.get("cpms")
        return cls(
            transaction=data["transaction"],
            result=data["result"],
            enabled=bool(data.get("enabled", False)),
            connected=bool(data.get("connected", False)),
            cpms=OcppCpms.from_dict(cpms) if isinstance(cpms, dict) else None,
        )


@dataclass(slots=True)
class BackendStatusResponse:
    transaction: str
    result: str
    connected: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            transaction=data["transaction"],
            result=data["result"],
            connected=bool(data.get("connected", False)),
        )


__all__ = ["OcppCpms", "OcppStatusResponse", "BackendStatusResponse"]
