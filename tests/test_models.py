"""Tests for ``aioratio.models`` dataclasses.

The JSON snippets here are synthetic but plausible — they mirror the
shapes inferred from the decompiled APK DTOs.
"""
from __future__ import annotations

import pytest

from aioratio.exceptions import RatioApiError
from aioratio.models import (
    ChargeSchedule,
    ChargeSessionStatus,
    Charger,
    ChargerFirmwareStatus,
    ChargerOverview,
    ChargerStatus,
    ChargerStatusError,
    CommandRequest,
    Indicators,
    ScheduleSlot,
    Session,
    SessionHistoryPage,
    SolarSettings,
    StartCommandParameters,
    UpperLowerLimitSetting,
    UserSettings,
    Vehicle,
)


# ----- Charger ---------------------------------------------------------------


def test_charger_from_dict_full():
    c = Charger.from_dict({"serialNumber": "RT-12345"})
    assert c.serial_number == "RT-12345"
    assert c.to_dict() == {"serialNumber": "RT-12345"}


def test_charger_from_dict_unknown_fields_ignored():
    c = Charger.from_dict({"serialNumber": "RT-1", "unknown_key": 42})
    assert c.serial_number == "RT-1"


# ----- ChargerStatus / Indicators -------------------------------------------


def test_charger_status_nested_construction():
    payload = {
        "isChargeStartAllowed": True,
        "isChargeStopAllowed": False,
        "indicators": {
            "chargingState": "CHARGING",
            "errors": [{"errorCode": 7}, {"errorCode": 12}],
            "isChargeSessionActive": True,
            "isChargingAuthorized": True,
            "isChargingDisabled": False,
            "isChargingDisabledReason": None,
            "isChargingPaused": False,
            "isPowerReducedByDSO": True,
            "isVehicleConnected": True,
        },
    }
    status = ChargerStatus.from_dict(payload)
    assert status.is_charge_start_allowed is True
    assert status.is_charge_stop_allowed is False
    assert isinstance(status.indicators, Indicators)
    assert status.indicators.charging_state == "CHARGING"
    assert len(status.indicators.errors) == 2
    assert all(isinstance(e, ChargerStatusError) for e in status.indicators.errors)
    assert status.indicators.errors[0].error_code == 7
    assert status.indicators.is_power_reduced_by_dso is True


def test_charger_status_missing_optional():
    status = ChargerStatus.from_dict(
        {"isChargeStartAllowed": False, "isChargeStopAllowed": False}
    )
    assert status.indicators is None


# ----- ChargerOverview ------------------------------------------------------


def test_charger_overview_full_nested():
    payload = {
        "serialNumber": "RT-OVR-1",
        "cloudConnectionState": "CONNECTED",
        "chargerStatus": {
            "isChargeStartAllowed": True,
            "isChargeStopAllowed": True,
            "indicators": {"chargingState": "IDLE", "errors": []},
        },
        "chargeSessionStatus": {"vehicleId": "veh-1", "actualChargingPower": 7400},
        "chargerFirmwareStatus": {
            "isFirmwareUpdateAvailable": False,
            "isFirmwareUpdateAllowed": True,
            "firmwareUpdateJobs": [
                {"jobId": "j1", "type": "MAIN", "status": "PENDING"}
            ],
            "firmwareUpdateStatus": "IDLE",
        },
        "lastUpdatedTimestamps": [
            {"setting": "USER_SETTINGS", "lastUpdated": 1730000000},
        ],
        "extra": "ignored",
    }
    o = ChargerOverview.from_dict(payload)
    assert o.serial_number == "RT-OVR-1"
    assert o.cloud_connection_state == "CONNECTED"
    assert isinstance(o.charger_status, ChargerStatus)
    assert isinstance(o.charge_session_status, ChargeSessionStatus)
    assert o.charge_session_status.actual_charging_power == 7400
    assert o.charge_session_status.vehicle_id == "veh-1"
    assert isinstance(o.charger_firmware_status, ChargerFirmwareStatus)
    assert len(o.charger_firmware_status.firmware_update_jobs) == 1
    assert o.charger_firmware_status.firmware_update_jobs[0].job_id == "j1"
    assert len(o.last_updated_timestamps) == 1
    assert o.last_updated_timestamps[0].last_updated == 1730000000


