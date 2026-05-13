"""``ChargerStatusResponse`` and the nested ``ChargeStatusIndicators``.

Sources:
  - ``charger/data/data_source/ble/ChargerStatusResponse$$serializer.java``
  - ``charger/data/data_source/ble/ChargeStatusIndicators$$serializer.java``

The plan's Phase 0 R6 flagged ``ChargeStatusIndicators`` as the shape we may
ship as opaque ``dict[str, Any]`` until hardware confirms it. The decompiled
serializer descriptor exposes a finite, well-typed field list so we ship the
typed dataclass below. The ``errors`` list element shape was not visible from
the descriptor alone; we keep it as ``list[dict[str, Any]]`` until hardware
returns a populated example.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Self


@dataclass(slots=True)
class ChargeStatusIndicators:
    """Source: ``ChargeStatusIndicators$$serializer.java``.

    Wire keys: ``chargingState, actualChargingPower, isVehicleConnected,
    isChargeSessionActive, isPowerReducedByDSO, isChargingPaused,
    isChargingAuthorized, isChargingDisabled, isChargingDisabledReason, errors``.
    """

    charging_state: str | None = None
    actual_charging_power: int | None = None
    is_vehicle_connected: bool = False
    is_charge_session_active: bool = False
    is_power_reduced_by_dso: bool = False
    is_charging_paused: bool = False
    is_charging_authorized: bool | None = None
    is_charging_disabled: bool = False
    is_charging_disabled_reason: str | None = None
    errors: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        errors_raw = data.get("errors") or []
        return cls(
            charging_state=data.get("chargingState"),
            actual_charging_power=(
                int(data["actualChargingPower"])
                if data.get("actualChargingPower") is not None
                else None
            ),
            is_vehicle_connected=bool(data.get("isVehicleConnected", False)),
            is_charge_session_active=bool(data.get("isChargeSessionActive", False)),
            is_power_reduced_by_dso=bool(data.get("isPowerReducedByDSO", False)),
            is_charging_paused=bool(data.get("isChargingPaused", False)),
            is_charging_authorized=data.get("isChargingAuthorized"),
            is_charging_disabled=bool(data.get("isChargingDisabled", False)),
            is_charging_disabled_reason=data.get("isChargingDisabledReason"),
            errors=list(errors_raw),
        )


@dataclass(slots=True)
class ChargerStatusResponse:
    """Source: ``ChargerStatusResponse$$serializer.java``.

    Wire keys (in descriptor order): ``transaction, result, cloudConnectionState,
    isChargeStartAllowed, isChargeStopAllowed, indicators``.
    """

    transaction: str
    result: str
    cloud_connection_state: str | None = None
    is_charge_start_allowed: bool = False
    is_charge_stop_allowed: bool = False
    indicators: ChargeStatusIndicators | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        ind = data.get("indicators")
        return cls(
            transaction=data["transaction"],
            result=data["result"],
            cloud_connection_state=data.get("cloudConnectionState"),
            is_charge_start_allowed=bool(data.get("isChargeStartAllowed", False)),
            is_charge_stop_allowed=bool(data.get("isChargeStopAllowed", False)),
            indicators=ChargeStatusIndicators.from_dict(ind) if isinstance(ind, dict) else None,
        )


__all__ = ["ChargeStatusIndicators", "ChargerStatusResponse"]
