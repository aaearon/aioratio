"""``GetChargerSensorValuesResponse`` parsing."""

from __future__ import annotations

from aioratio.ble.models import ChargerSensorValuesResponse


def test_sensor_values_full_payload() -> None:
    raw = {
        "transaction": "t",
        "result": "Success",
        "actualMainsVoltagePhase1": 230,
        "actualMainsVoltagePhase2": 231,
        "actualMainsVoltagePhase3": 229,
        "actualSensorBoxCurrentPhase1": 6,
        "actualSensorBoxCurrentPhase2": 0,
        "actualSensorBoxCurrentPhase3": 0,
    }
    parsed = ChargerSensorValuesResponse.from_dict(raw)
    assert parsed.actual_mains_voltage_phase_1 == 230
    assert parsed.actual_sensor_box_current_phase_1 == 6


def test_sensor_values_missing_phase_is_none() -> None:
    raw = {"transaction": "t", "result": "Success"}
    parsed = ChargerSensorValuesResponse.from_dict(raw)
    assert parsed.actual_mains_voltage_phase_1 is None
    assert parsed.actual_sensor_box_current_phase_3 is None
