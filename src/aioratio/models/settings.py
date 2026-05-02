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
try:
    from typing import Any, Optional, Self
except ImportError:  # Python 3.10
    from typing import Any, Optional  # type: ignore[assignment]
    from typing_extensions import Self


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
            if type(raw_value) is int:
                if not self.value.is_integer():
                    raise ValueError(
                        "UpperLowerLimitSetting.value must be integral when the "
                        f"original raw value was an int; got {self.value!r}"
                    )
                out["value"] = int(self.value)
            else:
                out["value"] = self.value
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

        def _integer_payload_value(field_name: str, value: float) -> int:
            if not float(value).is_integer():
                raise ValueError(f"{field_name} must be an integer-valued number, got {value!r}")
            return int(value)

        out: dict[str, Any] = {}
        if self.pure_solar_starting_current is not None and self.pure_solar_starting_current.value is not None:
            out["pureSolarStartingCurrent"] = _integer_payload_value(
                "pureSolarStartingCurrent", self.pure_solar_starting_current.value
            )
        if self.smart_solar_starting_current is not None and self.smart_solar_starting_current.value is not None:
            out["smartSolarStartingCurrent"] = _integer_payload_value(
                "smartSolarStartingCurrent", self.smart_solar_starting_current.value
            )
        if self.sun_off_delay_minutes is not None and self.sun_off_delay_minutes.value is not None:
            out["sunOffDelayMinutes"] = _integer_payload_value(
                "sunOffDelayMinutes", self.sun_off_delay_minutes.value
            )
        if self.sun_on_delay_minutes is not None and self.sun_on_delay_minutes.value is not None:
            out["sunOnDelayMinutes"] = _integer_payload_value(
                "sunOnDelayMinutes", self.sun_on_delay_minutes.value
            )
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
            start = f"{data['beginTimeHour']:02d}:{data.get('beginTimeMinute', 0):02d}"
        if end is None and "endTimeHour" in data:
            end = f"{data['endTimeHour']:02d}:{data.get('endTimeMinute', 0):02d}"
        return cls(
            start=start,
            end=end,
            days=[_DAY_ABBR_TO_FULL.get(str(d).upper(), str(d).lower()) for d in days],
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
                day_key = str(day).upper()
                day_lower = _DAY_ABBR_TO_FULL.get(day_key, str(day).lower())
                if day_lower in week:
                    week[day_lower].append(dict(serialised))
        out["weekSchedule"] = week
        return out


@dataclass(slots=True)
class CpmsConfig:
    """A CPMS entry from either the current setting or the options list.

    GET ``cpms.value``: ``{centralSystem, url}`` (ConfiguredCpms).
    List endpoint: ``{name, url, cpidType}`` (ConfigurableCpms).
    Both shapes are accepted; ``central_system`` captures the label field.
    """

    central_system: Optional[str] = None
    url: Optional[str] = None
    cpid_type: Optional[str] = None  # cpidType from ConfigurableCpms options list

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CpmsConfig":
        return cls(
            central_system=data.get("centralSystem") or data.get("name"),
            url=data.get("url"),
            cpid_type=data.get("cpidType"),
        )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if self.central_system is not None:
            out["centralSystem"] = self.central_system
        if self.url is not None:
            out["url"] = self.url
        return out


@dataclass(slots=True)
class OcppFieldStatus:
    """Metadata from ``ValueDTOWithReason`` for a single OCPP field.

    Defaults to ``is_change_allowed=True`` so that entities created before the
    first coordinator refresh are not immediately shown as unavailable. The
    coordinator will overwrite with real data on the first successful fetch.
    """

    is_change_allowed: bool = True
    change_not_allowed_reason: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OcppFieldStatus":
        return cls(
            is_change_allowed=bool(data.get("isChangeAllowed", True)),
            change_not_allowed_reason=_unwrap_str(data.get("changeNotAllowedReason")),
        )


@dataclass(slots=True)
class InstallerOcppSettings:
    """Installer OCPP settings.

    GET shape: each field is a ``ValueDTOWithReason`` wrapper.
    PUT shape (``to_dict``): flat — only the three writable values, no metadata.

    Source: ``InstallerOcppSettings.java`` (cloud data source),
    ``SetInstallerOcppSettings.java``, ``ChargePointIdentifier.java``.
    """

    enabled: Optional[bool] = None
    cpms: Optional[CpmsConfig] = None
    charge_point_identifier: Optional[str] = None
    enabled_status: OcppFieldStatus = field(default_factory=OcppFieldStatus)
    cpms_status: OcppFieldStatus = field(default_factory=OcppFieldStatus)
    charge_point_identifier_status: OcppFieldStatus = field(default_factory=OcppFieldStatus)
    charge_point_identifier_max_length: Optional[int] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "InstallerOcppSettings":
        enabled_raw = data.get("enabled")
        cpms_raw = data.get("cpms")
        cpid_raw = data.get("chargePointIdentifier")

        enabled: Optional[bool] = None
        enabled_status = OcppFieldStatus()
        if isinstance(enabled_raw, dict):
            v = enabled_raw.get("value")
            enabled = bool(v) if v is not None else None
            enabled_status = OcppFieldStatus.from_dict(enabled_raw)
        elif enabled_raw is not None:
            enabled = bool(enabled_raw)

        cpms: Optional[CpmsConfig] = None
        cpms_status = OcppFieldStatus()
        if isinstance(cpms_raw, dict):
            if "isChangeAllowed" in cpms_raw:
                # GET shape: ValueDTOWithReason wrapper
                v = cpms_raw.get("value")
                cpms = CpmsConfig.from_dict(v) if isinstance(v, dict) else None
                cpms_status = OcppFieldStatus.from_dict(cpms_raw)
            else:
                # Flat CpmsConfig dict (e.g. round-tripped from to_dict)
                cpms = CpmsConfig.from_dict(cpms_raw)

        charge_point_identifier: Optional[str] = None
        cpid_status = OcppFieldStatus()
        cpid_max_length: Optional[int] = None
        if isinstance(cpid_raw, dict):
            charge_point_identifier = cpid_raw.get("value")
            cpid_status = OcppFieldStatus.from_dict(cpid_raw)
            ml = cpid_raw.get("maxLength")
            cpid_max_length = int(ml) if ml is not None else None
        elif isinstance(cpid_raw, str):
            charge_point_identifier = cpid_raw

        return cls(
            enabled=enabled,
            cpms=cpms,
            charge_point_identifier=charge_point_identifier,
            enabled_status=enabled_status,
            cpms_status=cpms_status,
            charge_point_identifier_status=cpid_status,
            charge_point_identifier_max_length=cpid_max_length,
        )

    def to_dict(self) -> dict[str, Any]:
        """Emit the flat PUT shape — only the three writable fields."""
        out: dict[str, Any] = {}
        if self.enabled is not None:
            out["enabled"] = self.enabled
        if self.cpms is not None:
            out["cpms"] = self.cpms.to_dict()
        if self.charge_point_identifier is not None:
            out["chargePointIdentifier"] = self.charge_point_identifier
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
