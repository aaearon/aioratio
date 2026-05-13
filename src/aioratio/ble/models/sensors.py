"""``GetChargerSensorValues`` response.

Source: ``charger/data/data_source/ble/GetChargerSensorValuesResponse$$serializer.java``.
Wire keys: ``transaction, result, actualMainsVoltagePhase{1,2,3},
actualSensorBoxCurrentPhase{1,2,3}``.

**Units (confirmed on 2026-05-13 against v3.13.2 firmware):**

* Voltages are in deciV (0.1V resolution). E.g. ``2290`` means **229.0 V**.
* Currents are in deciA (0.1A resolution). E.g. ``-17`` means **-1.7 A**.

The raw int fields preserve the wire values; the ``*_volts`` / ``*_amps``
properties scale them for human-friendly display.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Self


@dataclass(slots=True)
class ChargerSensorValuesResponse:
    transaction: str
    result: str
    actual_mains_voltage_phase_1: int | None = None
    actual_mains_voltage_phase_2: int | None = None
    actual_mains_voltage_phase_3: int | None = None
    actual_sensor_box_current_phase_1: int | None = None
    actual_sensor_box_current_phase_2: int | None = None
    actual_sensor_box_current_phase_3: int | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            transaction=data["transaction"],
            result=data["result"],
            actual_mains_voltage_phase_1=_opt_int(data.get("actualMainsVoltagePhase1")),
            actual_mains_voltage_phase_2=_opt_int(data.get("actualMainsVoltagePhase2")),
            actual_mains_voltage_phase_3=_opt_int(data.get("actualMainsVoltagePhase3")),
            actual_sensor_box_current_phase_1=_opt_int(data.get("actualSensorBoxCurrentPhase1")),
            actual_sensor_box_current_phase_2=_opt_int(data.get("actualSensorBoxCurrentPhase2")),
            actual_sensor_box_current_phase_3=_opt_int(data.get("actualSensorBoxCurrentPhase3")),
        )

    @property
    def voltage_phase_1_volts(self) -> float | None:
        return _scale(self.actual_mains_voltage_phase_1, 10)

    @property
    def voltage_phase_2_volts(self) -> float | None:
        return _scale(self.actual_mains_voltage_phase_2, 10)

    @property
    def voltage_phase_3_volts(self) -> float | None:
        return _scale(self.actual_mains_voltage_phase_3, 10)

    @property
    def current_phase_1_amps(self) -> float | None:
        return _scale(self.actual_sensor_box_current_phase_1, 10)

    @property
    def current_phase_2_amps(self) -> float | None:
        return _scale(self.actual_sensor_box_current_phase_2, 10)

    @property
    def current_phase_3_amps(self) -> float | None:
        return _scale(self.actual_sensor_box_current_phase_3, 10)


def _opt_int(v: Any) -> int | None:
    return int(v) if v is not None else None


def _scale(v: int | None, divisor: int) -> float | None:
    return None if v is None else v / divisor


__all__ = ["ChargerSensorValuesResponse"]
