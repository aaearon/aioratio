"""User / Solar / Time settings models.

The Set*Update.to_dict outputs must use only keys that appear in the APK
``$$serializer.java`` descriptor (or, for Set*Request without a descriptor,
the order recorded in ``_serializer_refs.py``).
"""

from __future__ import annotations

from aioratio.ble.models import (
    SolarSettingsResponse,
    SolarSettingsUpdate,
    TimeSettingsResponse,
    TimeSettingsUpdate,
    UserSettingsResponse,
    UserSettingsUpdate,
)

from ._serializer_refs import SERIALIZER_KEYS

# ------------------------------------------------------------------------ user


def test_user_settings_response_parses_full_payload() -> None:
    raw = {
        "transaction": "t",
        "result": "Success",
        "startMode": "Manual",
        "cableSettings": "Locked",
        "minimumChargingCurrent": 6,
        "maximumChargingCurrent": 32,
        "chargingMode": "Smart",
    }
    parsed = UserSettingsResponse.from_dict(raw)
    assert parsed.start_mode == "Manual"
    assert parsed.minimum_charging_current == 6
    assert parsed.charging_mode == "Smart"


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
    # Output must not have 'transaction' (the client adds that) but every
    # remaining output key must be in the serializer descriptor.
    assert keys.issubset(allowed - {"transaction"})


# ----------------------------------------------------------------------- solar


def test_solar_settings_response_parses() -> None:
    raw = {
        "transaction": "t",
        "result": "Success",
        "smartSolarStartingCurrent": 6,
        "pureSolarStartingCurrent": 10,
        "sunOffDelayMinutes": 5,
        "sunOnDelayMinutes": 1,
    }
    parsed = SolarSettingsResponse.from_dict(raw)
    assert parsed.smart_solar_starting_current == 6
    assert parsed.sun_off_delay_minutes == 5


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


def test_time_settings_response_parses() -> None:
    raw = {
        "timeZoneAreaLocation": "Europe/Amsterdam",
        "timeZonePosix": "CET-1CEST,M3.5.0,M10.5.0/3",
        "transaction": "t",
        "result": "Success",
    }
    parsed = TimeSettingsResponse.from_dict(raw)
    assert parsed.time_zone_area_location == "Europe/Amsterdam"
    assert parsed.time_zone_posix.startswith("CET")


def test_time_settings_update_emits_both_required_keys() -> None:
    out = TimeSettingsUpdate(
        time_zone_area_location="Europe/Amsterdam",
        time_zone_posix="CET-1CEST,M3.5.0,M10.5.0/3",
    ).to_dict()
    # Both keys are non-optional in the descriptor.
    assert set(out.keys()) == {"timeZoneAreaLocation", "timeZonePosix"}
