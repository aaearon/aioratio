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
    ChargerDiagnostics,
    ChargerFirmwareStatus,
    ChargerOverview,
    ChargerStatus,
    ChargerStatusError,
    CommandRequest,
    CpmsConfig,
    DelayedStartSetting,
    Indicators,
    InstallerOcppSettings,
    OcppFieldStatus,
    ScheduleSlot,
    Session,
    SessionHistoryPage,
    SolarSettings,
    StartCommandParameters,
    TimeData,
    UpperLowerLimitSetting,
    UserSettings,
    Vehicle,
    WifiStatus,
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
    assert sch.slots[0].days == ["monday", "tuesday"]
    assert sch.slots[1].start == "23:00"


def test_charge_schedule_from_per_day_get_response():
    """Parse the actual GET response shape with per-day weekSchedule."""
    payload = {
        "enabled": {"value": True},
        "scheduleType": {"value": "WeekSchedule"},
        "randomizedTimeOffsetEnabled": {"value": False},
        "weekSchedule": {
            "monday": [
                {"beginTimeHour": 22, "beginTimeMinute": 0,
                 "endTimeHour": 6, "endTimeMinute": 0, "chargingMode": "Smart"},
            ],
            "tuesday": [],
            "wednesday": [],
            "thursday": [],
            "friday": [],
            "saturday": [
                {"beginTimeHour": 23, "beginTimeMinute": 30,
                 "endTimeHour": 7, "endTimeMinute": 0, "chargingMode": "Smart"},
            ],
            "sunday": [],
        },
    }
    sch = ChargeSchedule.from_dict(payload)
    assert sch.enabled is True
    assert sch.schedule_type == "WeekSchedule"
    assert len(sch.slots) == 2
    assert sch.slots[0].start == "22:00"
    assert "monday" in sch.slots[0].days
    assert sch.slots[0].charging_mode == "Smart"
    assert sch.slots[1].start == "23:30"
    assert "saturday" in sch.slots[1].days


def test_charge_schedule_with_delayed_start():
    """Parse delayedStart from GET response (value-wrapped inner fields)."""
    payload = {
        "enabled": {"value": True},
        "scheduleType": {"value": "DelayedStart"},
        "delayedStart": {
            "value": {
                "beginTimeHour": {"value": 3, "isChangeAllowed": True},
                "beginTimeMinute": {"value": 15, "isChangeAllowed": True},
                "chargingMode": {"value": "Smart", "isChangeAllowed": True},
            },
            "isChangeAllowed": True,
        },
    }
    sch = ChargeSchedule.from_dict(payload)
    assert sch.delayed_start is not None
    assert sch.delayed_start.begin_time_hour == 3
    assert sch.delayed_start.begin_time_minute == 15
    assert sch.delayed_start.charging_mode == "Smart"


def test_delayed_start_setting_to_dict():
    ds = DelayedStartSetting(begin_time_hour=22, begin_time_minute=30,
                             charging_mode="Smart")
    result = ds.to_dict()
    assert result == {
        "beginTimeHour": 22,
        "beginTimeMinute": 30,
        "chargingMode": "Smart",
    }


def test_delayed_start_setting_from_flat_dict():
    """Parse flat dict (PUT shape or direct construction)."""
    ds = DelayedStartSetting.from_dict({
        "beginTimeHour": 7,
        "beginTimeMinute": 0,
        "chargingMode": "PureSolar",
    })
    assert ds.begin_time_hour == 7
    assert ds.begin_time_minute == 0
    assert ds.charging_mode == "PureSolar"


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
    """ScheduleSlot.to_dict() emits APK ScheduledChargingSession shape."""
    payload = {"start": "22:00", "end": "06:00", "days": ["MON", "TUE"]}
    slot = ScheduleSlot.from_dict(payload)
    result = slot.to_dict()
    assert result == {"beginTimeHour": 22, "beginTimeMinute": 0,
                      "endTimeHour": 6, "endTimeMinute": 0}


def test_schedule_slot_to_dict_alternative_keys():
    payload = {"startTime": "23:30", "endTime": "07:15", "days": ["SAT"]}
    slot = ScheduleSlot.from_dict(payload)
    result = slot.to_dict()
    assert result == {"beginTimeHour": 23, "beginTimeMinute": 30,
                      "endTimeHour": 7, "endTimeMinute": 15}


