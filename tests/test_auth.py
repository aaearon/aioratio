"""Tests for CognitoSrpAuth."""
from __future__ import annotations

import asyncio
import time
from typing import Any

import pytest

from aioratio import auth as auth_mod
from aioratio.auth import CognitoSrpAuth, TokenBundle
from aioratio.exceptions import RatioAuthError
from aioratio.token_store import TokenStore


class FakeStore(TokenStore):
    """In-memory token store sufficient for tests."""

    def __init__(self, bundle: TokenBundle | None = None) -> None:
        self.bundle: TokenBundle | None = bundle
        self.saves: list[TokenBundle] = []

    async def load(self) -> Any:  # type: ignore[override]
        return self.bundle

    async def save(self, tokens: Any) -> None:  # type: ignore[override]
        self.bundle = tokens
        self.saves.append(tokens)

    async def clear(self) -> None:
        self.bundle = None


class FakeCognito:
    """Records POST bodies and replays canned responses by target."""

    def __init__(self) -> None:
        # mapping target -> list of responses (consumed in order)
        self.queues: dict[str, list[dict[str, Any]]] = {}
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def queue(self, target: str, response: dict[str, Any]) -> None:
        self.queues.setdefault(target, []).append(response)

    async def __call__(self, target: str, body: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((target, body))
        q = self.queues.get(target)
        if not q:
            raise AssertionError(f"unexpected Cognito call: {target}")
        resp = q.pop(0)
        if isinstance(resp, Exception):
            raise resp
        return resp

    def respond_calls(self) -> list[dict[str, Any]]:
        return [b for t, b in self.calls if t == "RespondToAuthChallenge"]

    def initiate_calls(self) -> list[dict[str, Any]]:
        return [b for t, b in self.calls if t == "InitiateAuth"]


def _auth_result(
    *,
    access: str = "ACCESS",
    refresh: str | None = "REFRESH",
    id_token: str = "ID",
    expires_in: int = 3600,
    new_device: tuple[str, str] | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "AccessToken": access,
        "IdToken": id_token,
        "ExpiresIn": expires_in,
        "TokenType": "Bearer",
    }
    if refresh is not None:
        out["RefreshToken"] = refresh
    if new_device is not None:
        out["NewDeviceMetadata"] = {
            "DeviceKey": new_device[0],
            "DeviceGroupKey": new_device[1],
        }
    return out


def make_auth(store: FakeStore, fake: FakeCognito | None = None) -> CognitoSrpAuth:
    obj = CognitoSrpAuth(
        email="user@example.com",
        password="hunter2",
        token_store=store,
        session=None,  # type: ignore[arg-type]
    )
    if fake is not None:
        obj._cognito_call = fake  # type: ignore[assignment]
    return obj


# ---------------------------------------------------------------------------


async def test_first_login_full_flow() -> None:
    fake = FakeCognito()
    fake.queue(
        "InitiateAuth",
        {
            "ChallengeName": "PASSWORD_VERIFIER",
            "ChallengeParameters": {
                "USERNAME": "internal-user-id",
                "USER_ID_FOR_SRP": "internal-user-id",
                "SRP_B": "ab" * 192,  # 384 bytes hex
                "SALT": "deadbeef",
                "SECRET_BLOCK": "c2VjcmV0YmxvY2s=",  # base64 ok
            },
        },
    )
    fake.queue(
        "RespondToAuthChallenge",
        {
            "AuthenticationResult": _auth_result(
                new_device=("dev-key-123", "eu-west-1_pool"),
            )
        },
    )
    fake.queue("ConfirmDevice", {"UserConfirmationNecessary": False})
    fake.queue("UpdateDeviceStatus", {})

    store = FakeStore()
    auth = make_auth(store, fake)
    bundle = await auth.login()

    assert bundle.access_token == "ACCESS"
    assert bundle.refresh_token == "REFRESH"
    assert bundle.device_key == "dev-key-123"
    assert bundle.device_group_key == "eu-west-1_pool"
    assert bundle.device_password  # set
    assert store.bundle is bundle

    confirm = next(b for t, b in fake.calls if t == "ConfirmDevice")
    assert confirm["DeviceSecretVerifierConfig"]["PasswordVerifier"]
    assert confirm["DeviceSecretVerifierConfig"]["Salt"]
    update = next(b for t, b in fake.calls if t == "UpdateDeviceStatus")
    assert update["DeviceRememberedStatus"] == "remembered"


async def test_second_login_device_srp_path() -> None:
    fake = FakeCognito()
    # 1: InitiateAuth -> PASSWORD_VERIFIER
    fake.queue(
        "InitiateAuth",
        {
            "ChallengeName": "PASSWORD_VERIFIER",
            "ChallengeParameters": {
                "USERNAME": "internal-user",
                "USER_ID_FOR_SRP": "internal-user",
                "SRP_B": "cd" * 192,
                "SALT": "feedface",
                "SECRET_BLOCK": "c2I=",
            },
        },
    )
    # 2: RespondToAuthChallenge PASSWORD_VERIFIER -> DEVICE_SRP_AUTH
    fake.queue(
        "RespondToAuthChallenge",
        {
            "ChallengeName": "DEVICE_SRP_AUTH",
            "ChallengeParameters": {"USERNAME": "internal-user"},
        },
    )
    # 3: RespondToAuthChallenge DEVICE_SRP_AUTH -> DEVICE_PASSWORD_VERIFIER
    fake.queue(
        "RespondToAuthChallenge",
        {
            "ChallengeName": "DEVICE_PASSWORD_VERIFIER",
            "ChallengeParameters": {
                "USERNAME": "internal-user",
                "SRP_B": "ef" * 192,
                "SALT": "cafebabe",
                "SECRET_BLOCK": "c2I=",
            },
        },
    )
    # 4: RespondToAuthChallenge DEVICE_PASSWORD_VERIFIER -> tokens
    fake.queue(
        "RespondToAuthChallenge",
        {"AuthenticationResult": _auth_result(refresh=None)},
    )

    existing = TokenBundle(
        access_token="OLD",
        id_token="OLDID",
        refresh_token="OLDREFRESH",
        expires_at=time.time() - 100,
        token_type="Bearer",
        device_key="DK",
        device_group_key="DGK",
        device_password="DPW",
    )
    store = FakeStore(existing)
    auth = make_auth(store, fake)

    bundle = await auth.login()

    # device_* preserved
    assert bundle.device_key == "DK"
    assert bundle.device_group_key == "DGK"
    assert bundle.device_password == "DPW"
    # refresh fell back to existing
    assert bundle.refresh_token == "OLDREFRESH"

    responds = fake.respond_calls()
    assert len(responds) == 3
    # Initiate had DEVICE_KEY
    init = fake.initiate_calls()[0]
    assert init["AuthParameters"]["DEVICE_KEY"] == "DK"
    # PASSWORD_VERIFIER response includes DEVICE_KEY
    assert responds[0]["ChallengeName"] == "PASSWORD_VERIFIER"
    assert responds[0]["ChallengeResponses"]["DEVICE_KEY"] == "DK"
    # DEVICE_SRP_AUTH response has SRP_A and DEVICE_KEY
    assert responds[1]["ChallengeName"] == "DEVICE_SRP_AUTH"
    assert "SRP_A" in responds[1]["ChallengeResponses"]
    assert responds[1]["ChallengeResponses"]["DEVICE_KEY"] == "DK"
    # DEVICE_PASSWORD_VERIFIER response has signature
    assert responds[2]["ChallengeName"] == "DEVICE_PASSWORD_VERIFIER"
    assert responds[2]["ChallengeResponses"]["PASSWORD_CLAIM_SIGNATURE"]


async def test_refresh_token_rotation_persisted() -> None:
    fake = FakeCognito()
    fake.queue(
        "InitiateAuth",
        {"AuthenticationResult": _auth_result(refresh="NEWREFRESH", access="A2")},
    )
    bundle = TokenBundle(
        access_token="OLD",
        id_token="ID",
        refresh_token="OLDREFRESH",
        expires_at=time.time() + 1000,
        token_type="Bearer",
        device_key="DK",
        device_group_key="DGK",
        device_password="DPW",
    )
    store = FakeStore(bundle)
    auth = make_auth(store, fake)

    new = await auth.refresh(bundle)
    assert new.refresh_token == "NEWREFRESH"
    assert new.access_token == "A2"
    assert store.bundle.refresh_token == "NEWREFRESH"
    init = fake.initiate_calls()[0]
    assert init["AuthFlow"] == "REFRESH_TOKEN_AUTH"
    assert init["AuthParameters"]["DEVICE_KEY"] == "DK"
    assert init["AuthParameters"]["REFRESH_TOKEN"] == "OLDREFRESH"


async def test_refresh_token_no_rotation_keeps_old() -> None:
    fake = FakeCognito()
    fake.queue(
        "InitiateAuth",
        {"AuthenticationResult": _auth_result(refresh=None, access="A3")},
    )
    bundle = TokenBundle(
        access_token="OLD",
        id_token="ID",
        refresh_token="KEEPME",
        expires_at=time.time() + 1000,
        token_type="Bearer",
    )
    store = FakeStore(bundle)
    auth = make_auth(store, fake)
    new = await auth.refresh(bundle)
    assert new.refresh_token == "KEEPME"


async def test_refresh_failure_falls_back_to_login() -> None:
    fake = FakeCognito()
    # Refresh fails
    fake.queue(
        "InitiateAuth",
        RatioAuthError("NotAuthorizedException: Refresh Token has expired"),
    )
    # Then full login proceeds
    fake.queue(
        "InitiateAuth",
        {
            "ChallengeName": "PASSWORD_VERIFIER",
            "ChallengeParameters": {
                "USERNAME": "u",
                "USER_ID_FOR_SRP": "u",
                "SRP_B": "12" * 192,
                "SALT": "ab",
                "SECRET_BLOCK": "c2I=",
            },
        },
    )
    fake.queue(
        "RespondToAuthChallenge",
        {"AuthenticationResult": _auth_result(access="POST_LOGIN")},
    )

    bundle = TokenBundle(
        access_token="OLD",
        id_token="ID",
        refresh_token="EXPIRED",
        expires_at=time.time() - 100,
        token_type="Bearer",
    )
    store = FakeStore(bundle)
    auth = make_auth(store, fake)

    token = await auth.get_access_token()
    assert token == "POST_LOGIN"


async def test_unsupported_challenge_raises_clean() -> None:
    fake = FakeCognito()
    fake.queue(
        "InitiateAuth",
        {"ChallengeName": "SMS_MFA", "ChallengeParameters": {}},
    )
    store = FakeStore()
    auth = make_auth(store, fake)
    with pytest.raises(RatioAuthError) as ei:
        await auth.login()
    assert "unsupported challenge" in str(ei.value)
    assert "SMS_MFA" in str(ei.value)


async def test_concurrent_refresh_serialised() -> None:
    fake = FakeCognito()
    # Only one InitiateAuth response queued; if more than one is made, we'll fail.
    fake.queue(
        "InitiateAuth",
        {"AuthenticationResult": _auth_result(refresh="NEW", access="ONLYONE")},
    )
    bundle = TokenBundle(
        access_token="OLD",
        id_token="ID",
        refresh_token="R",
        expires_at=time.time() - 100,
        token_type="Bearer",
        device_key="DK",
        device_group_key="DGK",
        device_password="DPW",
    )
    store = FakeStore(bundle)
    auth = make_auth(store, fake)

    results = await asyncio.gather(*[auth.get_access_token() for _ in range(5)])
    assert results == ["ONLYONE"] * 5
    initiate_calls = [t for t, _ in fake.calls if t == "InitiateAuth"]
    assert len(initiate_calls) == 1


async def test_get_access_token_uses_cached_when_fresh() -> None:
    fake = FakeCognito()  # no responses queued -> any call would fail
    bundle = TokenBundle(
        access_token="FRESH",
        id_token="ID",
        refresh_token="R",
        expires_at=time.time() + 1000,
        token_type="Bearer",
    )
    store = FakeStore(bundle)
    auth = make_auth(store, fake)
    token = await auth.get_access_token()
    assert token == "FRESH"
    assert fake.calls == []


async def test_cognito_error_mapping_NotAuthorized_to_RatioAuthError() -> None:
    """The real _cognito_call must map a 400 NotAuthorizedException to RatioAuthError."""
    auth = CognitoSrpAuth(
        email="u",
        password="p",
        token_store=FakeStore(),
        session=None,  # type: ignore[arg-type]
    )

    class FakeResp:
        status = 400

        async def text(self) -> str:
            return (
                '{"__type":"NotAuthorizedException",'
                '"message":"Incorrect username or password."}'
            )

        async def __aenter__(self) -> "FakeResp":
            return self

        async def __aexit__(self, *exc: Any) -> None:
            return None

    class FakeSession:
        def post(self, url: str, headers: Any = None, json: Any = None, **kwargs: Any) -> FakeResp:
            return FakeResp()

    auth._session = FakeSession()  # type: ignore[assignment]
    with pytest.raises(RatioAuthError) as ei:
        await auth._cognito_call("InitiateAuth", {})
    assert "NotAuthorizedException" in str(ei.value)


async def test_signature_inputs_use_user_id_for_srp_not_email(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    real_compute_signature = auth_mod._srp.compute_signature

    def spy(
        hkdf_key: bytes,
        pool_name: str,
        user_id_for_srp: str,
        secret_block_b64: str,
        timestamp: str,
    ) -> str:
        captured["pool_name"] = pool_name
        captured["user_id_for_srp"] = user_id_for_srp
        return real_compute_signature(
            hkdf_key, pool_name, user_id_for_srp, secret_block_b64, timestamp
        )

    monkeypatch.setattr(auth_mod._srp, "compute_signature", spy)

    fake = FakeCognito()
    fake.queue(
        "InitiateAuth",
        {
            "ChallengeName": "PASSWORD_VERIFIER",
            "ChallengeParameters": {
                "USERNAME": "internal-id",
                "USER_ID_FOR_SRP": "DIFFERENT-FROM-EMAIL",
                "SRP_B": "13" * 192,
                "SALT": "ab",
                "SECRET_BLOCK": "c2I=",
            },
        },
    )
    fake.queue(
        "RespondToAuthChallenge",
        {"AuthenticationResult": _auth_result()},
    )
    store = FakeStore()
    auth = make_auth(store, fake)
    await auth.login()

    assert captured["user_id_for_srp"] == "DIFFERENT-FROM-EMAIL"
    assert captured["user_id_for_srp"] != "user@example.com"


async def test_timeout_propagation() -> None:
    store = FakeStore()
    auth = CognitoSrpAuth(
        email="u@test.com",
        password="pw",
        token_store=store,
        session=None,  # type: ignore[arg-type]
        timeout=15.0,
    )
    assert auth._timeout == 15.0


async def test_timeout_default() -> None:
    store = FakeStore()
    auth = CognitoSrpAuth(
        email="u@test.com",
        password="pw",
        token_store=store,
        session=None,  # type: ignore[arg-type]
    )
    assert auth._timeout == 30.0


async def test_invalidate_access_token() -> None:
    bundle = TokenBundle(
        access_token="TOK",
        id_token="ID",
        refresh_token="REF",
        expires_at=time.time() + 9999,
        token_type="Bearer",
    )
    store = FakeStore(bundle)
    auth = CognitoSrpAuth(
        email="u@test.com",
        password="pw",
        token_store=store,
        session=None,  # type: ignore[arg-type]
    )
    await auth.invalidate_access_token()
    reloaded = await store.load()
    assert reloaded is not None
    assert reloaded.expires_at == 0.0


async def test_invalidate_access_token_no_bundle() -> None:
    """invalidate_access_token on empty store is a no-op."""
    store = FakeStore()
    auth = CognitoSrpAuth(
        email="u@test.com",
        password="pw",
        token_store=store,
        session=None,  # type: ignore[arg-type]
    )
    await auth.invalidate_access_token()  # should not raise
    assert await store.load() is None
