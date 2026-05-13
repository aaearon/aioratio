"""User / solar / time settings BLE payloads.

Sources (all under ``charger_settings/data/data_source/ble/``):
  - ``UserSettings.kt``: ``GetUserSettingsResponse`` and ``SetUserSettingsRequest``
  - ``SolarSettings.kt``: ``GetSolarSettingsResponse`` and ``SetSolarSettingsRequest``
  - ``TimeSettings.kt``: ``GetTimeSettingsResponse`` and ``SetTimeSettingsRequest``
    plus ``SerializedNames.java`` (``timeZoneAreaLocation``, ``timeZonePosix``).

The Set*Request payloads use Kotlinx nullable defaults so a partial update
emits only the fields that are present. ``to_dict`` omits ``None`` for the
same reason.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Self

# --------------------------------------------------------------------------- user


@dataclass(slots=True)
class UserSettingsResponse:
    """Source: ``GetUserSettingsResponse$$serializer.java``."""

    transaction: str
    result: str
    start_mode: str | None = None
    cable_settings: str | None = None
    minimum_charging_current: int | None = None
    maximum_charging_current: int | None = None
    charging_mode: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            transaction=data["transaction"],
            result=data["result"],
            start_mode=data.get("startMode"),
            cable_settings=data.get("cableSettings"),
            minimum_charging_current=_opt_int(data.get("minimumChargingCurrent")),
            maximum_charging_current=_opt_int(data.get("maximumChargingCurrent")),
            charging_mode=data.get("chargingMode"),
        )


@dataclass(slots=True)
class UserSettingsUpdate:
    """Payload for ``SetUserSettingsRequest``.

    All fields except ``transaction`` are nullable; ``to_dict`` omits ``None``
    fields so callers can patch individual settings.
    """

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
    """Source: ``GetSolarSettingsResponse$$serializer.java``."""

    transaction: str
    result: str
    smart_solar_starting_current: int | None = None
    pure_solar_starting_current: int | None = None
    sun_off_delay_minutes: int | None = None
    sun_on_delay_minutes: int | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            transaction=data["transaction"],
            result=data["result"],
            smart_solar_starting_current=_opt_int(data.get("smartSolarStartingCurrent")),
            pure_solar_starting_current=_opt_int(data.get("pureSolarStartingCurrent")),
            sun_off_delay_minutes=_opt_int(data.get("sunOffDelayMinutes")),
            sun_on_delay_minutes=_opt_int(data.get("sunOnDelayMinutes")),
        )


@dataclass(slots=True)
class SolarSettingsUpdate:
    """Payload for ``SetSolarSettingsRequest``."""

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
    """Source: ``GetTimeSettingsResponse$$serializer.java``.

    Wire keys (resolved from ``SerializedNames.java``): ``timeZoneAreaLocation``,
    ``timeZonePosix``, ``transaction``, ``result``.
    """

    transaction: str
    result: str
    time_zone_area_location: str | None = None
    time_zone_posix: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            transaction=data["transaction"],
            result=data["result"],
            time_zone_area_location=data.get("timeZoneAreaLocation"),
            time_zone_posix=data.get("timeZonePosix"),
        )


@dataclass(slots=True)
class TimeSettingsUpdate:
    """Payload for ``SetTimeSettingsRequest``.

    Both fields are required in the request descriptor (``addElement(..., false)``)
    so ``to_dict`` always emits them.
    """

    time_zone_area_location: str
    time_zone_posix: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "timeZoneAreaLocation": self.time_zone_area_location,
            "timeZonePosix": self.time_zone_posix,
        }


def _opt_int(v: Any) -> int | None:
    return int(v) if v is not None else None


__all__ = [
    "UserSettingsResponse",
    "UserSettingsUpdate",
    "SolarSettingsResponse",
    "SolarSettingsUpdate",
    "TimeSettingsResponse",
    "TimeSettingsUpdate",
]
