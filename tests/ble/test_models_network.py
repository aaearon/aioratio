"""``NetworkStatusResponse`` + nested wifi/ethernet/ipv4."""

from __future__ import annotations

from aioratio.ble.models import NetworkStatusResponse, b64_encode_text


def test_network_status_full_payload() -> None:
    ssid_plain = "TestNet"
    ssid_b64 = b64_encode_text(ssid_plain)
    raw = {
        "transaction": "t",
        "result": "success",
        "isTimeSynchronized": True,
        "connectionMedium": "wifi",
        "wifi": {
            "connected": True,
            "configuredSsid": ssid_b64,
            "rssi": -71,
            "ipv4": {
                "address": "10.0.0.42",
                "netmask": "255.255.255.0",
                "gateway": "10.0.0.1",
            },
        },
        "ethernet": {"connected": False},
    }
    parsed = NetworkStatusResponse.from_dict(raw)
    assert parsed.is_time_synchronized is True
    assert parsed.connection_medium == "wifi"
    assert parsed.wifi is not None
    assert parsed.wifi.connected is True
    assert parsed.wifi.ssid == ssid_plain
    assert parsed.wifi.ssid_raw == ssid_b64
    assert parsed.wifi.rssi == -71
    assert parsed.wifi.ipv4 is not None
    assert parsed.wifi.ipv4.address == "10.0.0.42"
    assert parsed.ethernet is not None
    assert parsed.ethernet.connected is False
    assert parsed.ethernet.ipv4 is None
