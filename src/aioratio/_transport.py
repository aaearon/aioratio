"""Private HTTP transport for the Ratio cloud API.

Wraps an :class:`aiohttp.ClientSession` and a :class:`CognitoSrpAuth`
instance: every request is signed with a bearer access token and a
single 401 retry is attempted (forcing the auth driver to refresh or
re-login on the second call).

This module is intentionally private -- public callers go through
:class:`aioratio.client.RatioClient`.
"""

from __future__ import annotations

import json as _json
import logging
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

_LOGGER = logging.getLogger(__name__)


class _CloudTransport:
    """Private async HTTP transport for the Ratio cloud API."""

    def __init__(
        self,
        *,
        auth: CognitoSrpAuth,
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
    ) -> dict[str, Any] | list[Any] | None:
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
                _LOGGER.debug("%s %s connection error: %s", method_upper, path, err)
                raise RatioConnectionError(str(err)) from err
            except TimeoutError as err:
                _LOGGER.debug("%s %s timed out", method_upper, path)
                raise RatioConnectionError("request timed out") from err

            if status == 401:
                if retried:
                    _LOGGER.debug("%s %s still 401 after refresh", method_upper, path)
                    raise RatioAuthError("authentication rejected after refresh")
                retried = True
                _LOGGER.debug("%s %s got 401; invalidating and retrying", method_upper, path)
                await self._auth.invalidate_access_token()
                continue

            if status == 429:
                msg = "rate limit exceeded"
                if retry_after:
                    msg = f"{msg} (retry-after={retry_after})"
                _LOGGER.debug("%s %s rate-limited: %s", method_upper, path, msg)
                raise RatioRateLimitError(msg, status=status)

            if status >= 400:
                body_text = body_bytes.decode("utf-8", errors="replace")
                _LOGGER.debug("%s %s -> HTTP %s: %s", method_upper, path, status, body_text)
                raise RatioApiError(f"HTTP {status}: {body_text}", status=status)

            if not body_bytes:
                return None
            if "json" in content_type.lower() or body_bytes.lstrip().startswith((b"{", b"[")):
                try:
                    return _json.loads(body_bytes.decode("utf-8"))
                except ValueError as err:
                    # Status was 2xx — surface that on the error so callers
                    # can distinguish "200 with garbage body" from a real
                    # 4xx/5xx failure.
                    raise RatioApiError(f"invalid JSON response: {err}", status=status) from err
            return None


__all__ = ["_CloudTransport"]
