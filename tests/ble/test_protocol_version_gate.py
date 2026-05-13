"""Per-command minimum-protocol-version enforcement."""

from __future__ import annotations

import pytest

from aioratio.ble.protocol import MIN_PROTOCOL_VERSION, require_version
from aioratio.exceptions import RatioBleUnsupportedCommandError


def test_known_command_below_minimum_raises() -> None:
    # GetUserSettings requires BASELINE_2_3_0 == 2.
    with pytest.raises(RatioBleUnsupportedCommandError) as exc:
        require_version("GetUserSettingsRequest", 1)
    assert "GetUserSettingsRequest" in str(exc.value)


def test_known_command_at_or_above_minimum_passes() -> None:
    require_version("GetUserSettingsRequest", 2)
    require_version("GetUserSettingsRequest", 6)


def test_basis_command_always_passes() -> None:
    require_version("ChargerStatusRequest", 1)
    require_version("ChargerStatusRequest", 6)


def test_unknown_command_passes_through() -> None:
    """Unknown commands aren't gated — let the charger reject on the wire."""
    require_version("MysteryNewCommandRequest", 1)


def test_baseline_4_command_rejected_for_version_3_charger() -> None:
    """GetProductInformation requires version 6; observed charger reports 3."""
    with pytest.raises(RatioBleUnsupportedCommandError):
        require_version("GetProductInformationRequest", 3)


def test_protocol_table_has_expected_entries() -> None:
    # Spot-check a few entries so a rename in the source code is caught.
    assert MIN_PROTOCOL_VERSION["ChargerStatusRequest"] == 1
    assert MIN_PROTOCOL_VERSION["GetUserSettingsRequest"] == 2
    assert MIN_PROTOCOL_VERSION["GetSolarSettingsRequest"] == 2
    assert MIN_PROTOCOL_VERSION["GetProductInformationRequest"] == 6
    assert MIN_PROTOCOL_VERSION["GetNetworkStatusRequest"] == 6
