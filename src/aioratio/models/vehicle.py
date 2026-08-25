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
        """Emit the POST/PUT shape, omitting fields that are ``None``.

        ``Vehicle$$serializer.java`` declares all four elements optional
        (``addElement(..., true)``) and nullable, and ``core/JsonKt.java``
        configures the app's ``Json`` with ``explicitNulls = false``. The app
        therefore never sends ``"vehicleId": null`` when creating a vehicle;
        neither do we.
        """
        out: dict[str, Any] = {}
        if self.vehicle_name is not None:
            out["vehicleName"] = self.vehicle_name
        if self.license_plate is not None:
            out["licensePlate"] = self.license_plate
        if self.vehicle_id is not None:
            out["vehicleId"] = self.vehicle_id
        if self.vehicle_state is not None:
            out["vehicleState"] = self.vehicle_state
        return out