def test_schedule_slot_to_dict_with_charging_mode():
    slot = ScheduleSlot(start="22:00", end="06:00", days=["monday"],
                        charging_mode="Smart")
    result = slot.to_dict()
    assert result["chargingMode"] == "Smart"


def test_charge_schedule_to_dict():
    """ChargeSchedule.to_dict() emits per-day weekSchedule for PUT."""
    payload = {
        "enabled": {"value": True},
        "scheduleType": {"value": "WeekSchedule"},
        "randomizedTimeOffsetEnabled": {"value": False},
        "slots": [
            {"start": "22:00", "end": "06:00", "days": ["MON", "TUE"]},
        ],
    }
    schedule = ChargeSchedule.from_dict(payload)
    result = schedule.to_dict()
    assert result["enabled"] is True
    assert result["scheduleType"] == "WeekSchedule"
    assert result["randomizedTimeOffsetEnabled"] is False
    assert "weekSchedule" in result
    week = result["weekSchedule"]
    assert len(week["monday"]) == 1
    assert week["monday"][0] == {"beginTimeHour": 22, "beginTimeMinute": 0,
                                  "endTimeHour": 6, "endTimeMinute": 0}
    assert len(week["tuesday"]) == 1
    assert week["wednesday"] == []


def test_charge_schedule_to_dict_with_delayed_start():
    schedule = ChargeSchedule(
        enabled=True,
        schedule_type="DelayedStart",
        delayed_start=DelayedStartSetting(
            begin_time_hour=7, begin_time_minute=0, charging_mode="Smart",
        ),
    )
    result = schedule.to_dict()
    assert result["delayedStart"] == {
        "beginTimeHour": 7,
        "beginTimeMinute": 0,
        "chargingMode": "Smart",
    }


# ----- ChargerDiagnostics ---------------------------------------------------


_DIAG_FULL = {
    "productInformation": {
        "connectivityController": {
            "firmwareVersion": "1.2.3",
            "hardwareVersion": "HW-CC-1",
        },
        "mainController": {
            "firmwareVersion": "4.5.6",
            "hardwareType": "CPC-V2",
            "hardwareVersion": "HW-MC-2",
            "serialNumber": "CPC-SN-001",
        },
        "app": {"version": "3.9.1"},
    },
    "networkStatus": {
        "isTimeSynchronized": True,
        "connectionMedium": "WIFI",
        "wifi": {
            "connected": True,
            "ipv4ReportedIfConnected": True,
            "ipv4": {"address": "192.168.1.50", "netmask": "255.255.255.0", "gateway": "192.168.1.1"},
            "ssid": "HomeNetwork",
            "rssi": -55,
        },
        "ethernet": {
            "connected": False,
            "ipv4ReportedIfConnected": False,
            "ipv4": None,
        },
    },
    "backendStatus": {"connected": True},
    "ocppStatus": {
        "connected": True,
        "enabled": True,
        "cpms": {"name": "Operator1", "url": "ws://ocpp.example.com/cp"},
    },
}


def test_charger_diagnostics_from_dict_full():
    d = ChargerDiagnostics.from_dict(_DIAG_FULL)
    assert d.product_information is not None
    pi = d.product_information
    assert pi.main_controller is not None
    assert pi.main_controller.serial_number == "CPC-SN-001"
    assert pi.main_controller.hardware_type == "CPC-V2"
    assert pi.main_controller.firmware_version == "4.5.6"
    assert pi.connectivity_controller is not None
    assert pi.connectivity_controller.firmware_version == "1.2.3"
    assert pi.connectivity_controller.hardware_version == "HW-CC-1"

    ns = d.network_status
    assert ns is not None
    assert ns.is_time_synchronized is True
    assert ns.connection_medium == "WIFI"
    assert ns.wifi is not None
    assert ns.wifi.connected is True
    assert ns.wifi.ssid == "HomeNetwork"
    assert ns.wifi.rssi == -55
    assert ns.wifi.ipv4 is not None
    assert ns.wifi.ipv4.address == "192.168.1.50"
    assert ns.ethernet is not None
    assert ns.ethernet.connected is False

    assert d.backend_status is not None
    assert d.backend_status.connected is True

    assert d.ocpp_status is not None
    assert d.ocpp_status.connected is True
    assert d.ocpp_status.enabled is True
    assert d.ocpp_status.cpms_name == "Operator1"
    assert d.ocpp_status.cpms_url == "ws://ocpp.example.com/cp"


