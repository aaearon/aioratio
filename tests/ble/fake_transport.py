"""In-memory ``BleTransport`` for unit-testing ``BleClient``.

The fake records every ``write_rx`` payload. Tests register response factories
keyed by request classname; whenever a matching request is written, the fake
schedules a reply via the registered TX callback.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from typing import Any

from aioratio.ble.codec import encode_request
from aioratio.ble.transport import DisconnectedCallback, TxCallback

ResponseFactory = Callable[[dict[str, Any]], tuple[str, dict[str, Any]]]


class FakeBleTransport:
    """Mirrors the ``BleTransport`` protocol with no actual BLE."""

    def __init__(self, *, protocol_version: int = 3) -> None:
        self.protocol_version = protocol_version
        self.connected = False
        self.disconnected_count = 0
        self.writes: list[bytes] = []
        self._tx_cb: TxCallback | None = None
        self._disconnected_cb: DisconnectedCallback | None = None
        self._responders: dict[str, ResponseFactory] = {}

    # ------ test helpers ------

    def register_response(self, classname: str, factory: ResponseFactory) -> None:
        """``factory(request_body)`` returns ``(response_classname, response_body)``."""
        self._responders[classname] = factory

    def register_static(
        self, request_classname: str, response_classname: str, body_template: dict[str, Any]
    ) -> None:
        """Convenience: echo the transaction id back into a static body template."""

        def factory(req: dict[str, Any]) -> tuple[str, dict[str, Any]]:
            body = dict(body_template)
            body.setdefault("transaction", req.get("transaction", ""))
            return response_classname, body

        self.register_response(request_classname, factory)

    # ------ BleTransport protocol ------

    async def connect(self) -> None:
        self.connected = True

    async def disconnect(self) -> None:
        self.connected = False
        self.disconnected_count += 1

    async def read_version(self) -> int:
        return self.protocol_version

    async def write_rx(self, payload: bytes) -> None:
        self.writes.append(payload)
        classname, body = _decode_request(payload)
        responder = self._responders.get(classname)
        if responder is None:
            return
        resp_classname, resp_body = responder(body)
        # Deliver via tx callback on the next event-loop tick so the producer
        # can register its future before the response lands.
        asyncio.get_running_loop().call_soon(self._deliver, resp_classname, resp_body)

    def set_tx_callback(self, cb: TxCallback) -> None:
        self._tx_cb = cb

    def set_disconnected_callback(self, cb: DisconnectedCallback | None) -> None:
        self._disconnected_cb = cb

    def fire_remote_disconnect(self) -> None:
        """Test helper: simulate the underlying link dropping unexpectedly."""
        self.connected = False
        cb = self._disconnected_cb
        if cb is not None:
            cb()

    # ------ internal ------

    def _deliver(self, classname: str, body: dict[str, Any]) -> None:
        cb = self._tx_cb
        if cb is None:
            return
        cb(encode_request(classname, body))


def _decode_request(payload: bytes) -> tuple[str, dict[str, Any]]:
    """Parse a single null-terminated frame back into ``(classname, body)``."""
    if not payload.endswith(b"\x00"):
        raise AssertionError("FakeBleTransport got a frame without 0x00 terminator")
    text = payload[:-1].decode("utf-8")
    brace = text.find("{")
    return text[:brace], json.loads(text[brace:])
