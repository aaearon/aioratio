"""User / Solar / Time settings models — wrapper shape from real wire data.

Get responses wrap every field in a ``SettableValue`` envelope; Set updates
send flat values. The 2026-05-13 v3.13.2 hardware walk is the source of
truth for the wrapper shape.
"""

from __future__ import annotations

from aioratio.ble.models import (
    SettableValue,
    SolarSettingsResponse,
    SolarSettingsUpdate,
    TimeSettingsResponse,
    TimeSettingsUpdate,
    UserSettingsResponse,
    UserSettingsUpdate,
)

from ._serializer_refs import SERIALIZER_KEYS

# ------------------------------------------------------------------------ user


def test_user_settings_response_parses_wrapped_payload() -> None:
    raw = {
        "transaction": "t",
        "result": "success",
        "startMode": {
            "value": "Auto",
            "isChangeAllowed": True,
            "allowedValues": ["Manual", "Auto"],
        },
        "cableSettings": {
            "value": "LockWhenCarConnected",
            "isChangeAllowed": True,
            "allowedValues": [
                "LockWhenCarConnected",
                "LockAutomatically",
                "LockAlways",
            ],
        },
        "minimumChargingCurrent": {
            "value": 6,
            "isChangeAllowed": True,
            "lowerLimit": 6,
            "upperLimit": 16,
        },
        "maximumChargingCurrent": {
            "value": 16,
            "isChangeAllowed": True,
            "lowerLimit": 6,
            "upperLimit": 16,
        },
        "chargingMode": {
            "value": "PureSolar",
            "isChangeAllowed": True,
            "allowedValues": ["Smart", "SmartSolar", "PureSolar"],
        },
    }
    parsed = UserSettingsResponse.from_dict(raw)

    assert isinstance(parsed.start_mode, SettableValue)
    assert parsed.start_mode.value == "Auto"
    assert parsed.start_mode.allowed_values == ["Manual", "Auto"]
    assert parsed.cable_settings is not None
    assert parsed.cable_settings.allowed_values == [
        "LockWhenCarConnected",
        "LockAutomatically",
        "LockAlways",
    ]
    assert parsed.minimum_charging_current is not None
    assert parsed.minimum_charging_current.value == 6
    assert parsed.minimum_charging_current.lower_limit == 6
    assert parsed.minimum_charging_current.upper_limit == 16
    assert parsed.charging_mode is not None
    assert parsed.charging_mode.value == "PureSolar"


def test_user_settings_update_omits_none_fields() -> None:
    upd = UserSettingsUpdate(maximum_charging_current=16)
    assert upd.to_dict() == {"maximumChargingCurrent": 16}


def test_user_settings_update_uses_only_serializer_keys() -> None:
    allowed = set(SERIALIZER_KEYS["SetUserSettingsRequest"])
    upd = UserSettingsUpdate(
        start_mode="Manual",
        cable_settings="Locked",
        minimum_charging_current=6,
        maximum_charging_current=32,
        charging_mode="Smart",
    )
    keys = set(upd.to_dict().keys())
    assert keys.issubset(allowed - {"transaction"})


# ----------------------------------------------------------------------- solar


def test_solar_settings_response_parses_wrapped_payload() -> None:
    raw = {
        "transaction": "t",
        "result": "success",
        "smartSolarStartingCurrent": {
            "value": 16,
            "isChangeAllowed": True,
            "lowerLimit": 6,
            "upperLimit": 16,
        },
        "pureSolarStartingCurrent": {
            "value": 6,
            "isChangeAllowed": True,
            "lowerLimit": 6,
            "upperLimit": 16,
        },
        "sunOffDelayMinutes": {
            "value": 2,
            "isChangeAllowed": True,
            "lowerLimit": 1,
            "upperLimit": 60,
        },
        "sunOnDelayMinutes": {
            "value": 2,
            "isChangeAllowed": True,
            "lowerLimit": 1,
            "upperLimit": 60,
        },
    }
    parsed = SolarSettingsResponse.from_dict(raw)
    assert parsed.smart_solar_starting_current is not None
    assert parsed.smart_solar_starting_current.value == 16
    assert parsed.sun_off_delay_minutes is not None
    assert parsed.sun_off_delay_minutes.upper_limit == 60


def test_solar_settings_update_uses_only_serializer_keys() -> None:
    allowed = set(SERIALIZER_KEYS["SetSolarSettingsRequest"]) - {"transaction"}
    out = SolarSettingsUpdate(
        smart_solar_starting_current=6,
        pure_solar_starting_current=10,
        sun_off_delay_minutes=5,
        sun_on_delay_minutes=1,
    ).to_dict()
    assert set(out.keys()).issubset(allowed)


# ------------------------------------------------------------------------ time


def test_time_settings_response_parses_wrapped_payload() -> None:
    raw = {
        "timeZoneAreaLocation": {"value": "Europe/Amsterdam", "isChangeAllowed": True},
        "timeZonePosix": {"value": "CET-1CEST,M3.5.0,M10.5.0/3", "isChangeAllowed": True},
        "transaction": "t",
        "result": "success",
    }
    parsed = TimeSettingsResponse.from_dict(raw)
    assert parsed.time_zone_area_location is not None
    assert parsed.time_zone_area_location.value == "Europe/Amsterdam"
    assert parsed.time_zone_posix is not None
    assert parsed.time_zone_posix.value is not None
    assert parsed.time_zone_posix.value.startswith("CET")


def test_time_settings_update_emits_both_required_keys() -> None:
    out = TimeSettingsUpdate(
        time_zone_area_location="Europe/Amsterdam",
        time_zone_posix="CET-1CEST,M3.5.0,M10.5.0/3",
    ).to_dict()
    assert set(out.keys()) == {"timeZoneAreaLocation", "timeZonePosix"}
