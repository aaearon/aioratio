"""Inspiro IPC framing codec.

Wire format (confirmed against ``BluetoothManager.java`` write+notify paths
and BluetoothManager.java:603 null-byte check on receive):

    request:  <classname-utf8><json-utf8>\\x00
    response: <classname-utf8><json-utf8>\\x00 [...repeat]

The classname is everything before the first ``{`` in the frame; the JSON
body starts at that brace and ends at the trailing null. Notify packets may
carry multiple frames concatenated, and a single frame may straddle multiple
notify packets, so ``decode_responses`` consumes a caller-owned bytearray and
leaves trailing partial bytes in the buffer.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

from ..exceptions import RatioBleProtocolError


def encode_request(classname: str, payload: dict[str, Any]) -> bytes:
    """Encode a single IPC request: ``classname + JSON + 0x00``.

    JSON is serialized without whitespace to match Kotlinx Serialization's
    default output.
    """
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    return classname.encode("utf-8") + body.encode("utf-8") + b"\x00"


def _split_classname_body(frame: bytes) -> tuple[str, dict[str, Any]]:
    text = frame.decode("utf-8", errors="strict")
    brace = text.find("{")
    if brace < 0:
        raise RatioBleProtocolError(f"frame has no JSON body: {text!r}")
    classname = text[:brace]
    if not classname:
        raise RatioBleProtocolError("frame has empty classname prefix")
    try:
        body = json.loads(text[brace:])
    except json.JSONDecodeError as exc:
        raise RatioBleProtocolError(f"frame JSON decode failed: {exc}") from exc
    if not isinstance(body, dict):
        raise RatioBleProtocolError(f"frame JSON is not an object: {type(body).__name__}")
    return classname, body


def decode_responses(buffer: bytearray) -> Iterator[tuple[str, dict[str, Any]]]:
    """Yield ``(classname, body)`` for every complete frame in ``buffer``.

    Trailing partial-frame bytes (no null terminator yet) remain in ``buffer``
    for the next call.
    """
    while True:
        idx = buffer.find(b"\x00")
        if idx < 0:
            return
        frame = bytes(buffer[:idx])
        del buffer[: idx + 1]
        if frame:
            yield _split_classname_body(frame)


__all__ = ["encode_request", "decode_responses"]