def test_wifi_status_from_dict_configured_ssid_with_fallback():
    status = WifiStatus.from_dict(
        {"configuredSsid": "MyWifi", "rssi": -65, "connected": True}
    )
    assert status.ssid == "MyWifi"
    assert status.rssi == -65
    assert status.connected is True

    fallback_status = WifiStatus.from_dict(
        {"ssid": "LegacyWifi", "rssi": -70, "connected": False}
    )
    assert fallback_status.ssid == "LegacyWifi"
    assert fallback_status.rssi == -70
    assert fallback_status.connected is False


def test_charger_diagnostics_from_dict_empty():
    d = ChargerDiagnostics.from_dict({})
    assert d.product_information is None
    assert d.network_status is None
    assert d.backend_status is None
    assert d.ocpp_status is None


def test_charger_diagnostics_missing_nested_fields():
    d = ChargerDiagnostics.from_dict({
        "productInformation": {},
        "networkStatus": {"connectionMedium": "ETHERNET"},
        "backendStatus": {},
    })
    assert d.product_information is not None
    assert d.product_information.main_controller is None
    assert d.network_status is not None
    assert d.network_status.connection_medium == "ETHERNET"
    assert d.network_status.wifi is None
    assert d.backend_status is not None
    assert d.backend_status.connected is None


# ----- CpmsConfig -----------------------------------------------------------


def test_cpms_config_from_dict_configured_cpms_shape():
    c = CpmsConfig.from_dict({"centralSystem": "Operator A", "url": "ws://a.example.com"})
    assert c.central_system == "Operator A"
    assert c.url == "ws://a.example.com"


def test_cpms_config_from_dict_configurable_cpms_shape():
    c = CpmsConfig.from_dict({"name": "Operator B", "url": "ws://b.example.com", "cpidType": "EV_NETWORK"})
    assert c.central_system == "Operator B"
    assert c.url == "ws://b.example.com"


def test_cpms_config_to_dict():
    c = CpmsConfig(central_system="Operator A", url="ws://a.example.com")
    assert c.to_dict() == {"centralSystem": "Operator A", "url": "ws://a.example.com"}


def test_cpms_config_to_dict_partial():
    c = CpmsConfig(url="ws://a.example.com")
    assert c.to_dict() == {"url": "ws://a.example.com"}


# ----- InstallerOcppSettings ------------------------------------------------


_OCPP_SETTINGS_FULL = {
    "enabled": {
        "value": True,
        "isChangeAllowed": True,
        "changeNotAllowedReason": None,
    },
    "cpms": {
        "value": {"centralSystem": "Operator A", "url": "ws://a.example.com"},
        "isChangeAllowed": True,
        "changeNotAllowedReason": None,
    },
    "chargePointIdentifier": {
        "value": "CP-001",
        "isChangeAllowed": True,
        "changeNotAllowedReason": None,
        "maxLength": 48,
    },
}


def test_installer_ocpp_settings_from_dict_full():
    s = InstallerOcppSettings.from_dict(_OCPP_SETTINGS_FULL)
    assert s.enabled is True
    assert s.cpms is not None
    assert s.cpms.central_system == "Operator A"
    assert s.cpms.url == "ws://a.example.com"
    assert s.charge_point_identifier == "CP-001"
    assert s.charge_point_identifier_max_length == 48
    assert s.enabled_status.is_change_allowed is True
    assert s.cpms_status.is_change_allowed is True
    assert s.charge_point_identifier_status.is_change_allowed is True


