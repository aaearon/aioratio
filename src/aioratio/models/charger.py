"""Charger-related dataclass models derived from APK DTOs.

Field names mirror the JSON keys produced by the cloud API (Kotlinx
Serialization uses Kotlin property names by default — no remapping
annotations were observed in the decompiled DTOs).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Self


@dataclass(slots=True)
class Charger:
    """Basic charger registration record.

    Source: ``charger/data/data_source/cloud/Charger.java`` —
    only ``serialNumber`` was present in 3.9.1.
    """

    serial_number: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(serial_number=data["serialNumber"])

    def to_dict(self) -> dict[str, Any]:
        return {"serialNumber": self.serial_number}


@dataclass(slots=True)
class ChargerStatusError:
    """A single error indicator entry inside ``ChargerStatus.indicators``.

    Source: ``ChargerStatusErrorDTO.java``.
    """

    error_code: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(error_code=int(data["errorCode"]))


@dataclass(slots=True)
class Indicators:
    """Detailed live indicators for a charger.

    Source: ``IndicatorsDTO.java``.
    """

    charging_state: Optional[str] = None
    errors: list[ChargerStatusError] = field(default_factory=list)
    is_charge_session_active: bool = False
    is_charging_authorized: Optional[bool] = None
    is_charging_disabled: bool = False
    is_charging_disabled_reason: Optional[str] = None
    is_charging_paused: bool = False
    is_power_reduced_by_dso: bool = False
    is_vehicle_connected: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        errors_raw = data.get("errors") or []
        return cls(
            charging_state=data.get("chargingState"),
            errors=[ChargerStatusError.from_dict(e) for e in errors_raw],
            is_charge_session_active=bool(data.get("isChargeSessionActive", False)),
            is_charging_authorized=data.get("isChargingAuthorized"),
            is_charging_disabled=bool(data.get("isChargingDisabled", False)),
            is_charging_disabled_reason=data.get("isChargingDisabledReason"),
            is_charging_paused=bool(data.get("isChargingPaused", False)),
            is_power_reduced_by_dso=bool(data.get("isPowerReducedByDSO", False)),
            is_vehicle_connected=bool(data.get("isVehicleConnected", False)),
        )


@dataclass(slots=True)
class ChargerStatus:
    """Connection/availability/error subset.

    Source: ``ChargerStatusDTO.java``.
    """

    is_charge_start_allowed: bool
    is_charge_stop_allowed: bool
    indicators: Optional[Indicators] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        ind = data.get("indicators")
        return cls(
            is_charge_start_allowed=bool(data.get("isChargeStartAllowed", False)),
            is_charge_stop_allowed=bool(data.get("isChargeStopAllowed", False)),
            indicators=Indicators.from_dict(ind) if isinstance(ind, dict) else None,
        )


@dataclass(slots=True)
class ChargeSessionStatus:
    """Live charge-session snapshot embedded in the charger overview.

    Source: ``ChargeSessionStatusDTO.java``.
    """

    actual_charging_power: int
    vehicle_id: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            actual_charging_power=int(data.get("actualChargingPower", 0)),
            vehicle_id=data.get("vehicleId"),
        )


@dataclass(slots=True)
class FirmwareUpdateJob:
    """Firmware update job entry.

    Source: ``FirmwareUpdateJobDTO.java`` — full schema not enumerated;
    fields stored as-is.
    """

    # TODO: confirm against live payload — schema not fully decoded from APK.
    job_id: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            job_id=data.get("jobId") or data.get("id"),
            type=data.get("type"),
            status=data.get("status"),
            raw=dict(data),
        )


@dataclass(slots=True)
class ChargerFirmwareStatus:
    """Firmware status block inside the charger overview.

    Source: ``ChargerFirmwareStatusDTO.java``.
    """

    is_firmware_update_available: bool = False
    is_firmware_update_allowed: bool = False
    firmware_update_jobs: list[FirmwareUpdateJob] = field(default_factory=list)
    firmware_update_status: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        jobs_raw = data.get("firmwareUpdateJobs") or []
        return cls(
            is_firmware_update_available=bool(data.get("isFirmwareUpdateAvailable", False)),
            is_firmware_update_allowed=bool(data.get("isFirmwareUpdateAllowed", False)),
            firmware_update_jobs=[FirmwareUpdateJob.from_dict(j) for j in jobs_raw],
            firmware_update_status=data.get("firmwareUpdateStatus"),
        )


@dataclass(slots=True)
class LastUpdatedTimestamp:
    """Per-setting last-updated marker.

    Source: ``LastUpdatedTimeStampsDTO.java``.
    """

    last_updated: int
    setting: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            last_updated=int(data.get("lastUpdated", 0)),
            setting=data.get("setting"),
        )


@dataclass(slots=True)
class ChargerOverview:
    """Rich charger state object — the per-charger overview returned by
    ``/chargers/status?id=overview``.

    Source: ``ChargerModelDTO.java``.
    """

    serial_number: str
    cloud_connection_state: Optional[str] = None
    charger_status: Optional[ChargerStatus] = None
    charge_session_status: Optional[ChargeSessionStatus] = None
    charger_firmware_status: Optional[ChargerFirmwareStatus] = None
    last_updated_timestamps: list[LastUpdatedTimestamp] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        cs = data.get("chargerStatus")
        css = data.get("chargeSessionStatus")
        cfs = data.get("chargerFirmwareStatus")
        ts_raw = data.get("lastUpdatedTimestamps") or []
        return cls(
            serial_number=data["serialNumber"],
            cloud_connection_state=data.get("cloudConnectionState"),
            charger_status=ChargerStatus.from_dict(cs) if isinstance(cs, dict) else None,
            charge_session_status=ChargeSessionStatus.from_dict(css) if isinstance(css, dict) else None,
            charger_firmware_status=ChargerFirmwareStatus.from_dict(cfs) if isinstance(cfs, dict) else None,
            last_updated_timestamps=[LastUpdatedTimestamp.from_dict(t) for t in ts_raw],
        )
