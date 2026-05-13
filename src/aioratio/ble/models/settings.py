"""User / solar / time settings BLE payloads.

Sources (all under ``charger_settings/data/data_source/ble/``):
  - ``UserSettings.kt``: ``GetUserSettingsResponse`` and ``SetUserSettingsRequest``
  - ``SolarSettings.kt``: ``GetSolarSettingsResponse`` and ``SetSolarSettingsRequest``
  - ``TimeSettings.kt``: ``GetTimeSettingsResponse`` and ``SetTimeSettingsRequest``
    plus ``SerializedNames.java`` (``timeZoneAreaLocation``, ``timeZonePosix``).

The wire is **asymmetric**: Get responses wrap every field in a
``SettableValue`` envelope (``{value, isChangeAllowed, allowedValues|limits}``),
while Set requests carry flat values. The 2026-05-13 v3.13.2 hardware walk
confirms this and is the source of truth for the wrapper shape.

The Set*Update payloads use Kotlinx nullable defaults so a partial update
emits only the fields that are present. ``to_dict`` omits ``None`` for the
same reason.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Self

from .common import SettableValue

# --------------------------------------------------------------------------- user


@dataclass(slots=True)
class UserSettingsResponse:
    """Source: ``GetUserSettingsResponse$$serializer.java`` + 2026-05-13 wire capture."""

    transaction: str
    result: str
    start_mode: SettableValue | None = None
    cable_settings: SettableValue | None = None
    minimum_charging_current: SettableValue | None = None
    maximum_charging_current: SettableValue | None = None
    charging_mode: SettableValue | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            transaction=data["transaction"],
            result=data["result"],
            start_mode=_maybe(data.get("startMode")),
            cable_settings=_maybe(data.get("cableSettings")),
            minimum_charging_current=_maybe(data.get("minimumChargingCurrent")),
            maximum_charging_current=_maybe(data.get("maximumChargingCurrent")),
            charging_mode=_maybe(data.get("chargingMode")),
        )


@dataclass(slots=True)
class UserSettingsUpdate:
    """Payload for ``SetUserSettingsRequest`` — sends flat values."""

    start_mode: str | None = None
    cable_settings: str | None = None
    minimum_charging_current: int | None = None
    maximum_charging_current: int | None = None
    charging_mode: str | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if self.start_mode is not None:
            out["startMode"] = self.start_mode
        if self.cable_settings is not None:
            out["cableSettings"] = self.cable_settings
        if self.minimum_charging_current is not None:
            out["minimumChargingCurrent"] = self.minimum_charging_current
        if self.maximum_charging_current is not None:
            out["maximumChargingCurrent"] = self.maximum_charging_current
        if self.charging_mode is not None:
            out["chargingMode"] = self.charging_mode
        return out


# -------------------------------------------------------------------------- solar


@dataclass(slots=True)
class SolarSettingsResponse:
    """Source: ``GetSolarSettingsResponse$$serializer.java`` + 2026-05-13 wire capture."""

    transaction: str
    result: str
    smart_solar_starting_current: SettableValue | None = None
    pure_solar_starting_current: SettableValue | None = None
    sun_off_delay_minutes: SettableValue | None = None
    sun_on_delay_minutes: SettableValue | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            transaction=data["transaction"],
            result=data["result"],
            smart_solar_starting_current=_maybe(data.get("smartSolarStartingCurrent")),
            pure_solar_starting_current=_maybe(data.get("pureSolarStartingCurrent")),
            sun_off_delay_minutes=_maybe(data.get("sunOffDelayMinutes")),
            sun_on_delay_minutes=_maybe(data.get("sunOnDelayMinutes")),
        )


@dataclass(slots=True)
class SolarSettingsUpdate:
    """Payload for ``SetSolarSettingsRequest`` — sends flat values."""

    smart_solar_starting_current: int | None = None
    pure_solar_starting_current: int | None = None
    sun_off_delay_minutes: int | None = None
    sun_on_delay_minutes: int | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if self.smart_solar_starting_current is not None:
            out["smartSolarStartingCurrent"] = self.smart_solar_starting_current
        if self.pure_solar_starting_current is not None:
            out["pureSolarStartingCurrent"] = self.pure_solar_starting_current
        if self.sun_off_delay_minutes is not None:
            out["sunOffDelayMinutes"] = self.sun_off_delay_minutes
        if self.sun_on_delay_minutes is not None:
            out["sunOnDelayMinutes"] = self.sun_on_delay_minutes
        return out


# --------------------------------------------------------------------------- time


@dataclass(slots=True)
class TimeSettingsResponse:
    """Source: ``GetTimeSettingsResponse$$serializer.java`` + 2026-05-13 wire capture.

    Wire keys (resolved from ``SerializedNames.java``): ``timeZoneAreaLocation``,
    ``timeZonePosix``, ``transaction``, ``result``.
    """

    transaction: str
    result: str
    time_zone_area_location: SettableValue | None = None
    time_zone_posix: SettableValue | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            transaction=data["transaction"],
            result=data["result"],
            time_zone_area_location=_maybe(data.get("timeZoneAreaLocation")),
            time_zone_posix=_maybe(data.get("timeZonePosix")),
        )


@dataclass(slots=True)
class TimeSettingsUpdate:
    """Payload for ``SetTimeSettingsRequest`` — both fields required."""

    time_zone_area_location: str
    time_zone_posix: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "timeZoneAreaLocation": self.time_zone_area_location,
            "timeZonePosix": self.time_zone_posix,
        }


def _maybe(raw: Any) -> SettableValue | None:
    if isinstance(raw, dict):
        return SettableValue.from_dict(raw)
    return None


__all__ = [
    "UserSettingsResponse",
    "UserSettingsUpdate",
    "SolarSettingsResponse",
    "SolarSettingsUpdate",
    "TimeSettingsResponse",
    "TimeSettingsUpdate",
]
