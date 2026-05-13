"""Wi-Fi scan / access-point / connect BLE payloads.

Sources (all under ``charger_onboarding/data/data_source/ble/``):
  - ``WifiScanResponse$$serializer.java`` — transaction, numberOfFoundNetworks, result
  - ``WifiAccessPointRequest$$serializer.java`` — transaction, index
  - ``WifiAccessPointResponse$$serializer.java`` — transaction, index, ssid, rssi, result
  - ``WifiConnectRequest$$serializer.java`` — transaction, ssid, password
  - ``WifiConnectResponse$$serializer.java`` — transaction, result

**SSID values are base64-encoded on the wire.** The 2026-05-13 v3.13.2 hardware
walk confirmed this on ``configuredSsid`` (and the same encoding is expected
on ``WifiAccessPointResponse.ssid``). The dataclasses below surface plain text
via ``ssid`` and keep the raw wire form in ``ssid_raw``. ``WifiConnectRequest``
re-encodes the SSID on the way out so callers can pass plain text.

WifiScan + WifiAccessPoint are paired: WifiScan returns the count, then the
caller iterates ``WifiAccessPointRequest(index=i)`` to pull each AP.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Self

from .common import b64_decode_text


@dataclass(slots=True)
class WifiScanResponse:
    transaction: str
    result: str
    number_of_found_networks: int = 0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            transaction=data["transaction"],
            result=data["result"],
            number_of_found_networks=int(data.get("numberOfFoundNetworks", 0)),
        )


@dataclass(slots=True)
class WifiAccessPoint:
    """One entry from the charger's last Wi-Fi scan.

    ``ssid`` is base64-decoded plain text; ``ssid_raw`` preserves the wire
    bytes for callers that need them.
    """

    transaction: str
    result: str
    index: int
    ssid: str | None = None
    ssid_raw: str | None = None
    rssi: int | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        ssid_raw = data.get("ssid")
        return cls(
            transaction=data["transaction"],
            result=data["result"],
            index=int(data["index"]),
            ssid=b64_decode_text(ssid_raw),
            ssid_raw=ssid_raw,
            rssi=int(data["rssi"]) if data.get("rssi") is not None else None,
        )


@dataclass(slots=True)
class WifiConnectResponse:
    transaction: str
    result: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(transaction=data["transaction"], result=data["result"])


__all__ = ["WifiScanResponse", "WifiAccessPoint", "WifiConnectResponse"]
