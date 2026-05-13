"""``BleClient`` end-to-end against ``FakeBleTransport``."""

from __future__ import annotations

import asyncio
import json

import pytest

from aioratio.ble.client import BleClient
from aioratio.ble.models import (
    ChargeControl,
    SolarSettingsUpdate,
    TimeSettingsUpdate,
    UserSettingsUpdate,
)
from aioratio.exceptions import (
    RatioBleConnectionError,
    RatioBleNotBondedError,
    RatioBleUnsupportedCommandError,
)

from .fake_transport import FakeBleTransport


@pytest.fixture()
def transport() -> FakeBleTransport:
    return FakeBleTransport(protocol_version=6)  # BASELINE_4_0_0 covers every cmd


async def _connected_client(transport: FakeBleTransport) -> BleClient:
    client = BleClient(transport=transport)
    await client.connect()
    return client


async def test_connect_reads_protocol_version_from_transport() -> None:
    transport = FakeBleTransport(protocol_version=3)
    client = BleClient(transport=transport)
    await client.connect()
    assert client.is_connected is True
    assert client.protocol_version == 3
    await client.disconnect()
    assert client.is_connected is False


async def test_must_provide_exactly_one_of_device_or_transport() -> None:
    with pytest.raises(TypeError):
        BleClient()


async def test_get_charger_status_round_trip(transport: FakeBleTransport) -> None:
    transport.register_static(
        "ChargerStatusRequest",
        "ChargerStatusResponse",
        {
            "result": "success",
            "cloudConnectionState": "Connected",
            "isChargeStartAllowed": True,
            "isChargeStopAllowed": False,
            "indicators": {
                "chargingState": "Idle",
                "actualChargingPower": 0,
                "isVehicleConnected": False,
                "isChargeSessionActive": False,
                "isPowerReducedByDSO": False,
                "isChargingPaused": False,
                "isChargingAuthorized": None,
                "isChargingDisabled": False,
                "isChargingDisabledReason": None,
                "errors": [],
            },
        },
    )
    client = await _connected_client(transport)
    try:
        status = await client.get_charger_status()
        assert status.result == "success"
        assert status.is_charge_start_allowed is True
        assert status.indicators is not None
        assert status.indicators.charging_state == "Idle"
        # One write happened, with the expected classname.
        assert len(transport.writes) == 1
        assert transport.writes[0].startswith(b"ChargerStatusRequest")
    finally:
        await client.disconnect()


async def test_charge_control_sends_control_field(transport: FakeBleTransport) -> None:
    transport.register_static(
        "ChargeControlRequest",
        "ChargeControlResponse",
        {"result": "success"},
    )
    client = await _connected_client(transport)
    try:
        resp = await client.charge_control(ChargeControl.STOP)
        assert resp.result == "success"
        # Check the on-wire body had control=Stop.
        body = json.loads(transport.writes[0][len("ChargeControlRequest") : -1])
        assert body["control"] == "Stop"
        # And a 16-char alphanumeric transaction ID.
        assert len(body["transaction"]) == 16
    finally:
        await client.disconnect()


async def test_set_user_settings_emits_only_provided_fields(
    transport: FakeBleTransport,
) -> None:
    transport.register_static(
        "SetUserSettingsRequest",
        "SetUserSettingsResponse",
        {"result": "success"},
    )
    client = await _connected_client(transport)
    try:
        await client.set_user_settings(UserSettingsUpdate(maximum_charging_current=16))
        body = json.loads(transport.writes[0][len("SetUserSettingsRequest") : -1])
        # Only the explicit field + transaction.
        assert set(body.keys()) == {"maximumChargingCurrent", "transaction"}
        assert body["maximumChargingCurrent"] == 16
    finally:
        await client.disconnect()


async def test_set_solar_settings_serializes_keys(transport: FakeBleTransport) -> None:
    transport.register_static(
        "SetSolarSettingsRequest",
        "SetSolarSettingsResponse",
        {"result": "success"},
    )
    client = await _connected_client(transport)
    try:
        await client.set_solar_settings(
            SolarSettingsUpdate(smart_solar_starting_current=6, sun_off_delay_minutes=5)
        )
        body = json.loads(transport.writes[0][len("SetSolarSettingsRequest") : -1])
        assert body["smartSolarStartingCurrent"] == 6
        assert body["sunOffDelayMinutes"] == 5
        assert "pureSolarStartingCurrent" not in body
    finally:
        await client.disconnect()


