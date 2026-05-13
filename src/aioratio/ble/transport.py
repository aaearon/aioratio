"""BLE transport abstraction.

``BleTransport`` is a thin protocol around the GATT operations the IPC client
needs. Production uses ``BleakBleTransport``, which delegates to
``bleak_retry_connector.establish_connection`` for resilient connects with
retry/backoff. Tests substitute a ``FakeBleTransport``.

The transport is intentionally minimal: connect/disconnect, version-byte read,
RX-characteristic write, and a single TX-notify callback hook. Everything else
(framing, transactions, protocol gating) lives one layer up in ``BleClient``.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from .const import RX_CHAR_UUID, TX_CHAR_UUID, VERSION_CHAR_UUID

if TYPE_CHECKING:  # pragma: no cover — bleak is optional at runtime
    from bleak import BleakClient
    from bleak.backends.device import BLEDevice


TxCallback = Callable[[bytes], None]


@runtime_checkable
class BleTransport(Protocol):
    """Minimal GATT surface ``BleClient`` depends on."""

    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...
    async def read_version(self) -> int: ...
    async def write_rx(self, payload: bytes) -> None: ...
    def set_tx_callback(self, cb: TxCallback) -> None: ...


class BleakBleTransport:
    """Production transport. Connects via ``bleak_retry_connector`` for resilience."""

    def __init__(
        self,
        device: BLEDevice,
        *,
        name: str = "ratio-charger",
        connect_timeout: float = 20.0,
        max_attempts: int = 3,
    ) -> None:
        self._device = device
        self._name = name
        self._connect_timeout = connect_timeout
        self._max_attempts = max_attempts
        self._client: BleakClient | None = None
        self._tx_cb: TxCallback | None = None
        self._notify_active = False

    async def connect(self) -> None:
        if self._client is None or not self._client.is_connected:
            from bleak_retry_connector import (
                BleakClientWithServiceCache,
                establish_connection,
            )

            self._client = await establish_connection(
                BleakClientWithServiceCache,
                self._device,
                self._name,
                max_attempts=self._max_attempts,
                use_services_cache=True,
            )
        if not self._notify_active:
            assert self._client is not None
            await self._client.start_notify(TX_CHAR_UUID, self._on_notify)
            self._notify_active = True

    async def disconnect(self) -> None:
        if self._notify_active and self._client is not None:
            try:
                await self._client.stop_notify(TX_CHAR_UUID)
            except Exception:  # noqa: BLE001
                # already torn down — fall through to disconnect
                pass
            self._notify_active = False
        if self._client is not None and self._client.is_connected:
            await self._client.disconnect()

    async def read_version(self) -> int:
        assert self._client is not None
        raw = await self._client.read_gatt_char(VERSION_CHAR_UUID)
        data = bytes(raw)
        if not data:
            raise ValueError("Version characteristic read returned empty payload")
        return data[0]

    async def write_rx(self, payload: bytes) -> None:
        assert self._client is not None
        await self._client.write_gatt_char(RX_CHAR_UUID, payload, response=False)

    def set_tx_callback(self, cb: TxCallback) -> None:
        self._tx_cb = cb

    def _on_notify(self, _sender: object, data: bytearray) -> None:
        cb = self._tx_cb
        if cb is not None:
            cb(bytes(data))


__all__ = ["BleTransport", "BleakBleTransport", "TxCallback"]
