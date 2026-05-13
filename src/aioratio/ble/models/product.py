"""``GetProductInformation`` response.

Source: ``charger/data/data_source/ble/GetProductInformationResponse$$serializer.java``
plus its ``$ConnectivityController`` and ``$MainController`` inner descriptors.

The Kotlin descriptors omit some fields the v3.13.2 firmware actually emits
on the wire (notably ``connectivityController.serialNumber``). Every field
below is annotated with the source — descriptor vs hardware walk.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Self


@dataclass(slots=True)
class ConnectivityController:
    """Source: ``$ConnectivityController$$serializer.java`` + 2026-05-13 walk.

    Descriptor lists ``firmwareVersion, hardwareVersion``. The v3.13.2 walk
    also returned ``serialNumber`` so we accept and surface it.
    """

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
    """Source: ``$MainController$$serializer.java`` + 2026-05-13 walk.

    Descriptor lists ``serialNumber, firmwareVersion, hardwareVersion,
    hardwareType``. The v3.13.2 walk returned ``firmwareVersion,
    hardwareType, serialNumber`` (no ``hardwareVersion``). We expose all
    four; missing keys land as ``None``.
    """

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
