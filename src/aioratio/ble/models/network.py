"""``GetNetworkStatus`` response with nested wifi/ethernet/ipv4 objects.

Sources:
  - ``charger/data/data_source/ble/GetNetworkStatusResponse$$serializer.java``
  - ``$Wifi$$serializer.java`` — connected, configuredSsid, rssi, ipv4
  - ``$Ethernet$$serializer.java`` — connected, ipv4
  - ``$Ipv4$$serializer.java`` — address, netmask, gateway

Wire format confirmed against v3.13.2 firmware on 2026-05-13. ``configuredSsid``
is base64-encoded; surfaced decoded as ``ssid`` with the raw form in ``ssid_raw``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Self

from .common import b64_decode_text


@dataclass(slots=True)
class Ipv4Info:
    """Source: ``GetNetworkStatusResponse$Ipv4$$serializer.java``."""

    address: str | None = None
    netmask: str | None = None
    gateway: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            address=data.get("address"),
            netmask=data.get("netmask"),
            gateway=data.get("gateway"),
        )


@dataclass(slots=True)
class WifiInfo:
    """Source: ``GetNetworkStatusResponse$Wifi$$serializer.java``."""

    connected: bool = False
    ssid: str | None = None
    ssid_raw: str | None = None
    rssi: int | None = None
    ipv4: Ipv4Info | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        ssid_raw = data.get("configuredSsid")
        ip = data.get("ipv4")
        return cls(
            connected=bool(data.get("connected", False)),
            ssid=b64_decode_text(ssid_raw),
            ssid_raw=ssid_raw,
            rssi=int(data["rssi"]) if data.get("rssi") is not None else None,
            ipv4=Ipv4Info.from_dict(ip) if isinstance(ip, dict) else None,
        )


@dataclass(slots=True)
class EthernetInfo:
    """Source: ``GetNetworkStatusResponse$Ethernet$$serializer.java``."""

    connected: bool = False
    ipv4: Ipv4Info | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        ip = data.get("ipv4")
        return cls(
            connected=bool(data.get("connected", False)),
            ipv4=Ipv4Info.from_dict(ip) if isinstance(ip, dict) else None,
        )


@dataclass(slots=True)
class NetworkStatusResponse:
    """Source: ``GetNetworkStatusResponse$$serializer.java``.

    Wire keys: ``transaction, result, isTimeSynchronized, connectionMedium,
    wifi, ethernet``. ``connectionMedium`` observed values: ``"wifi"``,
    ``"ethernet"``.
    """

    transaction: str
    result: str
    is_time_synchronized: bool = False
    connection_medium: str | None = None
    wifi: WifiInfo | None = None
    ethernet: EthernetInfo | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        wifi = data.get("wifi")
        eth = data.get("ethernet")
        return cls(
            transaction=data["transaction"],
            result=data["result"],
            is_time_synchronized=bool(data.get("isTimeSynchronized", False)),
            connection_medium=data.get("connectionMedium"),
            wifi=WifiInfo.from_dict(wifi) if isinstance(wifi, dict) else None,
            ethernet=EthernetInfo.from_dict(eth) if isinstance(eth, dict) else None,
        )


__all__ = ["NetworkStatusResponse", "WifiInfo", "EthernetInfo", "Ipv4Info"]
