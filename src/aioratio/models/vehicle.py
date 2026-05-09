"""Vehicle dataclass model.

Source: ``vehicles/domain/model/Vehicle.java`` and
``vehicles/data/data_source/VehicleResponse.java``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Self


@dataclass(slots=True)
class Vehicle:
    """A vehicle registered to the user.

    All fields are nullable per the Kotlin DTO (``Vehicle()`` no-arg
    ctor exists with all fields defaulting to ``null``).
    """

    vehicle_id: str | None = None
    vehicle_name: str | None = None
    license_plate: str | None = None
    vehicle_state: str | None = None

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