async def test_set_time_settings_required_fields(transport: FakeBleTransport) -> None:
    transport.register_static(
        "SetTimeSettingsRequest",
        "SetTimeSettingsResponse",
        {"result": "success"},
    )
    client = await _connected_client(transport)
    try:
        await client.set_time_settings(
            TimeSettingsUpdate(
                time_zone_area_location="Europe/Amsterdam",
                time_zone_posix="CET-1CEST,M3.5.0,M10.5.0/3",
            )
        )
        body = json.loads(transport.writes[0][len("SetTimeSettingsRequest") : -1])
        assert body["timeZoneAreaLocation"] == "Europe/Amsterdam"
        assert body["timeZonePosix"].startswith("CET")
    finally:
        await client.disconnect()


async def test_wifi_connect_base64_encodes_ssid(transport: FakeBleTransport) -> None:
    """Per the 2026-05-13 walk, SSIDs are base64-encoded on the wire.

    Password handling is provisional — passing a non-``None`` password must
    emit a ``RuntimeWarning`` so the caller can decide whether to proceed.
    """
    import warnings

    transport.register_static(
        "WifiConnectRequest",
        "WifiConnectResponse",
        {"result": "success"},
    )
    client = BleClient(transport=transport)
    await client.connect()
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            await client.wifi_connect("TestNet", password="hunter2")
        body = json.loads(transport.writes[0][len("WifiConnectRequest") : -1])
        assert body["ssid"] == "VGVzdE5ldA=="
        assert body["password"] == "hunter2"
        runtime_warnings = [w for w in caught if issubclass(w.category, RuntimeWarning)]
        assert any("password wire format" in str(w.message) for w in runtime_warnings)
    finally:
        await client.disconnect()


async def test_wifi_connect_open_network_no_warning(transport: FakeBleTransport) -> None:
    """``password=None`` (open network) must not emit a RuntimeWarning."""
    import warnings

    transport.register_static(
        "WifiConnectRequest",
        "WifiConnectResponse",
        {"result": "success"},
    )
    client = BleClient(transport=transport)
    await client.connect()
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            await client.wifi_connect("TestNet", password=None)
        runtime_warnings = [w for w in caught if issubclass(w.category, RuntimeWarning)]
        assert runtime_warnings == []
    finally:
        await client.disconnect()


async def test_wifi_scan_iterates_access_points(transport: FakeBleTransport) -> None:
    transport.register_static(
        "WifiScanRequest",
        "WifiScanResponse",
        {"result": "success", "numberOfFoundNetworks": 2},
    )

    def ap_factory(req: dict) -> tuple[str, dict]:
        from aioratio.ble.models import b64_encode_text

        idx = int(req["index"])
        return "WifiAccessPointResponse", {
            "transaction": req["transaction"],
            "result": "success",
            "index": idx,
            "ssid": b64_encode_text(f"net-{idx}"),
            "rssi": -50 - idx,
        }

    transport.register_response("WifiAccessPointRequest", ap_factory)

    client = await _connected_client(transport)
    try:
        aps = await client.wifi_scan()
        # SSIDs are surfaced decoded from base64.
        assert [a.ssid for a in aps] == ["net-0", "net-1"]
        assert [a.rssi for a in aps] == [-50, -51]
    finally:
        await client.disconnect()


async def test_command_times_out_when_no_response(transport: FakeBleTransport) -> None:
    # Don't register any responder — request will hang past the timeout.
    client = BleClient(transport=transport, command_timeout=0.05)
    await client.connect()
    try:
        with pytest.raises(RatioBleConnectionError, match="timeout"):
            await client.get_charger_status()
    finally:
        await client.disconnect()


async def test_unsupported_command_for_negotiated_version_raises() -> None:
    transport = FakeBleTransport(protocol_version=3)  # below BASELINE_4_0_0
    client = BleClient(transport=transport)
    await client.connect()
    try:
        with pytest.raises(RatioBleUnsupportedCommandError):
            await client.get_product_information()
        # No write should have been issued.
        assert transport.writes == []
    finally:
        await client.disconnect()


