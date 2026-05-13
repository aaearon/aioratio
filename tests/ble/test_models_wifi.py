"""Wi-Fi BLE models."""

from __future__ import annotations

from aioratio.ble.models import WifiAccessPoint, WifiConnectResponse, WifiScanResponse


def test_wifi_scan_parses_count() -> None:
    raw = {"transaction": "t", "numberOfFoundNetworks": 4, "result": "Success"}
    parsed = WifiScanResponse.from_dict(raw)
    assert parsed.number_of_found_networks == 4


def test_wifi_access_point_parses_full() -> None:
    raw = {
        "transaction": "t",
        "index": 0,
        "ssid": "home",
        "rssi": -55,
        "result": "Success",
    }
    parsed = WifiAccessPoint.from_dict(raw)
    assert parsed.ssid == "home"
    assert parsed.rssi == -55


def test_wifi_connect_response_minimal() -> None:
    parsed = WifiConnectResponse.from_dict({"transaction": "t", "result": "Failed"})
    assert parsed.result == "Failed"
