"""``GetChargerSensorValuesResponse`` parsing."""

from __future__ import annotations

from aioratio.ble.models import ChargerSensorValuesResponse


def test_sensor_values_full_payload_in_deci_units() -> None:
    # Real-wire convention (confirmed 2026-05-13): voltages in deciV,
    # currents in deciA. e.g. 2290 == 229.0 V; -17 == -1.7 A.
    raw = {
        "transaction": "t",
        "result": "success",
        "actualMainsVoltagePhase1": 2290,
        "actualMainsVoltagePhase2": 2281,
        "actualMainsVoltagePhase3": 2282,
        "actualSensorBoxCurrentPhase1": -17,
        "actualSensorBoxCurrentPhase2": 18,
        "actualSensorBoxCurrentPhase3": 0,
    }
    parsed = ChargerSensorValuesResponse.from_dict(raw)
    assert parsed.actual_mains_voltage_phase_1 == 2290  # raw wire value
    assert parsed.voltage_phase_1_volts == 229.0  # scaled accessor
    assert parsed.actual_sensor_box_current_phase_1 == -17
    assert parsed.current_phase_1_amps == -1.7


def test_sensor_values_missing_phase_is_none() -> None:
    raw = {"transaction": "t", "result": "success"}
    parsed = ChargerSensorValuesResponse.from_dict(raw)
    assert parsed.actual_mains_voltage_phase_1 is None
    assert parsed.actual_sensor_box_current_phase_3 is None
