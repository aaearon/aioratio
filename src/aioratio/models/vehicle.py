"""Vehicle dataclass model.

Source: ``vehicles/domain/model/Vehicle.java`` and
``vehicles/data/data_source/VehicleResponse.java``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Self


@dataclass(slots=True)
class Vehicle:
    """A vehicle registered to the user.

    All fields are nullable per the Kotlin DTO (``Vehicle()`` no-arg
    ctor exists with all fields defaulting to ``null``).
    """

    vehicle_id: Optional[str] = None
    vehicle_name: Optional[str] = None
    license_plate: Optional[str] = None
    vehicle_state: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            vehicle_id=data.get("vehicleId"),
            vehicle_name=data.get("vehicleName"),
            license_plate=data.get("licensePlate"),
            vehicle_state=data.get("vehicleState"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "vehicleId": self.vehicle_id,
            "vehicleName": self.vehicle_name,
            "licensePlate": self.license_plate,
            "vehicleState": self.vehicle_state,
        }
