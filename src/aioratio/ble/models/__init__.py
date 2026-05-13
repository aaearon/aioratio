"""BLE request/response dataclasses.

Wire-format keys are taken verbatim from the decompiled Kotlin
``$$serializer.java`` descriptors AND validated against a v3.13.2 firmware
hardware walk (2026-05-13). The cloud and BLE wire formats differ even when
domain concepts overlap, so BLE models are kept separate from
``aioratio.models``.
"""

from __future__ import annotations

from .common import (
    IPC_RESULT_FAILED,
    IPC_RESULT_SUCCESS,
    SettableValue,
    b64_decode_text,
    b64_encode_text,
    is_success,
)
from .control import ChargeControl, ChargeControlResponse
from .network import EthernetInfo, Ipv4Info, NetworkStatusResponse, WifiInfo
from .ocpp import BackendStatusResponse, OcppCpms, OcppStatusResponse
from .product import ConnectivityController, MainController, ProductInformationResponse
from .sensors import ChargerSensorValuesResponse
from .settings import (
    SolarSettingsResponse,
    SolarSettingsUpdate,
    TimeSettingsResponse,
    TimeSettingsUpdate,
    UserSettingsResponse,
    UserSettingsUpdate,
)
from .status import ChargerStatusResponse, ChargeStatusIndicators
from .wifi import WifiAccessPoint, WifiConnectResponse, WifiScanResponse

__all__ = [
    "IPC_RESULT_SUCCESS",
    "IPC_RESULT_FAILED",
    "is_success",
    "SettableValue",
    "b64_decode_text",
    "b64_encode_text",
    "ChargeControl",
    "ChargeControlResponse",
    "ConnectivityController",
    "MainController",
    "ProductInformationResponse",
    "ChargerSensorValuesResponse",
    "SolarSettingsResponse",
    "SolarSettingsUpdate",
    "TimeSettingsResponse",
    "TimeSettingsUpdate",
    "UserSettingsResponse",
    "UserSettingsUpdate",
    "ChargerStatusResponse",
    "ChargeStatusIndicators",
    "WifiAccessPoint",
    "WifiConnectResponse",
    "WifiScanResponse",
    "NetworkStatusResponse",
    "WifiInfo",
    "EthernetInfo",
    "Ipv4Info",
    "OcppCpms",
    "OcppStatusResponse",
    "BackendStatusResponse",
]
