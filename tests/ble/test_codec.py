"""Inspiro IPC framing codec."""

from __future__ import annotations

import pytest

from aioratio.ble.codec import decode_responses, encode_request
from aioratio.exceptions import RatioBleProtocolError


def test_encode_request_is_classname_json_null() -> None:
    raw = encode_request("ChargerStatusRequest", {"transaction": "abc"})
    assert raw.endswith(b"\x00")
    assert raw.startswith(b"ChargerStatusRequest")
    body = raw[len(b"ChargerStatusRequest") : -1]
    # No whitespace — Kotlinx default.
    assert b" " not in body
    assert body == b'{"transaction":"abc"}'


def test_encode_request_preserves_unicode() -> None:
    raw = encode_request("WifiConnectRequest", {"ssid": "Réseau", "password": "pässwörd"})
    assert "Réseau".encode() in raw
    assert "pässwörd".encode() in raw


def test_decode_single_frame() -> None:
    buf = bytearray(b'ChargerStatusResponse{"transaction":"abc","result":"success"}\x00')
    frames = list(decode_responses(buf))
    assert frames == [("ChargerStatusResponse", {"transaction": "abc", "result": "success"})]
    assert buf == bytearray()


def test_decode_concatenated_frames_in_one_packet() -> None:
    buf = bytearray(
        b'ChargerStatusResponse{"transaction":"abc","result":"success"}\x00'
        b'ChargeControlResponse{"transaction":"def","result":"Failed"}\x00'
    )
    frames = list(decode_responses(buf))
    assert frames == [
        ("ChargerStatusResponse", {"transaction": "abc", "result": "success"}),
        ("ChargeControlResponse", {"transaction": "def", "result": "Failed"}),
    ]
    assert buf == bytearray()


def test_decode_keeps_partial_tail_in_buffer() -> None:
    buf = bytearray(b'ChargerStatusResponse{"transaction":"abc"')
    frames = list(decode_responses(buf))
    assert frames == []
    # Tail preserved for the next notify chunk.
    assert buf == bytearray(b'ChargerStatusResponse{"transaction":"abc"')


def test_decode_skips_empty_frames_between_terminators() -> None:
    buf = bytearray(b"\x00\x00")
    assert list(decode_responses(buf)) == []
    assert buf == bytearray()


def test_decode_rejects_frame_with_no_json() -> None:
    buf = bytearray(b"JustAClassname\x00")
    with pytest.raises(RatioBleProtocolError):
        list(decode_responses(buf))


def test_decode_rejects_malformed_json() -> None:
    buf = bytearray(b"ChargerStatusResponse{not json}\x00")
    with pytest.raises(RatioBleProtocolError):
        list(decode_responses(buf))


def test_decode_rejects_non_object_json() -> None:
    buf = bytearray(b'ChargerStatusResponse"a string"\x00')
    with pytest.raises(RatioBleProtocolError):
        list(decode_responses(buf))