def test_charger_overview_minimal():
    o = ChargerOverview.from_dict({"serialNumber": "RT-2"})
    assert o.serial_number == "RT-2"
    assert o.charger_status is None
    assert o.charge_session_status is None
    assert o.charger_firmware_status is None
    assert o.last_updated_timestamps == []


def test_charge_session_status_optional_vehicle():
    css = ChargeSessionStatus.from_dict({"actualChargingPower": 0})
    assert css.vehicle_id is None
    assert css.actual_charging_power == 0


# ----- Settings -------------------------------------------------------------


def test_user_settings_nested():
    payload = {
        "cableSettings": {"value": "LOCKED", "allowedValues": ["LOCKED", "UNLOCKED"]},
        "chargingMode": {"value": "SOLAR", "allowedValues": ["SOLAR", "FAST"]},
        "maximumChargingCurrent": {"value": 16, "lower": 6, "upper": 32},
        "minimumChargingCurrent": {"value": 6},
        "startMode": {"value": "AUTO", "allowedValues": ["AUTO", "MANUAL"]},
        "extra_field": True,
    }
    s = UserSettings.from_dict(payload)
    assert s.cable_settings is not None
    assert s.cable_settings.value == "LOCKED"
    assert s.charging_mode is not None
    assert s.charging_mode.value == "SOLAR"
    assert "FAST" in s.charging_mode.allowed_values
    assert s.maximum_charging_current is not None
    assert s.maximum_charging_current.value == 16.0
    assert s.maximum_charging_current.lower == 6.0
    assert s.maximum_charging_current.upper == 32.0
    assert s.start_mode is not None
    assert s.start_mode.value == "AUTO"


def test_user_settings_missing_optional():
    s = UserSettings.from_dict({})
    assert s.cable_settings is None
    assert s.charging_mode is None
    assert s.maximum_charging_current is None


def test_solar_settings_full():
    payload = {
        "pureSolarStartingCurrent": {"value": 6},
        "smartSolarStartingCurrent": {"value": 8},
        "sunOffDelayMinutes": {"value": 5},
        "sunOnDelayMinutes": {"value": 5},
    }
    s = SolarSettings.from_dict(payload)
    assert s.pure_solar_starting_current is not None
    assert s.pure_solar_starting_current.value == 6.0
    assert s.smart_solar_starting_current is not None
    assert s.smart_solar_starting_current.value == 8.0


def test_charge_schedule_with_slots():
    payload = {
        "enabled": {"value": True},
        "scheduleType": {"value": "WEEKLY"},
        "randomizedTimeOffsetEnabled": {"value": False},
        "slots": [
            {"start": "22:00", "end": "06:00", "days": ["MON", "TUE"]},
            {"start": "23:00", "end": "07:00", "days": ["SAT"]},
        ],
        "unknown": "ignored",
    }
    sch = ChargeSchedule.from_dict(payload)
    assert sch.enabled is True
    assert sch.schedule_type == "WEEKLY"
    assert sch.randomized_time_offset_enabled is False
    assert len(sch.slots) == 2
    assert all(isinstance(s, ScheduleSlot) for s in sch.slots)
    assert sch.slots[0].days == ["MON", "TUE"]
    assert sch.slots[1].start == "23:00"


# ----- Command --------------------------------------------------------------


def test_command_request_round_trip_start():
    cr = CommandRequest(
        transaction_id="tx-1",
        command=CommandRequest.START_CHARGE,
        start_command_parameters=StartCommandParameters(vehicle_id="veh-9"),
    )
    d = cr.to_dict()
    assert d == {
        "transactionId": "tx-1",
        "command": "start-charge",
        "startCommandParameters": {"vehicleId": "veh-9"},
    }
    parsed = CommandRequest.from_dict(d)
    assert parsed.transaction_id == "tx-1"
    assert parsed.command == "start-charge"
    assert parsed.start_command_parameters is not None
    assert parsed.start_command_parameters.vehicle_id == "veh-9"


def test_command_request_stop_charge_no_params():
    cr = CommandRequest.from_dict(
        {"transactionId": "tx-2", "command": "stop-charge", "extra": 1}
    )
    assert cr.command == CommandRequest.STOP_CHARGE
    assert cr.start_command_parameters is None
    assert cr.grant_upgrade_permission_parameters is None


