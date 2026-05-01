"""Charger settings dataclass models.

Sources: ``charger_settings/data/data_source/cloud/UserSettings.java``,
``SolarSettings.java``, ``ChargeModeSettings.java`` and the schedule
DTOs under ``charger_schedule/data/data_source``.

These models are deliberately permissive — many of the underlying
Kotlin DTOs use ``ValueDTO<T>`` / ``EnumDataClass<T>`` wrappers whose
exact JSON shape was not exhaustively decoded. Consumers needing the
raw payload can use ``raw``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Self


@dataclass(slots=True)
class UpperLowerLimitSetting:
    """Numeric setting with optional bounds.

    # TODO: confirm against live payload — exact JSON shape varies per
    # setting in the APK (sometimes wrapped in ``{"value": ..., "lower":
    # ..., "upper": ...}``).
    """

    value: Optional[float] = None
    lower: Optional[float] = None
    upper: Optional[float] = None
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            value=_as_float(data.get("value")),
            lower=_as_float(data.get("lower") or data.get("lowerLimit")),
            upper=_as_float(data.get("upper") or data.get("upperLimit")),
            raw=dict(data),
        )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if self.value is not None:
            raw_value = self.raw.get("value")
            out["value"] = int(self.value) if isinstance(raw_value, int) else self.value
        return out


@dataclass(slots=True)
class EnumValue:
    """Generic ``EnumDataClass<T>`` wrapper from the APK.

    # TODO: confirm against live payload.
    """

    value: Optional[str] = None
    allowed_values: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        av = data.get("allowedValues") or []
        return cls(
            value=data.get("value"),
            allowed_values=[str(v) for v in av],
        )


@dataclass(slots=True)
class ChargeModeSettings:
    """Charging-mode setting with allowed values.

    Source: ``ChargeModeSettings.java``.
    """

    value: Optional[str] = None
    allowed_values: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        av = data.get("allowedValues") or []
        return cls(
            value=data.get("value"),
            allowed_values=[str(v) for v in av],
        )


@dataclass(slots=True)
class UserSettings:
    """User-configurable charger settings.

    Source: ``UserSettings.java``.
    """

    cable_settings: Optional[EnumValue] = None
    charging_mode: Optional[ChargeModeSettings] = None
    maximum_charging_current: Optional[UpperLowerLimitSetting] = None
    minimum_charging_current: Optional[UpperLowerLimitSetting] = None
    start_mode: Optional[EnumValue] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        def _enum(key: str) -> Optional[EnumValue]:
            v = data.get(key)
            return EnumValue.from_dict(v) if isinstance(v, dict) else None

        def _limit(key: str) -> Optional[UpperLowerLimitSetting]:
            v = data.get(key)
            return UpperLowerLimitSetting.from_dict(v) if isinstance(v, dict) else None

        cm = data.get("chargingMode")
        return cls(
            cable_settings=_enum("cableSettings"),
            charging_mode=ChargeModeSettings.from_dict(cm) if isinstance(cm, dict) else None,
            maximum_charging_current=_limit("maximumChargingCurrent"),
            minimum_charging_current=_limit("minimumChargingCurrent"),
            start_mode=_enum("startMode"),
        )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if self.cable_settings is not None and self.cable_settings.value is not None:
            out["cableSettings"] = {"value": self.cable_settings.value}
        if self.charging_mode is not None and self.charging_mode.value is not None:
            out["chargingMode"] = {"value": self.charging_mode.value}
        if self.maximum_charging_current is not None and self.maximum_charging_current.value is not None:
            out["maximumChargingCurrent"] = self.maximum_charging_current.to_dict()
        if self.minimum_charging_current is not None and self.minimum_charging_current.value is not None:
            out["minimumChargingCurrent"] = self.minimum_charging_current.to_dict()
        if self.start_mode is not None and self.start_mode.value is not None:
            out["startMode"] = {"value": self.start_mode.value}
        return out


@dataclass(slots=True)
class SolarSettings:
    """Solar / PV related settings.

    Source: ``SolarSettings.java``.
    """

    pure_solar_starting_current: Optional[UpperLowerLimitSetting] = None
    smart_solar_starting_current: Optional[UpperLowerLimitSetting] = None
    sun_off_delay_minutes: Optional[UpperLowerLimitSetting] = None
    sun_on_delay_minutes: Optional[UpperLowerLimitSetting] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        def _limit(key: str) -> Optional[UpperLowerLimitSetting]:
            v = data.get(key)
            return UpperLowerLimitSetting.from_dict(v) if isinstance(v, dict) else None

        return cls(
            pure_solar_starting_current=_limit("pureSolarStartingCurrent"),
            smart_solar_starting_current=_limit("smartSolarStartingCurrent"),
            sun_off_delay_minutes=_limit("sunOffDelayMinutes"),
            sun_on_delay_minutes=_limit("sunOnDelayMinutes"),
        )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if self.pure_solar_starting_current is not None and self.pure_solar_starting_current.value is not None:
            out["pureSolarStartingCurrent"] = self.pure_solar_starting_current.to_dict()
        if self.smart_solar_starting_current is not None and self.smart_solar_starting_current.value is not None:
            out["smartSolarStartingCurrent"] = self.smart_solar_starting_current.to_dict()
        if self.sun_off_delay_minutes is not None and self.sun_off_delay_minutes.value is not None:
            out["sunOffDelayMinutes"] = self.sun_off_delay_minutes.to_dict()
        if self.sun_on_delay_minutes is not None and self.sun_on_delay_minutes.value is not None:
            out["sunOnDelayMinutes"] = self.sun_on_delay_minutes.to_dict()
        return out


@dataclass(slots=True)
class ScheduleSlot:
    """Single time slot inside a weekly schedule.

    Source: derived from ``WeekScheduleData`` in ``charger_schedule``.

    # TODO: confirm against live payload — APK uses
    # ``WeekScheduleData`` whose nested shape was not fully extracted.
    """

    start: Optional[str] = None
    end: Optional[str] = None
    days: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        days = data.get("days") or []
        return cls(
            start=data.get("start") or data.get("startTime"),
            end=data.get("end") or data.get("endTime"),
            days=[str(d) for d in days],
        )


@dataclass(slots=True)
class ChargeSchedule:
    """Charge schedule with a list of slots.

    Source: ``ChargeScheduleGetSettings.java`` /
    ``ChargeSchedulePutSettings.java``.
    """

    enabled: bool = False
    schedule_type: Optional[str] = None
    randomized_time_offset_enabled: bool = False
    delayed_start: Optional[str] = None
    slots: list[ScheduleSlot] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        slots_raw = (
            data.get("slots")
            or data.get("weekSchedule")
            or data.get("weekScheduleSlots")
            or []
        )
        if isinstance(slots_raw, dict):
            # Some payloads nest slots under another key — flatten if needed.
            slots_raw = slots_raw.get("slots", [])
        return cls(
            enabled=_parse_bool(_unwrap_value(data.get("enabled"), False)),
            schedule_type=_unwrap_str(data.get("scheduleType")),
            randomized_time_offset_enabled=_parse_bool(
                _unwrap_value(data.get("randomizedTimeOffsetEnabled"), False)
            ),
            delayed_start=_unwrap_str(data.get("delayedStart")),
            slots=[ScheduleSlot.from_dict(s) for s in slots_raw if isinstance(s, dict)],
        )


def _parse_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lower = value.lower()
        if lower == "true":
            return True
        if lower == "false":
            return False
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    return default


def _as_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _unwrap_value(v: Any, default: Any = None) -> Any:
    """APK uses ``ValueDTO<T>`` wrappers — accept both the unwrapped
    primitive and the ``{"value": ...}`` shape.
    """
    if isinstance(v, dict) and "value" in v:
        return v["value"]
    return v if v is not None else default


def _unwrap_str(v: Any) -> Optional[str]:
    v = _unwrap_value(v)
    return None if v is None else str(v)
