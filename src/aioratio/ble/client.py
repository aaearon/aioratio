"""``BleClient`` — public BLE entry point.

Lifecycle:
    1. ``connect()``: open the underlying ``BleTransport`` (which subscribes to
       TX notifications) and read the Version characteristic. The byte value is
       the IPC protocol version we'll gate commands against.
    2. command methods talk to the charger via ``write_rx`` + the TX callback;
       each request gets its own transaction ID and waits on a future in the
       :class:`TransactionRegistry`.
    3. ``disconnect()``: close the transport. No internal reconnect loop —
       the HA caller wraps this via ``bleak-retry-connector``.

Construct with a ``bleak.backends.device.BLEDevice`` so HA's BT-proxy routing
works; ``from_address`` is the convenience constructor for scripts.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from ..exceptions import (
    RatioBleConnectionError,
    RatioBleNotBondedError,
    RatioBleProtocolError,
)
from .codec import decode_responses, encode_request
from .models import (
    BackendStatusResponse,
    ChargeControl,
    ChargeControlResponse,
    ChargerSensorValuesResponse,
    ChargerStatusResponse,
    NetworkStatusResponse,
    OcppStatusResponse,
    ProductInformationResponse,
    SolarSettingsResponse,
    SolarSettingsUpdate,
    TimeSettingsResponse,
    TimeSettingsUpdate,
    UserSettingsResponse,
    UserSettingsUpdate,
    WifiAccessPoint,
    WifiConnectResponse,
    WifiScanResponse,
    b64_encode_text,
)
from .protocol import require_version
from .transactions import TransactionRegistry, new_transaction_id
from .transport import BleakBleTransport, BleTransport, _looks_like_bond_required

if TYPE_CHECKING:  # pragma: no cover
    from bleak.backends.device import BLEDevice


DisconnectedCallback = Callable[[], None]


class BleClient:
    """Inspiro IPC client for a single Ratio EV charger.

    Construct with a ``BLEDevice`` (so HA's BT-proxy routing works) or use
    :meth:`from_address` for quick scripts.
    """

    def __init__(
        self,
        device: BLEDevice | None = None,
        *,
        transport: BleTransport | None = None,
        disconnected_callback: DisconnectedCallback | None = None,
        command_timeout: float = 15.0,
        connect_timeout: float = 20.0,
    ) -> None:
        if (device is None) == (transport is None):
            raise TypeError("BleClient requires exactly one of 'device' or 'transport'")
        if transport is not None:
            self._transport: BleTransport = transport
        else:
            assert device is not None
            self._transport = BleakBleTransport(device, connect_timeout=connect_timeout)
        self._disconnected_cb = disconnected_callback
        self._command_timeout = command_timeout
        self._registry = TransactionRegistry()
        self._rx_buffer = bytearray()
        self._protocol_version: int | None = None
        self._connected = False
        self._send_lock = asyncio.Lock()

    # ------------------------------------------------------------------ ctor

    @classmethod
    def from_service_info(
        cls,
        service_info: Any,
        *,
        disconnected_callback: DisconnectedCallback | None = None,
        command_timeout: float = 15.0,
        connect_timeout: float = 20.0,
    ) -> BleClient:
        """Construct from anything carrying a ``BLEDevice`` on ``.device``.

        Matches the shape of Home Assistant's ``BluetoothServiceInfoBleak``
        (``home_assistant_bluetooth.BluetoothServiceInfoBleak``) so a HA
        ``async_step_bluetooth`` handler can do
        ``BleClient.from_service_info(discovery_info)`` without aioratio
        depending on the HA-only type.
        """
        return cls(
            device=service_info.device,
            disconnected_callback=disconnected_callback,
            command_timeout=command_timeout,
            connect_timeout=connect_timeout,
        )

    @classmethod
    async def from_address(
        cls,
        address: str,
        *,
        adapter: str | None = None,
        connect_timeout: float = 20.0,
        command_timeout: float = 15.0,
    ) -> BleClient:
        """Convenience constructor — discover the device then wrap it."""
        from bleak import BleakScanner

        if adapter is not None:
            device = await BleakScanner.find_device_by_address(
                address, timeout=connect_timeout, adapter=adapter
            )
        else:
            device = await BleakScanner.find_device_by_address(
                address, timeout=connect_timeout
            )
        if device is None:
            raise RatioBleConnectionError(
                f"No advert seen for {address} within {connect_timeout:.0f}s"
            )
        return cls(
            device=device,
            command_timeout=command_timeout,
            connect_timeout=connect_timeout,
        )

    # -------------------------------------------------------------- lifecycle

    async def connect(self) -> None:
        if self._connected:
            return
        self._transport.set_tx_callback(self._on_tx)
        try:
            await self._transport.connect()
        except Exception as exc:
            if _looks_like_bond_required(exc):
                raise RatioBleNotBondedError(
                    f"charger requires a bonded link before GATT access: {exc}"
                ) from exc
            raise RatioBleConnectionError(f"BLE connect failed: {exc}") from exc
        try:
            self._protocol_version = await self._transport.read_version()
        except Exception as exc:
            try:
                await self._transport.disconnect()
            except Exception:
                pass
            if _looks_like_bond_required(exc):
                raise RatioBleNotBondedError(
                    f"charger requires a bonded link before GATT access: {exc}"
                ) from exc
            raise RatioBleConnectionError(f"BLE connect failed: {exc}") from exc
        self._connected = True

    async def disconnect(self) -> None:
        if not self._connected:
            return
        self._connected = False
        self._registry.fail_all(RatioBleConnectionError("client disconnected"))
        try:
            await self._transport.disconnect()
        finally:
            cb = self._disconnected_cb
            if cb is not None:
                try:
                    cb()
                except Exception:  # noqa: BLE001 — user callback
                    pass

    async def __aenter__(self) -> BleClient:
        await self.connect()
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        await self.disconnect()

    # ----------------------------------------------------------- properties

    @property
    def protocol_version(self) -> int | None:
        """Version byte read from the Version characteristic, or ``None`` until connected."""
        return self._protocol_version

    @property
    def is_connected(self) -> bool:
        return self._connected

    # ------------------------------------------------------------- public API

    async def get_product_information(self) -> ProductInformationResponse:
        body = await self._exchange("GetProductInformationRequest", {})
        return ProductInformationResponse.from_dict(body)

    async def get_charger_status(self) -> ChargerStatusResponse:
        body = await self._exchange("ChargerStatusRequest", {})
        return ChargerStatusResponse.from_dict(body)

    async def get_charger_sensor_values(self) -> ChargerSensorValuesResponse:
        body = await self._exchange("GetChargerSensorValuesRequest", {})
        return ChargerSensorValuesResponse.from_dict(body)

    async def charge_control(self, control: ChargeControl) -> ChargeControlResponse:
        body = await self._exchange("ChargeControlRequest", {"control": control.value})
        return ChargeControlResponse.from_dict(body)

    async def get_user_settings(self) -> UserSettingsResponse:
        body = await self._exchange("GetUserSettingsRequest", {})
        return UserSettingsResponse.from_dict(body)

    async def set_user_settings(self, update: UserSettingsUpdate) -> None:
        await self._exchange("SetUserSettingsRequest", update.to_dict())

    async def get_solar_settings(self) -> SolarSettingsResponse:
        body = await self._exchange("GetSolarSettingsRequest", {})
        return SolarSettingsResponse.from_dict(body)

    async def set_solar_settings(self, update: SolarSettingsUpdate) -> None:
        await self._exchange("SetSolarSettingsRequest", update.to_dict())

    async def get_time_settings(self) -> TimeSettingsResponse:
        body = await self._exchange("GetTimeSettingsRequest", {})
        return TimeSettingsResponse.from_dict(body)

    async def set_time_settings(self, update: TimeSettingsUpdate) -> None:
        await self._exchange("SetTimeSettingsRequest", update.to_dict())

    async def get_network_status(self) -> NetworkStatusResponse:
        body = await self._exchange("GetNetworkStatusRequest", {})
        return NetworkStatusResponse.from_dict(body)

    async def get_ocpp_status(self) -> OcppStatusResponse:
        body = await self._exchange("GetOcppStatusRequest", {})
        return OcppStatusResponse.from_dict(body)

    async def get_backend_status(self) -> BackendStatusResponse:
        body = await self._exchange("GetBackendStatusRequest", {})
        return BackendStatusResponse.from_dict(body)

    async def wifi_scan(self) -> list[WifiAccessPoint]:
        """Trigger a scan and pull every reported access point.

        ``WifiScanResponse.numberOfFoundNetworks`` is the count; we follow up
        with ``WifiAccessPointRequest(index=i)`` for each AP.
        """
        scan_body = await self._exchange("WifiScanRequest", {})
        scan = WifiScanResponse.from_dict(scan_body)
        results: list[WifiAccessPoint] = []
        for index in range(scan.number_of_found_networks):
            ap_body = await self._exchange("WifiAccessPointRequest", {"index": index})
            results.append(WifiAccessPoint.from_dict(ap_body))
        return results

    async def wifi_connect(self, ssid: str, password: str | None) -> WifiConnectResponse:
        """Connect the charger to a Wi-Fi network.

        SSID is base64-encoded on the wire — confirmed against v3.13.2 firmware
        on ``GetNetworkStatusResponse.wifi.configuredSsid``. Callers pass plain
        text; we encode here.

        **Password handling is PROVISIONAL.** The on-wire form of
        ``WifiConnectRequest.password`` has not been captured against real
        hardware. If the firmware expects base64 (matching ``ssid``), sending
        plain text here will silently fail to connect — the charger may simply
        reject the join without surfacing a parse error. When a non-``None``
        password is provided we emit a ``RuntimeWarning`` so the caller can
        decide whether to proceed. Open networks (``password=None``) are
        unaffected.
        """
        import warnings

        payload: dict[str, Any] = {"ssid": b64_encode_text(ssid)}
        if password is not None:
            warnings.warn(
                "WifiConnectRequest password wire format is unverified; the "
                "charger may silently reject this credential. Open this issue "
                "with a Wireshark/btsnoop capture if you can.",
                RuntimeWarning,
                stacklevel=2,
            )
            payload["password"] = password
        body = await self._exchange("WifiConnectRequest", payload)
        return WifiConnectResponse.from_dict(body)

    # --------------------------------------------------------------- internals

    async def _exchange(self, classname: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self._connected:
            raise RatioBleConnectionError("BleClient is not connected")
        assert self._protocol_version is not None
        require_version(classname, self._protocol_version)

        txn = new_transaction_id()
        body = {**payload, "transaction": txn}
        fut = self._registry.register(txn)
        frame = encode_request(classname, body)

        async with self._send_lock:
            try:
                await self._transport.write_rx(frame)
            except Exception as exc:
                self._registry.cancel(txn)
                raise RatioBleConnectionError(f"BLE write failed: {exc}") from exc

        try:
            _, response_body = await asyncio.wait_for(fut, timeout=self._command_timeout)
        except TimeoutError:
            self._registry.cancel(txn)
            raise RatioBleConnectionError(
                f"timeout waiting for {classname} response (txn={txn})"
            ) from None
        return response_body

    def _on_tx(self, data: bytes) -> None:
        self._rx_buffer.extend(data)
        try:
            for classname, body in decode_responses(self._rx_buffer):
                if not self._registry.resolve(classname, body):
                    # No pending transaction matches; drop.
                    pass
        except RatioBleProtocolError:
            # Frame-level decode failure — fail every pending request so
            # callers see a clear error rather than hanging.
            self._registry.fail_all(
                RatioBleProtocolError(
                    f"decode failed for TX buffer of {len(self._rx_buffer)} bytes"
                )
            )
            self._rx_buffer.clear()


__all__ = ["BleClient"]
