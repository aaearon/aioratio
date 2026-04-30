"""Charge-session history dataclass models.

Sources: ``charger_history/domain/model/Session.java``,
``TimeDataModel.java`` and ``ChargeSessionHistoryResponse.java``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Self

from .vehicle import Vehicle


@dataclass(slots=True)
class TimeData:
    """Begin/end marker for a session.

    Source: ``TimeDataModel.java``.
    """

    time: int
    type: Optional[str] = None
    user_uuid: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            time=int(data.get("time", 0)),
            type=data.get("type"),
            user_uuid=data.get("userUuid"),
        )


@dataclass(slots=True)
class Session:
    """A single completed charge session.

    Source: ``Session.java``.
    """

    session_id: str
    charger_serial_number: str
    total_charging_energy: int
    begin: Optional[TimeData] = None
    end: Optional[TimeData] = None
    user_id: Optional[str] = None
    vehicle: Optional[Vehicle] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        b = data.get("begin")
        e = data.get("end")
        v = data.get("vehicle")
        return cls(
            session_id=data["sessionId"],
            charger_serial_number=data["chargerSerialNumber"],
            total_charging_energy=int(data.get("totalChargingEnergy", 0)),
            begin=TimeData.from_dict(b) if isinstance(b, dict) else None,
            end=TimeData.from_dict(e) if isinstance(e, dict) else None,
            user_id=data.get("userId"),
            vehicle=Vehicle.from_dict(v) if isinstance(v, dict) else None,
        )


@dataclass(slots=True)
class SessionHistoryPage:
    """Paginated wrapper around a list of sessions.

    Source: ``ChargeSessionHistoryResponse.java`` — exposes
    ``chargeSessions`` and ``nextToken`` JSON keys.
    """

    sessions: list[Session] = field(default_factory=list)
    next_token: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        raw = data.get("chargeSessions") or data.get("sessions") or []
        return cls(
            sessions=[Session.from_dict(s) for s in raw if isinstance(s, dict)],
            next_token=data.get("nextToken"),
        )
