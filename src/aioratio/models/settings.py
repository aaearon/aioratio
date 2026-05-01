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

    The exact JSON shape varies per setting in the APK; ``raw`` preserves
    whatever the cloud returns so ``to_dict()`` can echo it back.
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
        out = dict(self.raw)
        if self.value is not None:
            raw_value = self.raw.get("value")
            out["value"] = int(self.value) if isinstance(raw_value, int) else self.value
        return out


@dataclass(slots=True)
class EnumValue:
    """Generic ``EnumDataClass<T>`` wrapper from the APK."""

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
        """Emit the PUT shape: flat nullable integers (not nested value objects).

        The GET response uses ``{"value": N, "isChangeAllowed": ..., ...}``
        wrappers, but the APK's ``SetSolarSettings`` DTO serialises each
        field as a bare ``Integer?``.
        """
        out: dict[str, Any] = {}
        if self.pure_solar_starting_current is not None and self.pure_solar_starting_current.value is not None:
            out["pureSolarStartingCurrent"] = int(self.pure_solar_starting_current.value)
        if self.smart_solar_starting_current is not None and self.smart_solar_starting_current.value is not None:
            out["smartSolarStartingCurrent"] = int(self.smart_solar_starting_current.value)
        if self.sun_off_delay_minutes is not None and self.sun_off_delay_minutes.value is not None:
            out["sunOffDelayMinutes"] = int(self.sun_off_delay_minutes.value)
        if self.sun_on_delay_minutes is not None and self.sun_on_delay_minutes.value is not None:
            out["sunOnDelayMinutes"] = int(self.sun_on_delay_minutes.value)
        return out


_DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
_DAY_ABBR_TO_FULL: dict[str, str] = {
    "MON": "monday", "TUE": "tuesday", "WED": "wednesday",
    "THU": "thursday", "FRI": "friday", "SAT": "saturday", "SUN": "sunday",
}


@dataclass(slots=True)
class DelayedStartSetting:
    """Delayed-start configuration.

    Source: ``DelayedStartSetting`` in ``charger_schedule``.
    Fields: ``beginTimeHour`` (int), ``beginTimeMinute`` (int),
    ``chargingMode`` (nullable enum string).

    The GET response wraps the whole object in ``{"value": {...}}``
    and each inner field in its own ``{"value": ...}`` wrapper.
    """

    begin_time_hour: int = 0
    begin_time_minute: int = 0
    charging_mode: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        v = data.get("value")
        inner = v if isinstance(v, dict) else data
        return cls(
            begin_time_hour=int(_unwrap_value(inner.get("beginTimeHour"), 0)),
            begin_time_minute=int(_unwrap_value(inner.get("beginTimeMinute"), 0)),
            charging_mode=_unwrap_str(inner.get("chargingMode")),
        )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "beginTimeHour": self.begin_time_hour,
            "beginTimeMinute": self.begin_time_minute,
        }
        if self.charging_mode is not None:
            out["chargingMode"] = self.charging_mode
        return out


@dataclass(slots=True)
class ScheduleSlot:
    """Single charging session inside a weekly schedule.

    Source: ``ScheduledChargingSession`` in ``charger_schedule``.
    The APK uses per-day lists of ``{beginTimeHour, beginTimeMinute,
    endTimeHour, endTimeMinute, chargingMode?}`` objects.

    ``start``/``end`` accept either ``"HH:MM"`` strings (convenience)
    or pre-split hour/minute ints. ``days`` lists the days this slot
    applies to (e.g. ``["monday", "tuesday"]``).
    """

    start: Optional[str] = None
    end: Optional[str] = None
    days: list[str] = field(default_factory=list)
    charging_mode: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        days = data.get("days") or []
        start = data.get("start") or data.get("startTime")
        end = data.get("end") or data.get("endTime")
        if start is None and "beginTimeHour" in data:
            start = f"{data['beginTimeHour']}:{data.get('beginTimeMinute', 0):02d}"
        if end is None and "endTimeHour" in data:
            end = f"{data['endTimeHour']}:{data.get('endTimeMinute', 0):02d}"
        return cls(
            start=start,
            end=end,
            days=[_DAY_ABBR_TO_FULL.get(str(d), str(d).lower()) for d in days],
            charging_mode=data.get("chargingMode"),
        )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if self.start is not None:
            h, m = (int(x) for x in self.start.split(":"))
            out["beginTimeHour"] = h
            out["beginTimeMinute"] = m
        if self.end is not None:
            h, m = (int(x) for x in self.end.split(":"))
            out["endTimeHour"] = h
            out["endTimeMinute"] = m
        if self.charging_mode is not None:
            out["chargingMode"] = self.charging_mode
        return out


@dataclass(slots=True)
class ChargeSchedule:
    """Charge schedule with a list of slots.

    Source: ``ChargeScheduleGetSettings.java`` /
    ``ChargeSchedulePutSettings.java``.

    The GET response wraps booleans/enums in ``{"value": ...}``
    objects and nests slots under per-day keys in ``weekSchedule``.
    The PUT DTO expects flat booleans, a ``ScheduleType`` enum
    string, and ``weekSchedule`` with per-day session lists.
    """

    enabled: bool = False
    schedule_type: Optional[str] = None
    randomized_time_offset_enabled: bool = False
    delayed_start: Optional[DelayedStartSetting] = None
    slots: list[ScheduleSlot] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        slots: list[ScheduleSlot] = []
        week = data.get("weekSchedule")
        if isinstance(week, dict):
            for day in _DAYS:
                day_slots = week.get(day) or []
                for s in day_slots:
                    if isinstance(s, dict):
                        slot = ScheduleSlot.from_dict(s)
                        if day not in slot.days:
                            slot.days.append(day)
                        slots.append(slot)
        else:
            slots_raw = data.get("slots") or data.get("weekScheduleSlots") or []
            slots = [ScheduleSlot.from_dict(s) for s in slots_raw if isinstance(s, dict)]

        ds_raw = data.get("delayedStart")
        delayed_start: Optional[DelayedStartSetting] = None
        if isinstance(ds_raw, dict):
            delayed_start = DelayedStartSetting.from_dict(ds_raw)

        return cls(
            enabled=_parse_bool(_unwrap_value(data.get("enabled"), False)),
            schedule_type=_unwrap_str(data.get("scheduleType")),
            randomized_time_offset_enabled=_parse_bool(
                _unwrap_value(data.get("randomizedTimeOffsetEnabled"), False)
            ),
            delayed_start=delayed_start,
            slots=slots,
        )

    def to_dict(self) -> dict[str, Any]:
        """Emit the PUT shape expected by ``ChargeSchedulePutSettings``."""
        out: dict[str, Any] = {"enabled": self.enabled}
        if self.schedule_type is not None:
            out["scheduleType"] = self.schedule_type
        out["randomizedTimeOffsetEnabled"] = self.randomized_time_offset_enabled
        if self.delayed_start is not None:
            out["delayedStart"] = self.delayed_start.to_dict()
        week: dict[str, list[dict[str, Any]]] = {day: [] for day in _DAYS}
        for slot in self.slots:
            serialised = slot.to_dict()
            for day in (slot.days or _DAYS):
                day_lower = _DAY_ABBR_TO_FULL.get(day, day.lower())
                if day_lower in week:
                    week[day_lower].append(serialised)
        out["weekSchedule"] = week
        return out


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
