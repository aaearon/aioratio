"""Protocol-version gate.

Each public BLE command maps to a minimum ``BleProtocolVersions`` value the
charger must report on the Version characteristic. If the negotiated version is
below the requirement, ``BleClient`` raises ``RatioBleUnsupportedCommandError``
before the request is sent.

Sources: ``doesSupport(int protocolVersion)`` on each IIpcTransaction
implementation in the decompile.
"""

from __future__ import annotations

from ..exceptions import RatioBleUnsupportedCommandError
from .const import (
    PROTOCOL_BASELINE_2_3_0,
    PROTOCOL_BASELINE_3_5_0,
    PROTOCOL_BASELINE_4_0_0,
    PROTOCOL_BASIS,
)

# Mapping: request classname -> minimum protocol version int.
MIN_PROTOCOL_VERSION: dict[str, int] = {
    # BASIS = 1
    "ChargerStatusRequest": PROTOCOL_BASIS,
    "ChargeControlRequest": PROTOCOL_BASIS,
    "FactoryResetRequest": PROTOCOL_BASIS,
    "GetChargerSensorValuesRequest": PROTOCOL_BASIS,
    "GetTimeSettingsRequest": PROTOCOL_BASIS,
    "SetTimeSettingsRequest": PROTOCOL_BASIS,
    "GetInstallerDSOSettingsRequest": PROTOCOL_BASIS,
    "SetInstallerDSOSettingsRequest": PROTOCOL_BASIS,
    "GetInstallerSettingsRequest": PROTOCOL_BASIS,
    "SetInstallerSettingsRequest": PROTOCOL_BASIS,
    "WifiScanRequest": PROTOCOL_BASIS,
    "WifiAccessPointRequest": PROTOCOL_BASIS,
    "WifiConnectRequest": PROTOCOL_BASIS,
    # BASELINE_2_3_0 = 2
    "GetUserSettingsRequest": PROTOCOL_BASELINE_2_3_0,
    "SetUserSettingsRequest": PROTOCOL_BASELINE_2_3_0,
    "GetSolarSettingsRequest": PROTOCOL_BASELINE_2_3_0,
    "SetSolarSettingsRequest": PROTOCOL_BASELINE_2_3_0,
    # BASELINE_3_5_0 = 5
    "SignChargerRegistrationRequest": PROTOCOL_BASELINE_3_5_0,
    # BASELINE_4_0_0 = 6
    "GetProductInformationRequest": PROTOCOL_BASELINE_4_0_0,
    "GetNetworkStatusRequest": PROTOCOL_BASELINE_4_0_0,
    "GetOcppStatusRequest": PROTOCOL_BASELINE_4_0_0,
    "GetBackendStatusRequest": PROTOCOL_BASELINE_4_0_0,
}


def require_version(classname: str, negotiated: int) -> None:
    """Raise if ``classname`` is unsupported at the negotiated protocol level."""
    minimum = MIN_PROTOCOL_VERSION.get(classname)
    if minimum is None:
        # Unknown command — let the charger reject it on the wire.
        return
    if negotiated < minimum:
        raise RatioBleUnsupportedCommandError(
            f"{classname} requires protocol version >= {minimum}; charger reports {negotiated}"
        )


__all__ = ["MIN_PROTOCOL_VERSION", "require_version"]
