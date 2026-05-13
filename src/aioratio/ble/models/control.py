"""``ChargeControl`` request payload + response.

Sources:
  - ``charger/data/data_source/ble/ChargeControlRequest$$serializer.java`` (transaction, control)
  - ``charger/data/data_source/ble/ChargeControlResponse$$serializer.java`` (transaction, result)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Self


class ChargeControl(StrEnum):
    """Allowed values for ``ChargeControlRequest.control``.

    Sourced from Inspiro firmware conventions; ``Start``/``Stop`` are the
    pair the mobile app uses on the start/stop buttons.
    """

    START = "Start"
    STOP = "Stop"


@dataclass(slots=True)
class ChargeControlResponse:
    transaction: str
    result: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(transaction=data["transaction"], result=data["result"])


__all__ = ["ChargeControl", "ChargeControlResponse"]
