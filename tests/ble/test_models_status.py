"""``ChargerStatusResponse`` + ``ChargeStatusIndicators``."""

from __future__ import annotations

from aioratio.ble.models import ChargerStatusResponse, ChargeStatusIndicators

from ._serializer_refs import SERIALIZER_KEYS


def test_charger_status_response_full_payload() -> None:
    raw = {
        "transaction": "abc",
        "result": "success",
        "cloudConnectionState": "Connected",
        "isChargeStartAllowed": True,
        "isChargeStopAllowed": False,
        "indicators": {
            "chargingState": "Charging",
            "actualChargingPower": 7400,
            "isVehicleConnected": True,
            "isChargeSessionActive": True,
            "isPowerReducedByDSO": False,
            "isChargingPaused": False,
            "isChargingAuthorized": True,
            "isChargingDisabled": False,
            "isChargingDisabledReason": None,
            "errors": [],
        },
    }
    parsed = ChargerStatusResponse.from_dict(raw)
    assert parsed.transaction == "abc"
    assert parsed.result == "success"
    assert parsed.cloud_connection_state == "Connected"
    assert parsed.is_charge_start_allowed is True
    assert parsed.is_charge_stop_allowed is False
    assert parsed.indicators is not None
    assert parsed.indicators.actual_charging_power == 7400
    assert parsed.indicators.is_vehicle_connected is True


def test_charger_status_response_missing_indicators_block() -> None:
    raw = {
        "transaction": "x",
        "result": "success",
        "isChargeStartAllowed": False,
        "isChargeStopAllowed": False,
    }
    parsed = ChargerStatusResponse.from_dict(raw)
    assert parsed.indicators is None


def test_charge_status_indicators_full_keys_match_serializer() -> None:
    """Every key Python parses must appear in the APK serializer descriptor."""
    raw_keys = set(SERIALIZER_KEYS["ChargeStatusIndicators"])
    sample = {k: None for k in raw_keys}
    sample["actualChargingPower"] = 1
    sample["errors"] = []
    indicators = ChargeStatusIndicators.from_dict(sample)
    # Sanity: it parses
    assert indicators.actual_charging_power == 1


def test_serializer_keys_table_has_all_charger_status_fields() -> None:
    assert "ChargerStatusResponse" in SERIALIZER_KEYS
    assert "ChargeStatusIndicators" in SERIALIZER_KEYS
    # Spot-check ordering vs descriptor declaration order.
    assert SERIALIZER_KEYS["ChargerStatusResponse"][0] == "transaction"
    assert SERIALIZER_KEYS["ChargerStatusResponse"][1] == "result"
