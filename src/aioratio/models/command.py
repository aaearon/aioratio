"""Command request models.

Sources: ``charger/data/data_source/cloud/ChargerRequest.java``,
``StartCommandParameters.java``, ``GrantUpgradePermissionParameters.java``,
and the ``CHARGER_COMMAND`` sealed class which lists the three known
commands: ``start-charge``, ``stop-charge``, ``grant-upgrade-permission``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, Optional, Self

from ..exceptions import RatioApiError


def _required(data: dict[str, Any], key: str) -> Any:
    if key not in data:
        raise RatioApiError(f"missing required field: {key}")
    return data[key]


@dataclass(slots=True)
class StartCommandParameters:
    """Parameters for the ``start-charge`` command."""

    vehicle_id: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(vehicle_id=data.get("vehicleId"))

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if self.vehicle_id is not None:
            out["vehicleId"] = self.vehicle_id
        return out


@dataclass(slots=True)
class GrantUpgradePermissionParameters:
    """Parameters for ``grant-upgrade-permission``.

    # TODO: confirm against live payload — APK class exists but the
    # exact field set was not enumerated.
    """

    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(raw=dict(data))

    def to_dict(self) -> dict[str, Any]:
        return dict(self.raw)


@dataclass(slots=True)
class CommandRequest:
    """A request body posted to the charger command endpoint.

    Source: ``ChargerRequest.java``.
    """

    START_CHARGE: ClassVar[str] = "start-charge"
    STOP_CHARGE: ClassVar[str] = "stop-charge"
    GRANT_UPGRADE_PERMISSION: ClassVar[str] = "grant-upgrade-permission"

    transaction_id: str
    command: str
    start_command_parameters: Optional[StartCommandParameters] = None
    grant_upgrade_permission_parameters: Optional[GrantUpgradePermissionParameters] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        sc = data.get("startCommandParameters")
        gp = data.get("grantUpgradePermissionParameters")
        return cls(
            transaction_id=_required(data, "transactionId"),
            command=_required(data, "command"),
            start_command_parameters=(
                StartCommandParameters.from_dict(sc) if isinstance(sc, dict) else None
            ),
            grant_upgrade_permission_parameters=(
                GrantUpgradePermissionParameters.from_dict(gp) if isinstance(gp, dict) else None
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "transactionId": self.transaction_id,
            "command": self.command,
        }
        if self.start_command_parameters is not None:
            out["startCommandParameters"] = self.start_command_parameters.to_dict()
        if self.grant_upgrade_permission_parameters is not None:
            out["grantUpgradePermissionParameters"] = (
                self.grant_upgrade_permission_parameters.to_dict()
            )
        return out
