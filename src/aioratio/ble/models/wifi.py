"""Wi-Fi scan / access-point / connect BLE payloads.

Sources (all under ``charger_onboarding/data/data_source/ble/``):
  - ``WifiScanResponse$$serializer.java`` — transaction, numberOfFoundNetworks, result
  - ``WifiAccessPointRequest$$serializer.java`` — transaction, index
  - ``WifiAccessPointResponse$$serializer.java`` — transaction, index, ssid, rssi, result
  - ``WifiConnectRequest$$serializer.java`` — transaction, ssid, password
  - ``WifiConnectResponse$$serializer.java`` — transaction, result

WifiScan + WifiAccessPoint are paired: WifiScan returns the count, then the
caller iterates ``WifiAccessPointRequest(index=i)`` to pull each AP.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Self


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
    """One entry from the charger's last Wi-Fi scan."""

    transaction: str
    result: str
    index: int
    ssid: str | None = None
    rssi: int | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            transaction=data["transaction"],
            result=data["result"],
            index=int(data["index"]),
            ssid=data.get("ssid"),
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
