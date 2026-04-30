"""AWS Cognito SRP-6a implementation.

Implements the Cognito flavour of SRP-6a as required by the
``USER_SRP_AUTH`` and ``DEVICE_SRP_AUTH`` flows of Amazon Cognito User
Pools. References:

- RFC 5054 / RFC 2945 (SRP-6a)
- The (N, g) constant used by Cognito (3072-bit MODP, ``g = 2``),
  taken verbatim from the AWS SDKs (amplify-js, aws-sdk-android).
- AWS amplify-js / aws-sdk-android source for the wire-format quirks
  (unpadded ``SRP_A``, ``Caldera Derived Key`` HKDF info string, the
  ``EEE MMM d HH:mm:ss z yyyy`` Locale.US timestamp).

This module is a pure-Python implementation; it relies only on the
standard library (``hashlib``, ``hmac``, ``secrets``, ``os``, ``base64``,
``time``).
"""
from __future__ import annotations

import base64
import hmac
import os
import secrets
import time
from hashlib import sha256
from typing import Tuple

# Cognito-defined 3072-bit MODP prime, generator g = 2.
_N_HEX = (
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

N: int = int(_N_HEX, 16)
g: int = 2
N_LEN: int = 384  # bytes (3072 bits)


def int_to_padded_bytes(x: int, length: int = N_LEN) -> bytes:
    """Big-endian, left-zero-padded byte representation of ``x``."""
    return x.to_bytes(length, "big")


def bytes_to_int(b: bytes) -> int:
    """Parse big-endian unsigned integer from bytes."""
    return int.from_bytes(b, "big")


def _PAD(x: int) -> bytes:
    return int_to_padded_bytes(x, N_LEN)


def _H(data: bytes) -> bytes:
    return sha256(data).digest()


# Module-level constant: k = H(PAD(N) || PAD(g))
N_BYTES: bytes = _PAD(N)
k: int = bytes_to_int(_H(N_BYTES + _PAD(g)))


def generate_a() -> Tuple[int, int]:
    """Generate a fresh SRP private/public client value pair ``(a, A)``.

    ``a`` is a random 256-bit integer reduced mod N (the reduction is a
    no-op since N is 2048-bit, but kept for clarity).
    ``A = g^a mod N``.
    """
    a = secrets.randbits(256) % N
    A = pow(g, a, N)
    return a, A


def compute_u(A: int, B: int) -> int:
    """u = H(PAD(A) || PAD(B)) interpreted as a big-endian integer."""
    return bytes_to_int(_H(_PAD(A) + _PAD(B)))


def compute_x(salt: int, pool_name: str, user_id_for_srp: str, password: str) -> int:
    """User-pool x value.

    inner = H(pool_name || ':' || user_id_for_srp || ':' || password)
    x     = H(PAD(salt) || inner)
    """
    inner = _H(f"{pool_name}:{user_id_for_srp}:{password}".encode())
    return bytes_to_int(_H(_PAD(salt) + inner))


def compute_x_device(device_group_key: str, device_key: str, password: str, salt: int) -> int:
    """Device-SRP x value.

    inner = H(device_group_key || device_key || ':' || password)
    x     = H(PAD(salt) || inner)
    """
    inner = _H(f"{device_group_key}{device_key}:{password}".encode())
    return bytes_to_int(_H(_PAD(salt) + inner))


def compute_S(B: int, k_: int, g_: int, N_: int, x: int, a: int, u: int) -> int:
    """S = (B - k * g^x)^(a + u*x) mod N. Negative pre-mod handled."""
    base = (B - k_ * pow(g_, x, N_)) % N_
    if base < 0:  # defensive; Python % already returns non-negative for positive N
        base += N_
    return pow(base, a + u * x, N_)


def hkdf_derive(u: int, S: int) -> bytes:
    """HKDF-SHA256 with Cognito's ``Caldera Derived Key`` info string.

    salt = PAD(u), IKM = PAD(S), L = 16, info = b"Caldera Derived Key".
    Only T(1) of the expand step is required (16 <= 32).
    """
    salt = _PAD(u)
    ikm = _PAD(S)
    prk = hmac.new(salt, ikm, sha256).digest()
    info = b"Caldera Derived Key"
    t1 = hmac.new(prk, info + b"\x01", sha256).digest()
    return t1[:16]


def format_timestamp(t: time.struct_time | None = None) -> str:
    """Java ``EEE MMM d HH:mm:ss z yyyy`` Locale.US, UTC, *unpadded* day.

    Example: ``Thu Apr 30 17:32:00 UTC 2026`` (no leading zero on day).
    """
    if t is None:
        t = time.gmtime()
    return time.strftime("%a %b ", t) + str(t.tm_mday) + time.strftime(" %H:%M:%S UTC %Y", t)


def compute_signature(
    hkdf_key: bytes,
    pool_name: str,
    user_id_for_srp: str,
    secret_block_b64: str,
    timestamp: str,
) -> str:
    """HMAC-SHA256 over ``pool_name || user_id || secret_block || ts``.

    ``secret_block_b64`` is base64-decoded first.
    Returns the base64 signature.
    """
    secret_block = base64.b64decode(secret_block_b64)
    msg = (
        pool_name.encode()
        + user_id_for_srp.encode()
        + secret_block
        + timestamp.encode()
    )
    sig = hmac.new(hkdf_key, msg, sha256).digest()
    return base64.b64encode(sig).decode()


class UserSrp:
    """User-pool SRP helper.

    Usage::

        srp = UserSrp()
        a_hex = srp.start()  # send as SRP_A
        sig, ts = srp.process_challenge(B_hex, salt_hex, secret_block_b64,
                                        user_id_for_srp, pool_name, password)
    """

    def __init__(self) -> None:
        self._a: int | None = None
        self._A: int | None = None

    def start(self) -> str:
        """Initialise (a, A) and return ``A`` as unpadded lowercase hex."""
        self._a, self._A = generate_a()
        return format(self._A, "x")

    def process_challenge(
        self,
        B_hex: str,
        salt_hex: str,
        secret_block_b64: str,
        user_id_for_srp: str,
        pool_name: str,
        password: str,
    ) -> Tuple[str, str]:
        """Process Cognito's PASSWORD_VERIFIER challenge.

        Returns ``(signature_b64, timestamp)``.
        """
        if self._a is None or self._A is None:
            raise RuntimeError("UserSrp.start() must be called first")
        B = int(B_hex, 16)
        salt = int(salt_hex, 16)
        if B % N == 0:
            raise ValueError("Invalid SRP_B from server (B mod N == 0)")
        u = compute_u(self._A, B)
        if u == 0:
            raise ValueError("Invalid u (must be non-zero)")
        x = compute_x(salt, pool_name, user_id_for_srp, password)
        S = compute_S(B, k, g, N, x, self._a, u)
        hkdf_key = hkdf_derive(u, S)
        ts = format_timestamp()
        sig = compute_signature(
            hkdf_key, pool_name, user_id_for_srp, secret_block_b64, ts
        )
        return sig, ts


class DeviceSrp:
    """Device-SRP helper.

    Same algorithm as :class:`UserSrp` but the ``x`` derivation uses
    ``device_group_key + device_key + ':' + device_password`` instead of
    ``pool_name + ':' + user_id + ':' + password``.
    The HMAC signature message uses ``device_group_key || device_key``
    in place of ``pool_name || user_id``.
    """

    def __init__(self, device_group_key: str, device_key: str, device_password: str) -> None:
        self._device_group_key = device_group_key
        self._device_key = device_key
        self._device_password = device_password
        self._a: int | None = None
        self._A: int | None = None

    def start(self) -> str:
        self._a, self._A = generate_a()
        return format(self._A, "x")

    def process_challenge(
        self,
        B_hex: str,
        salt_hex: str,
        secret_block_b64: str,
    ) -> Tuple[str, str]:
        if self._a is None or self._A is None:
            raise RuntimeError("DeviceSrp.start() must be called first")
        B = int(B_hex, 16)
        salt = int(salt_hex, 16)
        if B % N == 0:
            raise ValueError("Invalid SRP_B from server (B mod N == 0)")
        u = compute_u(self._A, B)
        if u == 0:
            raise ValueError("Invalid u (must be non-zero)")
        x = compute_x_device(
            self._device_group_key, self._device_key, self._device_password, salt
        )
        S = compute_S(B, k, g, N, x, self._a, u)
        hkdf_key = hkdf_derive(u, S)
        ts = format_timestamp()
        secret_block = base64.b64decode(secret_block_b64)
        msg = (
            self._device_group_key.encode()
            + self._device_key.encode()
            + secret_block
            + ts.encode()
        )
        sig = base64.b64encode(hmac.new(hkdf_key, msg, sha256).digest()).decode()
        return sig, ts


def generate_device_verifier(device_group_key: str, device_key: str) -> dict:
    """Create a fresh device password / salt / verifier triple.

    Matches the Amplify JS algorithm:

    - password = base64(40 random bytes)
    - salt     = 16 random bytes
    - x        = H(PAD(salt_int) || H(group_key || device_key || ':' || password))
    - verifier = g^x mod N

    Returns ``{'password': str, 'salt_b64': str, 'verifier_b64': str}``
    where ``salt_b64`` is base64 of the raw 16-byte salt and
    ``verifier_b64`` is base64 of the *padded* (256-byte) verifier.
    """
    password = base64.standard_b64encode(os.urandom(40)).decode()
    salt = os.urandom(16)
    salt_int = bytes_to_int(salt)
    inner = _H(f"{device_group_key}{device_key}:{password}".encode())
    x = bytes_to_int(_H(_PAD(salt_int) + inner))
    verifier = pow(g, x, N)
    return {
        "password": password,
        "salt_b64": base64.b64encode(salt).decode(),
        "verifier_b64": base64.b64encode(_PAD(verifier)).decode(),
    }


__all__ = [
    "N",
    "g",
    "N_LEN",
    "N_BYTES",
    "k",
    "int_to_padded_bytes",
    "bytes_to_int",
    "generate_a",
    "compute_u",
    "compute_x",
    "compute_x_device",
    "compute_S",
    "hkdf_derive",
    "format_timestamp",
    "compute_signature",
    "UserSrp",
    "DeviceSrp",
    "generate_device_verifier",
]