# ----- Vehicle --------------------------------------------------------------


def test_vehicle_from_dict_full():
    v = Vehicle.from_dict(
        {
            "vehicleId": "v1",
            "vehicleName": "Polestar",
            "licensePlate": "AB-12-CD",
            "vehicleState": "ACTIVE",
        }
    )
    assert v.vehicle_id == "v1"
    assert v.vehicle_name == "Polestar"
    assert v.license_plate == "AB-12-CD"
    assert v.vehicle_state == "ACTIVE"


def test_vehicle_all_optional():
    v = Vehicle.from_dict({})
    assert v.vehicle_id is None
    assert v.vehicle_name is None
    assert v.license_plate is None
    assert v.vehicle_state is None


# ----- History --------------------------------------------------------------


def test_session_full_nested():
    payload = {
        "sessionId": "s-1",
        "chargerSerialNumber": "RT-1",
        "totalChargingEnergy": 12345,
        "begin": {"time": 1730000000, "type": "PLUG_IN", "userUuid": "u-1"},
        "end": {"time": 1730003600, "type": "UNPLUG", "userUuid": "u-1"},
        "userId": "u-1",
        "vehicle": {"vehicleId": "v1", "vehicleName": "Tesla"},
    }
    s = Session.from_dict(payload)
    assert s.session_id == "s-1"
    assert s.charger_serial_number == "RT-1"
    assert s.total_charging_energy == 12345
    assert s.begin is not None and s.begin.time == 1730000000
    assert s.end is not None and s.end.type == "UNPLUG"
    assert s.vehicle is not None and s.vehicle.vehicle_name == "Tesla"


def test_session_history_page():
    payload = {
        "chargeSessions": [
            {
                "sessionId": "s-a",
                "chargerSerialNumber": "RT-1",
                "totalChargingEnergy": 1000,
            },
            {
                "sessionId": "s-b",
                "chargerSerialNumber": "RT-1",
                "totalChargingEnergy": 2000,
                "vehicle": {"vehicleId": "v2"},
            },
        ],
        "nextToken": "tok-2",
    }
    page = SessionHistoryPage.from_dict(payload)
    assert page.next_token == "tok-2"
    assert len(page.sessions) == 2
    assert page.sessions[0].session_id == "s-a"
    assert page.sessions[1].vehicle is not None
    assert page.sessions[1].vehicle.vehicle_id == "v2"


def test_session_history_page_empty():
    page = SessionHistoryPage.from_dict({})
    assert page.sessions == []
    assert page.next_token is None


# ----- Sanity --------------------------------------------------------------


def test_unknown_keys_tolerated_across_models():
    # spot-check that adding noise doesn't blow up any model
    Charger.from_dict({"serialNumber": "x", "noise": [1, 2, 3]})
    ChargerStatus.from_dict(
        {"isChargeStartAllowed": True, "isChargeStopAllowed": True, "junk": "j"}
    )
    UserSettings.from_dict({"junk": {}})
    SolarSettings.from_dict({"junk": 1})
    Vehicle.from_dict({"junk": 1})


@pytest.mark.parametrize(
    "cmd",
    [CommandRequest.START_CHARGE, CommandRequest.STOP_CHARGE, CommandRequest.GRANT_UPGRADE_PERMISSION],
)
def test_command_constants(cmd: str):
    assert isinstance(cmd, str) and "-" in cmd


# ----- Missing required fields raise RatioApiError --------------------------


def test_session_missing_required_raises():
    with pytest.raises(RatioApiError, match="sessionId"):
        Session.from_dict({})


def test_charger_missing_required_raises():
    with pytest.raises(RatioApiError, match="serialNumber"):
        Charger.from_dict({})


def test_command_request_missing_required_raises():
    with pytest.raises(RatioApiError, match="transactionId"):
        CommandRequest.from_dict({})


def test_charger_overview_missing_required_raises():
    with pytest.raises(RatioApiError, match="serialNumber"):
        ChargerOverview.from_dict({})


# ----- _parse_bool via ChargeSchedule ---------------------------------------


def test_charge_schedule_parse_bool_string_false():
    sch = ChargeSchedule.from_dict({"enabled": "false"})
    assert sch.enabled is False


