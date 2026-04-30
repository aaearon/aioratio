"""Public dataclass models for the aioratio library."""
from __future__ import annotations

from .charger import (
    ChargeSessionStatus,
    Charger,
    ChargerFirmwareStatus,
    ChargerOverview,
    ChargerStatus,
    ChargerStatusError,
    FirmwareUpdateJob,
    Indicators,
    LastUpdatedTimestamp,
)
from .command import (
    CommandRequest,
    GrantUpgradePermissionParameters,
    StartCommandParameters,
)
from .history import Session, SessionHistoryPage, TimeData
from .settings import (
    ChargeModeSettings,
    ChargeSchedule,
    EnumValue,
    ScheduleSlot,
    SolarSettings,
    UpperLowerLimitSetting,
    UserSettings,
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
    # settings
    "UserSettings",
    "ChargeModeSettings",
    "SolarSettings",
    "ChargeSchedule",
    "ScheduleSlot",
    "UpperLowerLimitSetting",
    "EnumValue",
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
