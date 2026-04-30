"""Cognito SRP authentication driver.

Implements three flows against the Cognito Identity Provider service:

1. First-time login (``USER_SRP_AUTH`` -> ``ConfirmDevice`` ->
   ``UpdateDeviceStatus``).
2. Subsequent login with a remembered device (``USER_SRP_AUTH`` ->
   ``DEVICE_SRP_AUTH`` -> ``DEVICE_PASSWORD_VERIFIER``).
3. Refresh-token grant (``REFRESH_TOKEN_AUTH``) with rotation handling.

Token persistence is delegated to :class:`TokenStore`.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any

import aiohttp

from .const import COGNITO_CLIENT_ID, COGNITO_REGION, COGNITO_USER_POOL_ID
from .exceptions import (
    RatioApiError,
    RatioAuthError,
    RatioConnectionError,
    RatioRateLimitError,
)
from . import srp as _srp

# ``token_store.py`` is being implemented in parallel; fall back to a
# local-compatible definition so this module is importable today.
try:  # pragma: no cover - fallback exercised when stub lacks symbols
    from .token_store import TokenBundle, TokenStore  # type: ignore[attr-defined]
except ImportError:  # pragma: no cover
    # TODO: remove fallback once token_store.py is implemented (parallel work)
    from dataclasses import dataclass, field
    from .token_store import TokenStore  # type: ignore

    @dataclass
    class TokenBundle:  # type: ignore[no-redef]
        access_token: str
        id_token: str
        refresh_token: str
        expires_at: float
        token_type: str = "Bearer"
        device_key: str | None = None
        device_group_key: str | None = None
        device_password: str | None = None

        @property
        def is_expired(self) -> bool:
            return time.time() >= self.expires_at - 30


_DEVICE_NAME = "Home Assistant via aioratio"


def _cognito_url(region: str) -> str:
    return f"https://cognito-idp.{region}.amazonaws.com/"


def _expires_at(expires_in: int | float) -> float:
    return time.time() + float(expires_in)


def _is_expired(bundle: "TokenBundle") -> bool:
    """Bundle expiry check that works whether or not the bundle exposes
    an ``is_expired`` property (the parallel agent's version may)."""
    prop = getattr(bundle, "is_expired", None)
    if isinstance(prop, bool):
        return prop
    return time.time() >= bundle.expires_at - 30


class CognitoSrpAuth:
    """Cognito SRP authentication driver."""

    def __init__(
        self,
        *,
        email: str | None,
        password: str | None,
        token_store: TokenStore,
        session: aiohttp.ClientSession,
        client_id: str = COGNITO_CLIENT_ID,
        user_pool_id: str = COGNITO_USER_POOL_ID,
        region: str = COGNITO_REGION,
    ) -> None:
        self._email = email
        self._password = password
        self._token_store = token_store
        self._session = session
        self._client_id = client_id
        self._user_pool_id = user_pool_id
        self._region = region
        self._lock = asyncio.Lock()

    @property
    def pool_name(self) -> str:
        """The portion of the user-pool id after the underscore."""
        return self._user_pool_id.split("_", 1)[1]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def get_access_token(self) -> str:
        async with self._lock:
            bundle = await self._token_store.load()
            if bundle is None:
                bundle = await self._login_locked()
            elif _is_expired(bundle):
                if bundle.refresh_token:
                    try:
                        bundle = await self._refresh_locked(bundle)
                    except RatioAuthError:
                        bundle = await self._login_locked()
                else:
                    bundle = await self._login_locked()
            return bundle.access_token

    async def login(self) -> TokenBundle:
        async with self._lock:
            return await self._login_locked()

    async def refresh(self, bundle: TokenBundle) -> TokenBundle:
        async with self._lock:
            return await self._refresh_locked(bundle)

    # ------------------------------------------------------------------
    # Internals (assume lock held)
    # ------------------------------------------------------------------
    async def _login_locked(self) -> TokenBundle:
        if self._email is None or self._password is None:
            raise RatioAuthError("email and password required for login")

        existing = await self._token_store.load()
        device_key = getattr(existing, "device_key", None) if existing else None
        device_group_key = (
            getattr(existing, "device_group_key", None) if existing else None
        )
        device_password = (
            getattr(existing, "device_password", None) if existing else None
        )

        user_srp = _srp.UserSrp()
        srp_a = user_srp.start()

        auth_params: dict[str, str] = {
            "USERNAME": self._email,
            "SRP_A": srp_a,
        }
        if device_key:
            auth_params["DEVICE_KEY"] = device_key

        init = await self._initiate_auth("USER_SRP_AUTH", auth_params)
        challenge = init.get("ChallengeName")
        if challenge != "PASSWORD_VERIFIER":
            self._raise_unsupported(challenge)

        cp = init["ChallengeParameters"]
        srp_username = cp["USERNAME"]  # echo this verbatim
        user_id_for_srp = cp["USER_ID_FOR_SRP"]
        signature, ts = user_srp.process_challenge(
            cp["SRP_B"],
            cp["SALT"],
            cp["SECRET_BLOCK"],
            user_id_for_srp,
            self.pool_name,
            self._password,
        )
        responses = {
            "USERNAME": srp_username,
            "PASSWORD_CLAIM_SECRET_BLOCK": cp["SECRET_BLOCK"],
            "PASSWORD_CLAIM_SIGNATURE": signature,
            "TIMESTAMP": ts,
        }
        if device_key:
            responses["DEVICE_KEY"] = device_key
        resp = await self._respond_to_challenge("PASSWORD_VERIFIER", responses)

        # If a remembered device exists, Cognito returns DEVICE_SRP_AUTH next.
        if resp.get("ChallengeName") == "DEVICE_SRP_AUTH":
            if not (device_key and device_group_key and device_password):
                raise RatioAuthError(
                    "DEVICE_SRP_AUTH challenge issued but no stored device"
                )
            device_srp = _srp.DeviceSrp(
                device_group_key, device_key, device_password
            )
            device_a = device_srp.start()
            cp2 = resp["ChallengeParameters"]
            username2 = cp2.get("USERNAME", srp_username)
            resp2 = await self._respond_to_challenge(
                "DEVICE_SRP_AUTH",
                {
                    "USERNAME": username2,
                    "DEVICE_KEY": device_key,
                    "SRP_A": device_a,
                },
            )
            if resp2.get("ChallengeName") != "DEVICE_PASSWORD_VERIFIER":
                self._raise_unsupported(resp2.get("ChallengeName"))
            cp3 = resp2["ChallengeParameters"]
            username3 = cp3.get("USERNAME", username2)
            sig2, ts2 = device_srp.process_challenge(
                cp3["SRP_B"], cp3["SALT"], cp3["SECRET_BLOCK"]
            )
            resp3 = await self._respond_to_challenge(
                "DEVICE_PASSWORD_VERIFIER",
                {
                    "USERNAME": username3,
                    "PASSWORD_CLAIM_SECRET_BLOCK": cp3["SECRET_BLOCK"],
                    "PASSWORD_CLAIM_SIGNATURE": sig2,
                    "TIMESTAMP": ts2,
                    "DEVICE_KEY": device_key,
                },
            )
            auth_result = self._extract_auth_result(resp3)
            bundle = self._build_bundle(
                auth_result,
                device_key=device_key,
                device_group_key=device_group_key,
                device_password=device_password,
                fallback_refresh=existing.refresh_token if existing else None,
            )
            await self._token_store.save(bundle)
            return bundle

        # Otherwise expect AuthenticationResult and possibly NewDeviceMetadata.
        if "AuthenticationResult" not in resp:
            self._raise_unsupported(resp.get("ChallengeName"))
        auth_result = resp["AuthenticationResult"]
        new_dev = auth_result.get("NewDeviceMetadata") or {}
        new_device_key = new_dev.get("DeviceKey")
        new_device_group_key = new_dev.get("DeviceGroupKey")
        new_device_password: str | None = None
        if new_device_key and new_device_group_key:
            verifier = _srp.generate_device_verifier(
                new_device_group_key, new_device_key
            )
            new_device_password = verifier["password"]
            await self._confirm_device(
                access_token=auth_result["AccessToken"],
                device_key=new_device_key,
                password_verifier=verifier["verifier_b64"],
                salt=verifier["salt_b64"],
            )
            await self._update_device_status(
                access_token=auth_result["AccessToken"],
                device_key=new_device_key,
            )

        bundle = self._build_bundle(
            auth_result,
            device_key=new_device_key,
            device_group_key=new_device_group_key,
            device_password=new_device_password,
        )
        await self._token_store.save(bundle)
        return bundle

    async def _refresh_locked(self, bundle: TokenBundle) -> TokenBundle:
        if not bundle.refresh_token:
            raise RatioAuthError("no refresh token available")
        params: dict[str, str] = {"REFRESH_TOKEN": bundle.refresh_token}
        if bundle.device_key:
            params["DEVICE_KEY"] = bundle.device_key
        resp = await self._initiate_auth("REFRESH_TOKEN_AUTH", params)
        if "AuthenticationResult" not in resp:
            self._raise_unsupported(resp.get("ChallengeName"))
        auth_result = resp["AuthenticationResult"]
        new_bundle = self._build_bundle(
            auth_result,
            device_key=bundle.device_key,
            device_group_key=bundle.device_group_key,
            device_password=bundle.device_password,
            fallback_refresh=bundle.refresh_token,
        )
        await self._token_store.save(new_bundle)
        return new_bundle

    # ------------------------------------------------------------------
    # Cognito wire calls
    # ------------------------------------------------------------------
    async def _initiate_auth(
        self, auth_flow: str, auth_parameters: dict[str, str]
    ) -> dict[str, Any]:
        return await self._cognito_call(
            "InitiateAuth",
            {
                "AuthFlow": auth_flow,
                "ClientId": self._client_id,
                "AuthParameters": auth_parameters,
            },
        )

    async def _respond_to_challenge(
        self, challenge_name: str, responses: dict[str, str]
    ) -> dict[str, Any]:
        return await self._cognito_call(
            "RespondToAuthChallenge",
            {
                "ChallengeName": challenge_name,
                "ClientId": self._client_id,
                "ChallengeResponses": responses,
            },
        )

    async def _confirm_device(
        self,
        *,
        access_token: str,
        device_key: str,
        password_verifier: str,
        salt: str,
    ) -> None:
        await self._cognito_call(
            "ConfirmDevice",
            {
                "AccessToken": access_token,
                "DeviceKey": device_key,
                "DeviceName": _DEVICE_NAME,
                "DeviceSecretVerifierConfig": {
                    "PasswordVerifier": password_verifier,
                    "Salt": salt,
                },
            },
        )

    async def _update_device_status(
        self, *, access_token: str, device_key: str
    ) -> None:
        await self._cognito_call(
            "UpdateDeviceStatus",
            {
                "AccessToken": access_token,
                "DeviceKey": device_key,
                "DeviceRememberedStatus": "remembered",
            },
        )

    async def _cognito_call(self, target: str, body: dict[str, Any]) -> dict[str, Any]:
        url = _cognito_url(self._region)
        headers = {
            "Content-Type": "application/x-amz-json-1.1",
            "X-Amz-Target": f"AWSCognitoIdentityProviderService.{target}",
        }
        try:
            async with self._session.post(url, headers=headers, json=body) as resp:
                status = resp.status
                text = await resp.text()
        except aiohttp.ClientError as err:
            raise RatioConnectionError(str(err)) from err
        except asyncio.TimeoutError as err:
            raise RatioConnectionError("request timed out") from err

        try:
            import json
            data = json.loads(text) if text else {}
        except ValueError as err:
            raise RatioAuthError(f"invalid JSON from Cognito: {text!r}") from err

        if status >= 400 or "__type" in data:
            self._raise_cognito_error(data, status)
        return data

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _build_bundle(
        self,
        auth_result: dict[str, Any],
        *,
        device_key: str | None,
        device_group_key: str | None,
        device_password: str | None,
        fallback_refresh: str | None = None,
    ) -> TokenBundle:
        refresh = auth_result.get("RefreshToken") or fallback_refresh or ""
        return TokenBundle(
            access_token=auth_result["AccessToken"],
            id_token=auth_result.get("IdToken", ""),
            refresh_token=refresh,
            expires_at=_expires_at(auth_result.get("ExpiresIn", 3600)),
            token_type=auth_result.get("TokenType", "Bearer"),
            device_key=device_key,
            device_group_key=device_group_key,
            device_password=device_password,
        )

    @staticmethod
    def _extract_auth_result(resp: dict[str, Any]) -> dict[str, Any]:
        if "AuthenticationResult" not in resp:
            raise RatioAuthError(
                f"unexpected Cognito response: {resp.get('ChallengeName')!r}"
            )
        return resp["AuthenticationResult"]

    @staticmethod
    def _raise_unsupported(name: str | None) -> None:
        raise RatioAuthError(f"unsupported challenge: {name}")

    @staticmethod
    def _raise_cognito_error(data: dict[str, Any], status: int) -> None:
        err_type = data.get("__type", "")
        message = data.get("message") or data.get("Message") or err_type or "Cognito error"
        short = err_type.rsplit("#", 1)[-1] if err_type else ""
        if short in {
            "NotAuthorizedException",
            "UserNotFoundException",
            "PasswordResetRequiredException",
            "UserNotConfirmedException",
            "InvalidParameterException",
        }:
            raise RatioAuthError(f"{short}: {message}")
        if short == "TooManyRequestsException":
            raise RatioRateLimitError(f"{short}: {message}")
        if status >= 500:
            raise RatioApiError(f"Cognito {status}: {message}")
        raise RatioAuthError(f"{short or 'CognitoError'}: {message}")


__all__ = ["CognitoSrpAuth", "TokenBundle"]
