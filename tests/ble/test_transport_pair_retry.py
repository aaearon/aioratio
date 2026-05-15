"""``BleakBleTransport`` must pair-and-retry on a bond-required GATT failure.

Background: ESPHome ``bluetooth_proxy`` per-connection pairing state is reset
on every disconnect. After the first connection's SMP exchange completes and
the LTK is stored in NVS, the *next* connection still goes out with
``ESP_GATT_AUTH_REQ_NONE`` and the charger rejects with ``status=15``
(insufficient encryption). The proxy only restarts encryption from the stored
LTK when ``bluetooth_device_pair`` arrives on the *live* connection — which
``bleak``'s ``client.pair()`` translates to.

So the only working pattern is: try the GATT op, and on bond-required, call
``client.pair()`` on the same connection and retry once. Pairing on a
*separate* connection (the previous home-assistant-ratio approach) succeeds
but doesn't propagate to the next read.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from bleak.exc import BleakError

from aioratio.ble.transport import BleakBleTransport, _looks_like_bond_required


def _bond_required_exc() -> BleakError:
    """A ``BleakError`` whose message matches ``_looks_like_bond_required``."""
    return BleakError(
        "Bluetooth GATT Error address=79:75:75:A4:A0:45 handle=17 error=15 "
        "description=Insufficient encryption"
    )


def _make_transport_with_mock_client(client: MagicMock) -> BleakBleTransport:
    """Construct a transport with the inner ``BleakClient`` pre-stubbed.

    Bypasses ``establish_connection`` so the test focuses on the pair-retry
    behaviour around individual GATT operations.
    """
    device = MagicMock(name="BLEDevice")
    transport = BleakBleTransport(device)
    transport._client = client  # type: ignore[attr-defined]
    return transport


@pytest.mark.asyncio
async def test_read_version_pairs_and_retries_on_bond_required() -> None:
    """A bond-required ``read_gatt_char`` triggers ``pair()`` then a single retry."""
    client = MagicMock()
    client.is_connected = True
    # First read raises bond-required; second succeeds with version byte 0x03.
    client.read_gatt_char = AsyncMock(side_effect=[_bond_required_exc(), b"\x03"])
    client.pair = AsyncMock(return_value=None)

    transport = _make_transport_with_mock_client(client)

    version = await transport.read_version()

    assert version == 3
    assert client.read_gatt_char.await_count == 2
    client.pair.assert_awaited_once()


@pytest.mark.asyncio
async def test_read_version_does_not_retry_on_unrelated_bleak_error() -> None:
    """Non-bond errors must surface without a pair attempt."""
    client = MagicMock()
    client.is_connected = True
    boom = BleakError("characteristic not found")
    client.read_gatt_char = AsyncMock(side_effect=boom)
    client.pair = AsyncMock()

    transport = _make_transport_with_mock_client(client)

    with pytest.raises(BleakError) as excinfo:
        await transport.read_version()

    assert excinfo.value is boom
    client.pair.assert_not_called()
    assert client.read_gatt_char.await_count == 1


@pytest.mark.asyncio
async def test_read_version_propagates_pair_failure() -> None:
    """If ``pair()`` itself fails the original retry path must not swallow it."""
    client = MagicMock()
    client.is_connected = True
    client.read_gatt_char = AsyncMock(side_effect=_bond_required_exc())
    pair_exc = BleakError("Pairing failed due to error: 5")
    client.pair = AsyncMock(side_effect=pair_exc)

    transport = _make_transport_with_mock_client(client)

    with pytest.raises(BleakError) as excinfo:
        await transport.read_version()

    assert excinfo.value is pair_exc
    client.pair.assert_awaited_once()
    # Original op tried once, no retry after pair failed.
    assert client.read_gatt_char.await_count == 1


@pytest.mark.asyncio
async def test_write_rx_pairs_and_retries_on_bond_required() -> None:
    """Same pattern for ``write_gatt_char`` — every GATT op needs the same guard."""
    client = MagicMock()
    client.is_connected = True
    client.write_gatt_char = AsyncMock(side_effect=[_bond_required_exc(), None])
    client.pair = AsyncMock(return_value=None)

    transport = _make_transport_with_mock_client(client)

    await transport.write_rx(b"\x00hello\x00")

    assert client.write_gatt_char.await_count == 2
    client.pair.assert_awaited_once()


@pytest.mark.asyncio
async def test_start_notify_pairs_and_retries_on_bond_required() -> None:
    """``connect`` calls ``start_notify``; bond-required there must retry too."""
    client = MagicMock()
    client.is_connected = True
    client.start_notify = AsyncMock(side_effect=[_bond_required_exc(), None])
    client.pair = AsyncMock(return_value=None)

    transport = _make_transport_with_mock_client(client)

    # Skip the establish_connection path — start with the client already wired.
    transport._notify_active = False  # type: ignore[attr-defined]

    await transport.connect()

    assert client.start_notify.await_count == 2
    client.pair.assert_awaited_once()


def test_looks_like_bond_required_recognises_esphome_gatt_error_15() -> None:
    """The marker list must catch the exact wording bleak_esphome surfaces."""
    exc = _bond_required_exc()
    assert _looks_like_bond_required(exc)
