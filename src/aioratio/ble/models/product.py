"""``GetProductInformation`` response.

Source: ``charger/data/data_source/ble/GetProductInformationResponse$$serializer.java``
plus its ``$ConnectivityController`` and ``$MainController`` inner descriptors.

Note: ``GetProductInformationRequest`` requires ``BASELINE_4_0_0`` (version 6).
The Phase 0 PoC observed a charger advertising version 3, which means this
command will be rejected with ``RatioBleUnsupportedCommandError`` on that
hardware — callers should treat ``ProductInformationResponse`` as a best-effort
read on newer firmware only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Self


@dataclass(slots=True)
class ConnectivityController:
    """Source: ``GetProductInformationResponse$ConnectivityController$$serializer.java``."""

    firmware_version: str | None = None
    hardware_version: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            firmware_version=data.get("firmwareVersion"),
            hardware_version=data.get("hardwareVersion"),
        )


@dataclass(slots=True)
class MainController:
    """Source: ``GetProductInformationResponse$MainController$$serializer.java``."""

    serial_number: str | None = None
    firmware_version: str | None = None
    hardware_version: str | None = None
    hardware_type: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            serial_number=data.get("serialNumber"),
            firmware_version=data.get("firmwareVersion"),
            hardware_version=data.get("hardwareVersion"),
            hardware_type=data.get("hardwareType"),
        )


@dataclass(slots=True)
class ProductInformationResponse:
    """Source: ``GetProductInformationResponse$$serializer.java``.

    Wire keys (in descriptor order): ``transaction, result,
    connectivityController, mainController``.
    """

    transaction: str
    result: str
    connectivity_controller: ConnectivityController | None = None
    main_controller: MainController | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        cc = data.get("connectivityController")
        mc = data.get("mainController")
        return cls(
            transaction=data["transaction"],
            result=data["result"],
            connectivity_controller=ConnectivityController.from_dict(cc)
            if isinstance(cc, dict)
            else None,
            main_controller=MainController.from_dict(mc) if isinstance(mc, dict) else None,
        )


__all__ = ["ConnectivityController", "MainController", "ProductInformationResponse"]
