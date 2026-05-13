"""``GetChargerSensorValues`` response.

Source: ``charger/data/data_source/ble/GetChargerSensorValuesResponse$$serializer.java``.
Wire keys: ``transaction, result, actualMainsVoltagePhase{1,2,3},
actualSensorBoxCurrentPhase{1,2,3}``.

Units are not annotated in the descriptor; based on Inspiro firmware
conventions the voltage values are integer mV (or V — to be confirmed against
hardware) and currents are 0.1 A increments. The Phase 0 PoC step 7 was meant
to confirm the units; that's still pending a working hardware connect.
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


def _opt_int(v: Any) -> int | None:
    return int(v) if v is not None else None


__all__ = ["ChargerSensorValuesResponse"]
