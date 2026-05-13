"""BLE request/response dataclasses.

Wire-format keys are taken verbatim from the decompiled Kotlin
``$$serializer.java`` descriptors. The cloud and BLE wire formats differ even
when domain concepts overlap, so BLE models are kept separate from
``aioratio.models``.
"""

from __future__ import annotations

from .common import IPC_RESULT_FAILED, IPC_RESULT_SUCCESS, is_success
from .control import ChargeControl, ChargeControlResponse
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
]
