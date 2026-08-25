"""Public dataclass models for the aioratio library."""

from __future__ import annotations

from .charger import (
    Charger,
    ChargerFirmwareStatus,
    ChargerOverview,
    ChargerStatus,
    ChargerStatusError,
    ChargeSessionStatus,
    FirmwareUpdateJob,
    Indicators,
    LastUpdatedTimestamp,
)
from .command import (
    CommandRequest,
    GrantUpgradePermissionParameters,
    StartCommandParameters,
)
from .diagnostics import (
    BackendStatus,
    ChargerDiagnostics,
    ConnectivityController,
    EthernetStatus,
    Ipv4,
    MainController,
    NetworkStatus,
    OcppDiagnosticStatus,
    ProductInformation,
    WifiStatus,
)
from .history import Session, SessionHistoryPage, TimeData
from .settings import (
    ChargeModeSettings,
    ChargeSchedule,
    ChargeScheduleUpdate,
    CpmsConfig,
    DelayedStartSetting,
    EnumValue,
    InstallerOcppSettings,
    OcppFieldStatus,
    OcppSettingsUpdate,
    ScheduleSlot,
    SolarSettings,
    SolarSettingsUpdate,
    UpperLowerLimitSetting,
    UserSettings,
    UserSettingsUpdate,
)
from .vehicle import Vehicle

__all__ = [
    # charger
    "Charger",
    "ChargerOverview",
    "ChargerStatus",
    "ChargerStatusError",
    "Indicators",
    "ChargeSessionStatus",
    "ChargerFirmwareStatus",
    "FirmwareUpdateJob",
    "LastUpdatedTimestamp",
    # diagnostics
    "ChargerDiagnostics",
    "ProductInformation",
    "ConnectivityController",
    "MainController",
    "NetworkStatus",
    "WifiStatus",
    "EthernetStatus",
    "Ipv4",
    "BackendStatus",
    "OcppDiagnosticStatus",
    # settings
    "UserSettings",
    "UserSettingsUpdate",
    "ChargeModeSettings",
    "SolarSettings",
    "SolarSettingsUpdate",
    "ChargeSchedule",
    "ChargeScheduleUpdate",
    "ScheduleSlot",
    "DelayedStartSetting",
    "UpperLowerLimitSetting",
    "EnumValue",
    "CpmsConfig",
    "OcppFieldStatus",
    "InstallerOcppSettings",
    "OcppSettingsUpdate",
    # command
    "CommandRequest",
    "StartCommandParameters",
    "GrantUpgradePermissionParameters",
    # history
    "Session",
    "SessionHistoryPage",
    "TimeData",
    # vehicle
    "Vehicle",
]
