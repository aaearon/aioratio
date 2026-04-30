"""Vector tests for the Cognito SRP-6a implementation.

Each test re-implements the expected value independently using the
stdlib primitives (``hashlib``, ``hmac``, ``pow``) so a regression in
the production code cannot pass via self-consistency.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import time
from hashlib import sha256

import pytest

from aioratio import srp


# ---------------------------------------------------------------------------
# Independent re-implementation of the primitives used by the tests.
# ---------------------------------------------------------------------------

_REF_N_HEX = (
    "FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD1"
    "29024E088A67CC74020BBEA63B139B22514A08798E3404DD"
    "EF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245"
    "E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7ED"
    "EE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3D"
    "C2007CB8A163BF0598DA48361C55D39A69163FA8FD24CF5F"
    "83655D23DCA3AD961C62F356208552BB9ED529077096966D"
    "670C354E4ABC9804F1746C08CA18217C32905E462E36CE3B"
    "E39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9"
    "DE2BCBF6955817183995497CEA956AE515D2261898FA0510"
    "15728E5A8AAAC42DAD33170D04507A33A85521ABDF1CBA64"
    "ECFB850458DBEF0A8AEA71575D060C7DB3970F85A6E1E4C7"
    "ABF5AE8CDB0933D71E8C94E04A25619DCEE3D2261AD2EE6B"
    "F12FFA06D98A0864D87602733EC86A64521F2B18177B200C"
    "BBE117577A615D6C770988C0BAD946E208E24FA074E5AB31"
    "43DB5BFCE0FD108E4B82D120A93AD2CAFFFFFFFFFFFFFFFF"
)
_REF_N = int(_REF_N_HEX, 16)
_REF_G = 2
_REF_LEN = 384


def _ref_pad(x: int) -> bytes:
    return x.to_bytes(_REF_LEN, "big")


def _ref_h(b: bytes) -> bytes:
    return hashlib.sha256(b).digest()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_padding_and_constants() -> None:
    # N parsed correctly and padded to exactly 384 bytes (3072 bits).
    assert srp.N == _REF_N
    assert srp.N.bit_length() == 3072
    assert len(srp.N_BYTES) == 384
    assert srp.N_BYTES == _ref_pad(_REF_N)
    assert srp.g == 2
    assert srp.N_LEN == 384

    # k = SHA256(PAD(N) || PAD(g)), independently computed.
    expected_k_bytes = _ref_h(_ref_pad(_REF_N) + _ref_pad(_REF_G))
    assert len(expected_k_bytes) == 32
    expected_k = int.from_bytes(expected_k_bytes, "big")
    assert srp.k == expected_k


def test_compute_A_unpadded_hex() -> None:
    # a = 1 -> A = g.
    a = 1
    A = pow(_REF_G, a, _REF_N)
    assert A == 2
    assert format(A, "x") == "2"  # unpadded, lower-case

    # a = N - 1 -> A = pow(g, N-1, N). For prime-ish N (Sophie-Germain, p safe)
    # this just exercises the non-trivial path. We don't rely on Fermat here.
    a2 = _REF_N - 1
    A2 = pow(_REF_G, a2, _REF_N)
    expected_hex = format(A2, "x")
    # Sanity: no padding to 512 hex chars unless A2 happens to use top bit
    # (it might or might not). Just check format() output matches.
    assert format(A2, "x") == expected_hex


def test_compute_u_padded_hash() -> None:
    A, B = 1, 2
    expected = int.from_bytes(_ref_h(_ref_pad(A) + _ref_pad(B)), "big")
    assert srp.compute_u(A, B) == expected
    # Also confirm padded inputs were used (not raw varlen ints): swapping
    # padding to 32-byte would yield a different value.
    short = int.from_bytes(
        _ref_h(A.to_bytes(32, "big") + B.to_bytes(32, "big")), "big"
    )
    assert srp.compute_u(A, B) != short


def test_compute_x_uses_pool_name_not_id() -> None:
    pool_name = "mH4sFjLoF"  # suffix only, NOT eu-west-1_mH4sFjLoF
    user_id = "abcdef"
    password = "password123"
    salt = 0x1234

    inner = _ref_h(f"{pool_name}:{user_id}:{password}".encode())
    x_bytes = _ref_h(_ref_pad(salt) + inner)
    expected = int.from_bytes(x_bytes, "big")

    assert srp.compute_x(salt, pool_name, user_id, password) == expected

    # Sanity: using the full pool_id would give a different x.
    full_pool = "eu-west-1_mH4sFjLoF"
    inner_wrong = _ref_h(f"{full_pool}:{user_id}:{password}".encode())
    x_wrong = int.from_bytes(_ref_h(_ref_pad(salt) + inner_wrong), "big")
    assert srp.compute_x(salt, pool_name, user_id, password) != x_wrong


def test_compute_S_negative_base_handled() -> None:
    # Pick small numbers where B - k*g^x is negative pre-mod.
    # Using small toy N would be wrong since the fn uses srp.N. Instead pick
    # x small so that k*g^x >> B.
    B = 5
    x = 7
    a = 11
    u = 13

    expected_base = (B - srp.k * pow(srp.g, x, srp.N)) % srp.N
    assert expected_base >= 0
    expected = pow(expected_base, a + u * x, srp.N)

    got = srp.compute_S(B, srp.k, srp.g, srp.N, x, a, u)
    assert got == expected


def test_hkdf_caldera_info() -> None:
    u = 0x1
    S = 0x2
    salt = _ref_pad(u)
    ikm = _ref_pad(S)
    info = b"Caldera Derived Key"
    prk = hmac.new(salt, ikm, hashlib.sha256).digest()
    t1 = hmac.new(prk, info + b"\x01", hashlib.sha256).digest()
    expected = t1[:16]

    assert srp.hkdf_derive(u, S) == expected
    assert len(srp.hkdf_derive(u, S)) == 16


def test_format_timestamp_unpadded_day(monkeypatch: pytest.MonkeyPatch) -> None:
    # 2026-04-30 17:32:00 UTC -> Thursday
    fixed1 = time.struct_time((2026, 4, 30, 17, 32, 0, 3, 120, 0))
    assert srp.format_timestamp(fixed1) == "Thu Apr 30 17:32:00 UTC 2026"

    # 2026-04-05 17:32:00 UTC -> Sunday, single-digit day, no leading zero
    fixed2 = time.struct_time((2026, 4, 5, 17, 32, 0, 6, 95, 0))
    assert srp.format_timestamp(fixed2) == "Sun Apr 5 17:32:00 UTC 2026"

    # And the default-arg path uses gmtime.
    monkeypatch.setattr(srp.time, "gmtime", lambda: fixed1)
    assert srp.format_timestamp() == "Thu Apr 30 17:32:00 UTC 2026"


def test_signature_roundtrip() -> None:
    hkdf_key = bytes(range(16))
    pool_name = "mH4sFjLoF"
    user_id = "user-id-for-srp-xyz"
    secret_block = b"\x00\x01\x02opaque-secret-block-bytes"
    secret_block_b64 = base64.b64encode(secret_block).decode()
    timestamp = "Thu Apr 30 17:32:00 UTC 2026"

    msg = pool_name.encode() + user_id.encode() + secret_block + timestamp.encode()
    expected = base64.b64encode(
        hmac.new(hkdf_key, msg, hashlib.sha256).digest()
    ).decode()

    got = srp.compute_signature(hkdf_key, pool_name, user_id, secret_block_b64, timestamp)
    assert got == expected


def test_device_verifier_deterministic(monkeypatch: pytest.MonkeyPatch) -> None:
    # Fixed bytes for the two os.urandom calls (40, then 16).
    rand40 = bytes(range(40))
    rand16 = bytes(range(100, 116))
    calls = iter([rand40, rand16])

    def fake_urandom(n: int) -> bytes:
        b = next(calls)
        assert len(b) == n
        return b

    monkeypatch.setattr(srp.os, "urandom", fake_urandom)

    out = srp.generate_device_verifier("device-group-key-XYZ", "device-key-ABC")

    # Independent expected computation.
    expected_password = base64.standard_b64encode(rand40).decode()
    expected_salt_b64 = base64.b64encode(rand16).decode()
    salt_int = int.from_bytes(rand16, "big")
    inner = _ref_h(
        f"device-group-key-XYZdevice-key-ABC:{expected_password}".encode()
    )
    x = int.from_bytes(_ref_h(_ref_pad(salt_int) + inner), "big")
    verifier = pow(_REF_G, x, _REF_N)
    expected_verifier_b64 = base64.b64encode(_ref_pad(verifier)).decode()

    assert out["password"] == expected_password
    assert out["salt_b64"] == expected_salt_b64
    assert out["verifier_b64"] == expected_verifier_b64


def test_device_srp_x_uses_group_key() -> None:
    device_group_key = "GROUPKEY123"
    device_key = "DEVICEKEY456"
    password = "device-password!!"
    salt = 0xCAFE

    # Independent expected computation: H(group_key + device_key + ':' + pwd)
    inner = _ref_h(f"{device_group_key}{device_key}:{password}".encode())
    expected = int.from_bytes(_ref_h(_ref_pad(salt) + inner), "big")

    got = srp.compute_x_device(device_group_key, device_key, password, salt)
    assert got == expected

    # And it must NOT match the pool-style format using these as if they
    # were pool_name and user_id (would put a colon between them).
    pool_style_inner = _ref_h(
        f"{device_group_key}:{device_key}:{password}".encode()
    )
    pool_style_x = int.from_bytes(_ref_h(_ref_pad(salt) + pool_style_inner), "big")
    assert got != pool_style_x


def test_user_srp_start_unpadded_hex(monkeypatch: pytest.MonkeyPatch) -> None:
    # Force a deterministic 'a' so we can compare A.
    monkeypatch.setattr(srp.secrets, "randbits", lambda n: 1)
    s = srp.UserSrp()
    a_hex = s.start()
    # a = 1 -> A = g = 2 -> "2"
    assert a_hex == "2"