def test_charge_schedule_parse_bool_string_true():
    sch = ChargeSchedule.from_dict({"enabled": "true"})
    assert sch.enabled is True


def test_charge_schedule_parse_bool_wrapped_string_false():
    sch = ChargeSchedule.from_dict({"enabled": {"value": "false"}})
    assert sch.enabled is False


# ----- Round-trip serialisation (to_dict preserves full shape) ---------------


def test_upper_lower_limit_roundtrip():
    payload = {
        "value": 16,
        "lowerLimit": 6,
        "upperLimit": 32,
        "isChangeAllowed": True,
    }
    setting = UpperLowerLimitSetting.from_dict(payload)
    result = setting.to_dict()
    assert result["value"] == 16
    assert result["lowerLimit"] == 6
    assert result["upperLimit"] == 32
    assert result["isChangeAllowed"] is True


def test_upper_lower_limit_roundtrip_preserves_int_type():
    payload = {"value": 8, "lowerLimit": 1, "upperLimit": 20}
    setting = UpperLowerLimitSetting.from_dict(payload)
    setting.value = 12.0
    result = setting.to_dict()
    assert result["value"] == 12
    assert isinstance(result["value"], int)


def test_upper_lower_limit_roundtrip_no_value():
    payload = {"lowerLimit": 0, "upperLimit": 100}
    setting = UpperLowerLimitSetting.from_dict(payload)
    result = setting.to_dict()
    assert "value" not in result
    assert result["lowerLimit"] == 0
    assert result["upperLimit"] == 100


def test_solar_settings_roundtrip():
    """SolarSettings.to_dict() emits flat integers (PUT shape), not nested value objects."""
    payload = {
        "pureSolarStartingCurrent": {
            "value": 6,
            "lowerLimit": 1,
            "upperLimit": 16,
            "isChangeAllowed": True,
        },
        "smartSolarStartingCurrent": {"value": 8},
        "sunOffDelayMinutes": {"value": 5, "lowerLimit": 1, "upperLimit": 30},
        "sunOnDelayMinutes": {"value": 5},
    }
    settings = SolarSettings.from_dict(payload)
    result = settings.to_dict()
    assert result == {
        "pureSolarStartingCurrent": 6,
        "smartSolarStartingCurrent": 8,
        "sunOffDelayMinutes": 5,
        "sunOnDelayMinutes": 5,
    }


def test_user_settings_roundtrip():
    payload = {
        "maximumChargingCurrent": {
            "value": 16,
            "lowerLimit": 6,
            "upperLimit": 32,
            "isChangeAllowed": True,
        },
        "minimumChargingCurrent": {"value": 6},
    }
    settings = UserSettings.from_dict(payload)
    result = settings.to_dict()
    assert result["maximumChargingCurrent"]["isChangeAllowed"] is True
    assert result["maximumChargingCurrent"]["value"] == 16


def test_schedule_slot_to_dict():
    payload = {"start": "22:00", "end": "06:00", "days": ["MON", "TUE"]}
    slot = ScheduleSlot.from_dict(payload)
    result = slot.to_dict()
    assert result == {"start": "22:00", "end": "06:00", "days": ["MON", "TUE"]}


def test_schedule_slot_to_dict_alternative_keys():
    payload = {"startTime": "23:00", "endTime": "07:00", "days": ["SAT"]}
    slot = ScheduleSlot.from_dict(payload)
    result = slot.to_dict()
    assert result == {"start": "23:00", "end": "07:00", "days": ["SAT"]}


def test_charge_schedule_to_dict():
    payload = {
        "enabled": {"value": True},
        "scheduleType": {"value": "WEEKLY"},
        "randomizedTimeOffsetEnabled": {"value": False},
        "slots": [
            {"start": "22:00", "end": "06:00", "days": ["MON", "TUE"]},
        ],
    }
    schedule = ChargeSchedule.from_dict(payload)
    result = schedule.to_dict()
    assert result["enabled"] is True
    assert result["scheduleType"] == "WEEKLY"
    assert result["randomizedTimeOffsetEnabled"] is False
    assert len(result["slots"]) == 1
    assert result["slots"][0] == {"start": "22:00", "end": "06:00", "days": ["MON", "TUE"]}
