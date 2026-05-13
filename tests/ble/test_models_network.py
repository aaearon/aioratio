"""``NetworkStatusResponse`` + nested wifi/ethernet/ipv4."""

from __future__ import annotations

import pytest

from aioratio.ble.models import (
    EthernetInfo,
    Ipv4Info,
    NetworkStatusResponse,
    WifiInfo,
    b64_encode_text,
)

from ._serializer_refs import SERIALIZER_KEYS


def _attr_path(obj: object, path: str) -> object:
    for name in path.split("."):
        obj = getattr(obj, name)
    return obj


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


@pytest.mark.parametrize(
    ("serializer_name", "model", "sample", "attribute_path", "expected"),
    [
        (
            "GetNetworkStatusResponse",
            NetworkStatusResponse,
            {
                "transaction": "t",
                "result": "success",
                "isTimeSynchronized": True,
                "connectionMedium": "wifi",
                "wifi": {
                    "connected": True,
                    "configuredSsid": b64_encode_text("TestNet"),
                    "rssi": -71,
                    "ipv4": {
                        "address": "10.0.0.42",
                        "netmask": "255.255.255.0",
                        "gateway": "10.0.0.1",
                    },
                },
                "ethernet": {
                    "connected": False,
                    "ipv4": {
                        "address": "10.0.0.43",
                        "netmask": "255.255.255.0",
                        "gateway": "10.0.0.1",
                    },
                },
            },
            "wifi.ssid",
            "TestNet",
        ),
        (
            "GetNetworkStatusResponse$Wifi",
            WifiInfo,
            {
                "connected": True,
                "configuredSsid": b64_encode_text("TestNet"),
                "rssi": -71,
                "ipv4": {
                    "address": "10.0.0.42",
                    "netmask": "255.255.255.0",
                    "gateway": "10.0.0.1",
                },
            },
            "ssid",
            "TestNet",
        ),
        (
            "GetNetworkStatusResponse$Ethernet",
            EthernetInfo,
            {
                "connected": True,
                "ipv4": {
                    "address": "10.0.0.43",
                    "netmask": "255.255.255.0",
                    "gateway": "10.0.0.1",
                },
            },
            "ipv4.gateway",
            "10.0.0.1",
        ),
        (
            "GetNetworkStatusResponse$Ipv4",
            Ipv4Info,
            {
                "address": "10.0.0.42",
                "netmask": "255.255.255.0",
                "gateway": "10.0.0.1",
            },
            "gateway",
            "10.0.0.1",
        ),
    ],
)
def test_network_status_keys_match_serializer(
    serializer_name: str,
    model: object,
    sample: dict[str, object],
    attribute_path: str,
    expected: object,
) -> None:
    assert tuple(sample) == SERIALIZER_KEYS[serializer_name]

    parsed = model.from_dict(sample)

    assert _attr_path(parsed, attribute_path) == expected