def test_installer_ocpp_settings_from_dict_change_not_allowed():
    data = {
        "enabled": {
            "value": True,
            "isChangeAllowed": False,
            "changeNotAllowedReason": "MANAGED_BY_OPERATOR",
        },
        "cpms": {
            "value": None,
            "isChangeAllowed": False,
            "changeNotAllowedReason": "MANAGED_BY_OPERATOR",
        },
        "chargePointIdentifier": {
            "value": "CP-XYZ",
            "isChangeAllowed": False,
            "changeNotAllowedReason": "MANAGED_BY_OPERATOR",
            "maxLength": 64,
        },
    }
    s = InstallerOcppSettings.from_dict(data)
    assert s.enabled_status.is_change_allowed is False
    assert s.enabled_status.change_not_allowed_reason == "MANAGED_BY_OPERATOR"
    assert s.cpms is None
    assert s.cpms_status.is_change_allowed is False
    assert s.charge_point_identifier_status.is_change_allowed is False
    assert s.charge_point_identifier_max_length == 64


def test_installer_ocpp_settings_from_dict_empty():
    s = InstallerOcppSettings.from_dict({})
    assert s.enabled is None
    assert s.cpms is None
    assert s.charge_point_identifier is None
    assert s.enabled_status.is_change_allowed is True
    assert s.charge_point_identifier_max_length is None


def test_installer_ocpp_settings_to_dict_flat():
    s = InstallerOcppSettings(
        enabled=True,
        cpms=CpmsConfig(central_system="Operator A", url="ws://a.example.com"),
        charge_point_identifier="CP-001",
        enabled_status=OcppFieldStatus(is_change_allowed=False, change_not_allowed_reason="reason"),
    )
    result = s.to_dict()
    assert result == {
        "enabled": True,
        "cpms": {"centralSystem": "Operator A", "url": "ws://a.example.com"},
        "chargePointIdentifier": "CP-001",
    }
    assert "enabledStatus" not in result
    assert "isChangeAllowed" not in result


def test_installer_ocpp_settings_to_dict_partial():
    s = InstallerOcppSettings(charge_point_identifier="NEW-CP")
    result = s.to_dict()
    assert result == {"chargePointIdentifier": "NEW-CP"}
    assert "enabled" not in result
    assert "cpms" not in result


def test_ocpp_field_status_defaults():
    status = OcppFieldStatus()
    assert status.is_change_allowed is True
    assert status.change_not_allowed_reason is None


# ----- Session / TimeData to_dict round-trips --------------------------------

def test_time_data_to_dict():
    td = TimeData(time=1_700_000_000, type="start", user_uuid="u-123")
    result = td.to_dict()
    assert result == {"time": 1_700_000_000, "type": "start", "userUuid": "u-123"}


def test_time_data_to_dict_nulls():
    td = TimeData(time=0)
    result = td.to_dict()
    assert result == {"time": 0, "type": None, "userUuid": None}
    assert TimeData.from_dict(result).time == 0


def test_session_to_dict_round_trip():
    raw = {
        "sessionId": "sess-1",
        "chargerSerialNumber": "SN001",
        "totalChargingEnergy": 12345,
        "begin": {"time": 1_700_000_000, "type": None, "userUuid": None},
        "end": {"time": 1_700_003_600, "type": None, "userUuid": None},
        "userId": "user-42",
        "vehicle": {
            "vehicleId": "v-1",
            "vehicleName": "My EV",
            "licensePlate": None,
            "vehicleState": None,
        },
    }
    session = Session.from_dict(raw)
    result = session.to_dict()
    # Round-trip: deserialise the output and compare field-by-field.
    restored = Session.from_dict(result)
    assert restored.session_id == "sess-1"
    assert restored.total_charging_energy == 12345
    assert restored.begin is not None and restored.begin.time == 1_700_000_000
    assert restored.end is not None and restored.end.time == 1_700_003_600
    assert restored.vehicle is not None and restored.vehicle.vehicle_name == "My EV"


def test_session_to_dict_no_vehicle():
    session = Session(
        session_id="s2",
        charger_serial_number="SN002",
        total_charging_energy=0,
    )
    result = session.to_dict()
    assert result["vehicle"] is None
    assert result["begin"] is None
    assert result["end"] is None
    restored = Session.from_dict(result)
    assert restored.session_id == "s2"
    assert restored.vehicle is None
