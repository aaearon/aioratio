"""Private HTTP transport for the Ratio cloud API.

Wraps an :class:`aiohttp.ClientSession` and a :class:`CognitoSrpAuth`
instance: every request is signed with a bearer access token and a
single 401 retry is attempted (forcing the auth driver to refresh or
re-login on the second call).

This module is intentionally private -- public callers go through
:class:`aioratio.client.RatioClient`.
"""
from __future__ import annotations

import asyncio
import json as _json
from typing import TYPE_CHECKING, Any

import aiohttp

from .const import API_BASE_URL, USER_AGENT
from .exceptions import (
    RatioApiError,
    RatioAuthError,
    RatioConnectionError,
    RatioRateLimitError,
)

if TYPE_CHECKING:
    from .auth import CognitoSrpAuth


class _CloudTransport:
    """Private async HTTP transport for the Ratio cloud API."""

    def __init__(
        self,
        *,
        auth: "CognitoSrpAuth",
        session: aiohttp.ClientSession,
        base_url: str = API_BASE_URL,
        timeout: float = 30.0,
    ) -> None:
        self._auth = auth
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._timeout = aiohttp.ClientTimeout(total=timeout)

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> Any:
        """Send an authenticated request and return parsed JSON or None."""
        if not path.startswith("/"):
            path = "/" + path
        url = self._base_url + path
        method_upper = method.upper()

        retried = False
        while True:
            access_token = await self._auth.get_access_token()
            headers = {
                "Authorization": f"Bearer {access_token}",
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
            }
            if method_upper != "GET" and json is not None:
                headers["Content-Type"] = "application/json"

            try:
                async with self._session.request(
                    method_upper,
                    url,
                    params=params,
                    json=json,
                    headers=headers,
                    timeout=self._timeout,
                ) as resp:
                    status = resp.status
                    body_bytes = await resp.read()
                    content_type = resp.headers.get("Content-Type", "")
                    retry_after = resp.headers.get("Retry-After")
            except aiohttp.ClientError as err:
                raise RatioConnectionError(str(err)) from err
            except asyncio.TimeoutError as err:
                raise RatioConnectionError("request timed out") from err

            if status == 401:
                if retried:
                    raise RatioAuthError("authentication rejected after refresh")
                retried = True
                # Best-effort: expire any cached bundle so the next
                # get_access_token() forces a refresh or re-login.
                store = getattr(self._auth, "_token_store", None)
                if store is not None:
                    try:
                        bundle = await store.load()
                    except Exception:  # pragma: no cover - defensive
                        bundle = None
                    if bundle is not None:
                        bundle.expires_at = 0.0
                        try:
                            await store.save(bundle)
                        except Exception:  # pragma: no cover - defensive
                            pass
                continue

            if status == 429:
                msg = "rate limit exceeded"
                if retry_after:
                    msg = f"{msg} (retry-after={retry_after})"
                raise RatioRateLimitError(msg)

            if status >= 400:
                body_text = body_bytes.decode("utf-8", errors="replace")
                raise RatioApiError(f"HTTP {status}: {body_text}")

            if not body_bytes:
                return None
            if "json" in content_type.lower() or body_bytes.lstrip().startswith(
                (b"{", b"[")
            ):
                try:
                    return _json.loads(body_bytes.decode("utf-8"))
                except ValueError as err:
                    raise RatioApiError(f"invalid JSON response: {err}") from err
            return None


__all__ = ["_CloudTransport"]
