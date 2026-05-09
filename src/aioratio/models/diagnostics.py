"""Charger diagnostics dataclass models.

Source: ``ChargerDiagnosticsDTO.kt`` (charger/domain/model) and
``ChargerInformationCloudDataSource.java`` (path: status?id=diagnostics).

All fields are Optional and permissive — missing keys yield None rather
than raising. No ``to_dict`` is provided because these models are read-only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Self


@dataclass(slots=True)
class Ipv4:
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
class WifiStatus:
    connected: bool | None = None
    ipv4_reported_if_connected: bool | None = None
    ipv4: Ipv4 | None = None
    ssid: str | None = None
    rssi: int | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        ipv4_raw = data.get("ipv4")
        return cls(
            connected=data.get("connected"),
            ipv4_reported_if_connected=data.get("ipv4ReportedIfConnected"),
            ipv4=Ipv4.from_dict(ipv4_raw) if isinstance(ipv4_raw, dict) else None,
            ssid=data.get("configuredSsid") or data.get("ssid"),
            rssi=_as_int(data.get("rssi")),
        )


@dataclass(slots=True)
class EthernetStatus:
    connected: bool | None = None
    ipv4_reported_if_connected: bool | None = None
    ipv4: Ipv4 | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        ipv4_raw = data.get("ipv4")
        return cls(
            connected=data.get("connected"),
            ipv4_reported_if_connected=data.get("ipv4ReportedIfConnected"),
            ipv4=Ipv4.from_dict(ipv4_raw) if isinstance(ipv4_raw, dict) else None,
        )


@dataclass(slots=True)
class NetworkStatus:
    is_time_synchronized: bool | None = None
    connection_medium: str | None = None
    wifi: WifiStatus | None = None
    ethernet: EthernetStatus | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        wifi_raw = data.get("wifi")
        eth_raw = data.get("ethernet")
        medium_raw = data.get("connectionMedium")
        return cls(
            is_time_synchronized=data.get("isTimeSynchronized"),
            connection_medium=medium_raw if isinstance(medium_raw, str) else None,
            wifi=WifiStatus.from_dict(wifi_raw) if isinstance(wifi_raw, dict) else None,
            ethernet=EthernetStatus.from_dict(eth_raw) if isinstance(eth_raw, dict) else None,
        )


@dataclass(slots=True)
class ConnectivityController:
    firmware_version: str | None = None
    hardware_version: str | None = None
    serial_number: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            firmware_version=data.get("firmwareVersion"),
            hardware_version=data.get("hardwareVersion"),
            serial_number=data.get("serialNumber"),
        )


@dataclass(slots=True)
class MainController:
    firmware_version: str | None = None
    hardware_type: str | None = None
    hardware_version: str | None = None
    serial_number: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            firmware_version=data.get("firmwareVersion"),
            hardware_type=data.get("hardwareType"),
            hardware_version=data.get("hardwareVersion"),
            serial_number=data.get("serialNumber"),
        )


@dataclass(slots=True)
class ProductInformation:
    connectivity_controller: ConnectivityController | None = None
    main_controller: MainController | None = None
    # ``app`` (mobile app version) is intentionally excluded — not useful for HA.

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        cc_raw = data.get("connectivityController")
        mc_raw = data.get("mainController")
        return cls(
            connectivity_controller=ConnectivityController.from_dict(cc_raw)
            if isinstance(cc_raw, dict)
            else None,
            main_controller=MainController.from_dict(mc_raw) if isinstance(mc_raw, dict) else None,
        )


@dataclass(slots=True)
class BackendStatus:
    connected: bool | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(connected=data.get("connected"))


@dataclass(slots=True)
class OcppDiagnosticStatus:
    connected: bool | None = None
    enabled: bool | None = None
    cpms_name: str | None = None
    cpms_url: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        cpms_raw = data.get("cpms")
        cpms_name: str | None = None
        cpms_url: str | None = None
        if isinstance(cpms_raw, dict):
            cpms_name = cpms_raw.get("name")
            cpms_url = cpms_raw.get("url")
        return cls(
            connected=data.get("connected"),
            enabled=data.get("enabled"),
            cpms_name=cpms_name,
            cpms_url=cpms_url,
        )


@dataclass(slots=True)
class ChargerDiagnostics:
    product_information: ProductInformation | None = None
    network_status: NetworkStatus | None = None
    backend_status: BackendStatus | None = None
    ocpp_status: OcppDiagnosticStatus | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        pi_raw = data.get("productInformation")
        ns_raw = data.get("networkStatus")
        bs_raw = data.get("backendStatus")
        os_raw = data.get("ocppStatus")
        return cls(
            product_information=ProductInformation.from_dict(pi_raw)
            if isinstance(pi_raw, dict)
            else None,
            network_status=NetworkStatus.from_dict(ns_raw) if isinstance(ns_raw, dict) else None,
            backend_status=BackendStatus.from_dict(bs_raw) if isinstance(bs_raw, dict) else None,
            ocpp_status=OcppDiagnosticStatus.from_dict(os_raw)
            if isinstance(os_raw, dict)
            else None,
        )


def _as_int(v: Any) -> int | None:
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None
