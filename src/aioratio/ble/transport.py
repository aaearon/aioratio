"""BLE transport abstraction.

``BleTransport`` is a thin protocol around the GATT operations the IPC client
needs. Production uses ``BleakBleTransport``, which delegates to
``bleak_retry_connector.establish_connection`` for resilient connects with
retry/backoff. Tests substitute a ``FakeBleTransport``.

The transport is intentionally minimal: connect/disconnect, version-byte read,
RX-characteristic write, and a single TX-notify callback hook. Everything else
(framing, transactions, protocol gating) lives one layer up in ``BleClient``.

Pair-and-retry: ESPHome ``bluetooth_proxy`` keeps its ``is_paired_`` flag
per-connection. After the first connection bonds (LTK persisted in proxy
NVS), each *subsequent* connection still issues GATT ops with
``ESP_GATT_AUTH_REQ_NONE`` and is rejected with
``status=15`` (insufficient encryption). The proxy only restarts encryption
from the stored LTK when ``bluetooth_device_pair`` arrives on the *live*
connection — which ``bleak.BleakClient.pair()`` translates to. So every GATT
op here is wrapped in a single pair-and-retry on bond-required, run on the
same ``BleakClient`` (and therefore the same proxy connection) that the read
is happening on.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Protocol, TypeVar, runtime_checkable

from .const import RX_CHAR_UUID, TX_CHAR_UUID, VERSION_CHAR_UUID

if TYPE_CHECKING:  # pragma: no cover — bleak is optional at runtime
    from bleak import BleakClient
    from bleak.backends.device import BLEDevice


TxCallback = Callable[[bytes], None]

T = TypeVar("T")


# Substrings that BlueZ / bleak / bleak_esphome surface when a peer rejects
# GATT access for lack of an SMP bond. Matched against ``str(exc).lower()``
# because the concrete exception class varies between bleak backends
# (BleakError, BleakDBusError, OSError, BleakGATTProtocolError ...).
_BOND_REQUIRED_MARKERS = (
    "insufficient authentication",
    "insufficient encryption",
    "insufficient encryption key size",
    "att error: 0x05",  # insufficient authentication
    "att error: 0x0f",  # insufficient encryption
    "att error: 0x0c",  # insufficient encryption key size
    "error=5 ",  # bleak_esphome wording (handle=N error=5 description=...)
    "error=15 ",
    "not paired",
)


def _looks_like_bond_required(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return any(marker in msg for marker in _BOND_REQUIRED_MARKERS)


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
            await self._with_pair_retry(
                lambda: self._client.start_notify(  # type: ignore[union-attr]
                    TX_CHAR_UUID, self._on_notify
                )
            )
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
        raw = await self._with_pair_retry(
            lambda: self._client.read_gatt_char(VERSION_CHAR_UUID)  # type: ignore[union-attr]
        )
        data = bytes(raw)
        if not data:
            raise ValueError("Version characteristic read returned empty payload")
        return data[0]

    async def write_rx(self, payload: bytes) -> None:
        assert self._client is not None
        await self._with_pair_retry(
            lambda: self._client.write_gatt_char(  # type: ignore[union-attr]
                RX_CHAR_UUID, payload, response=False
            )
        )

    async def _with_pair_retry(self, op: Callable[[], Awaitable[T]]) -> T:
        """Run ``op``; on bond-required, ``pair()`` once and retry exactly once.

        Pair MUST run on the same underlying ``BleakClient`` as ``op`` so that
        the ESPHome proxy's per-connection ``is_paired_`` flag flips to true
        before the retry. A separate ``BleakClient`` would pair successfully
        but not affect the connection that does the read.

        Errors from ``pair()`` itself (``NotImplementedError`` if the proxy
        lacks the PAIRING feature flag, ``BleakError`` if the charger rejects
        SMP) are propagated unchanged — caller decides how to surface them.
        """
        try:
            return await op()
        except Exception as exc:  # noqa: BLE001 — wide net, narrowed by marker check
            if not _looks_like_bond_required(exc):
                raise
        assert self._client is not None
        await self._client.pair()
        return await op()

    def set_tx_callback(self, cb: TxCallback) -> None:
        self._tx_cb = cb

    def _on_notify(self, _sender: object, data: bytearray) -> None:
        cb = self._tx_cb
        if cb is not None:
            cb(bytes(data))


__all__ = [
    "BleTransport",
    "BleakBleTransport",
    "TxCallback",
    "_looks_like_bond_required",
]