async def test_exchange_requires_connection(transport: FakeBleTransport) -> None:
    client = BleClient(transport=transport)
    with pytest.raises(RatioBleConnectionError):
        await client.get_charger_status()


async def test_disconnect_fails_pending_transactions(transport: FakeBleTransport) -> None:
    """Background pending request must surface a clear error on disconnect."""
    client = BleClient(transport=transport, command_timeout=10.0)
    await client.connect()
    task = asyncio.create_task(client.get_charger_status())
    # Give the event loop a beat to start the task.
    await asyncio.sleep(0)
    await client.disconnect()
    with pytest.raises(RatioBleConnectionError):
        await task


async def test_disconnected_callback_runs(transport: FakeBleTransport) -> None:
    called = []
    client = BleClient(transport=transport, disconnected_callback=lambda: called.append(1))
    await client.connect()
    await client.disconnect()
    assert called == [1]


class _AuthFailingTransport(FakeBleTransport):
    """Surfaces an Insufficient-Authentication-style error from read_version.

    Matches what bleak's BlueZ backend reports when the peer requires bonding:
    the Version characteristic read fails with the peer kicking the link
    before the GATT op completes.
    """

    def __init__(self, message: str) -> None:
        super().__init__()
        self._message = message

    async def read_version(self) -> int:
        raise OSError(self._message)


class _ReadVersionFailingTransport(FakeBleTransport):
    async def read_version(self) -> int:
        raise RuntimeError("boom")


async def test_connect_disconnects_transport_when_read_version_fails() -> None:
    transport = _ReadVersionFailingTransport()
    client = BleClient(transport=transport)

    with pytest.raises(RatioBleConnectionError) as info:
        await client.connect()

    assert isinstance(info.value.__cause__, RuntimeError)
    assert transport.disconnected_count == 1
    assert client.is_connected is False


@pytest.mark.parametrize(
    "message",
    [
        "Could not read Version characteristic: Insufficient Authentication",
        "org.bluez.Error.Failed: ATT error: 0x05",
        "GATT operation failed: Insufficient Encryption",
        "ATT error: 0x0f",  # insufficient encryption
        "ATT error: 0x0c",
        "Insufficient Encryption Key Size",
        "not paired",
    ],
)
async def test_connect_raises_not_bonded_on_auth_failure(message: str) -> None:
    transport = _AuthFailingTransport(message)
    client = BleClient(transport=transport)
    with pytest.raises(RatioBleNotBondedError):
        await client.connect()
    assert client.is_connected is False


async def test_connect_raises_generic_connection_error_on_other_failures() -> None:
    transport = _AuthFailingTransport("Device disconnected before reply")
    client = BleClient(transport=transport)
    with pytest.raises(RatioBleConnectionError) as info:
        await client.connect()
    # Must not be the bond-required subclass — caller distinguishes UX paths.
    assert not isinstance(info.value, RatioBleNotBondedError)
    assert transport.disconnected_count == 1
    assert client.is_connected is False


async def test_async_context_manager_connects_and_disconnects(
    transport: FakeBleTransport,
) -> None:
    async with BleClient(transport=transport) as client:
        assert client.is_connected is True
    assert transport.disconnected_count == 1


async def test_async_context_manager_disconnects_on_exception(
    transport: FakeBleTransport,
) -> None:
    class _Boom(Exception):
        pass

    with pytest.raises(_Boom):
        async with BleClient(transport=transport):
            raise _Boom

    assert transport.disconnected_count == 1


async def test_from_service_info_constructs_with_device_from_info() -> None:
    """Anything carrying a ``BLEDevice`` on ``.device`` works.

    Matches the shape of HA's ``BluetoothServiceInfoBleak`` without importing
    the HA-only type.
    """
    from types import SimpleNamespace

    from bleak.backends.device import BLEDevice

    # Minimal ``details`` keeps BleakClient's BlueZ backend constructor happy
    # without touching any real adapter.
    fake_device = BLEDevice(
        "AA:BB:CC:DD:EE:FF",
        "RATIO_TEST",
        {"path": "/org/bluez/hci0/dev_AA_BB_CC_DD_EE_FF"},
    )
    info = SimpleNamespace(device=fake_device)

    client = BleClient.from_service_info(info)
    assert isinstance(client, BleClient)
    assert client.is_connected is False
