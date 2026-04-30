"""High-level Ratio EV Charging API client.

Orchestrates :class:`CognitoSrpAuth`, :class:`_CloudTransport`, and the
typed dataclass models. ``RatioClient`` is the only public entry point
expected to be used by library consumers.
"""
from __future__ import annotations

import base64
import dataclasses
import json as _json
import uuid
from datetime import datetime, timezone
from typing import Any, Optional, Union

import aiohttp

from ._transport import _CloudTransport
from .auth import CognitoSrpAuth
from .const import (
    API_BASE_URL,
    COGNITO_CLIENT_ID,
    COGNITO_REGION,
    COGNITO_USER_POOL_ID,
)
from .exceptions import RatioAuthError
from .models import (
    ChargeSchedule,
    Charger,
    ChargerOverview,
    SessionHistoryPage,
    SolarSettings,
    UserSettings,
    Vehicle,
)
from .token_store import MemoryTokenStore, TokenStore


def _new_transaction_id() -> str:
    return uuid.uuid4().hex[:16]


def _decode_jwt_payload(token: str) -> dict[str, Any]:
    """Decode the (unverified) payload of a JWT."""
    if not token:
        raise RatioAuthError("missing id token")
    parts = token.split(".")
    if len(parts) < 2:
        raise RatioAuthError("malformed id token")
    payload = parts[1]
    # urlsafe base64 may lack padding
    padding = "=" * (-len(payload) % 4)
    try:
        raw = base64.urlsafe_b64decode(payload + padding)
        return _json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as err:
        raise RatioAuthError(f"failed to decode id token: {err}") from err


def _epoch_seconds(value: Union[datetime, int, None]) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return int(value.timestamp())
    return int(value)


def _ensure_list(payload: Any, key: str) -> list[Any]:
    """Return ``payload[key]`` if dict-wrapped, else ``payload`` if list."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        v = payload.get(key)
        if isinstance(v, list):
            return v
    return []


class RatioClient:
    """Async client for the Ratio EV Charging cloud API."""

    def __init__(
        self,
        *,
        email: str | None = None,
        password: str | None = None,
        token_store: TokenStore | None = None,
        session: aiohttp.ClientSession | None = None,
        client_id: str = COGNITO_CLIENT_ID,
        user_pool_id: str = COGNITO_USER_POOL_ID,
        region: str = COGNITO_REGION,
        base_url: str = API_BASE_URL,
        timeout: float = 30.0,
    ) -> None:
        self._email = email
        self._password = password
        self._token_store = token_store or MemoryTokenStore()
        self._client_id = client_id
        self._user_pool_id = user_pool_id
        self._region = region
        self._base_url = base_url
        self._timeout = timeout

        self._supplied_session = session is not None
        self._session: aiohttp.ClientSession | None = session
        self._auth: CognitoSrpAuth | None = None
        self._transport: _CloudTransport | None = None
        self._closed = False

        if session is not None:
            self._init_components(session)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def _init_components(self, session: aiohttp.ClientSession) -> None:
        self._auth = CognitoSrpAuth(
            email=self._email,
            password=self._password,
            token_store=self._token_store,
            session=session,
            client_id=self._client_id,
            user_pool_id=self._user_pool_id,
            region=self._region,
        )
        self._transport = _CloudTransport(
            auth=self._auth,
            session=session,
            base_url=self._base_url,
            timeout=self._timeout,
        )

    def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None:
            self._session = aiohttp.ClientSession()
            self._init_components(self._session)
        return self._session

    @property
    def transport(self) -> _CloudTransport:
        """Return the bound transport, creating a session if needed."""
        if self._transport is None:
            self._ensure_session()
        assert self._transport is not None
        return self._transport

    @property
    def auth(self) -> CognitoSrpAuth:
        if self._auth is None:
            self._ensure_session()
        assert self._auth is not None
        return self._auth

    async def __aenter__(self) -> "RatioClient":
        self._ensure_session()
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._session is not None and not self._supplied_session:
            await self._session.close()

    # ------------------------------------------------------------------
    # Auth-related helpers
    # ------------------------------------------------------------------
    async def login(self) -> None:
        """Force a fresh login, ignoring any cached token state."""
        await self.auth.login()

    async def user_id(self) -> str:
        """Return the ``sub`` claim from the current ID token."""
        # ensure tokens are present (will trigger login if needed)
        await self.auth.get_access_token()
        bundle = await self._token_store.load()
        if bundle is None or not bundle.id_token:
            raise RatioAuthError("no id token available")
        payload = _decode_jwt_payload(bundle.id_token)
        sub = payload.get("sub") or payload.get("cognito:username")
        if not sub:
            raise RatioAuthError("id token has no sub claim")
        return str(sub)

    # ------------------------------------------------------------------
    # Chargers
    # ------------------------------------------------------------------
    async def chargers(self) -> list[Charger]:
        uid = await self.user_id()
        data = await self.transport.request("GET", f"/users/{uid}/chargers")
        items = _ensure_list(data, "chargers")
        return [Charger.from_dict(c) for c in items if isinstance(c, dict)]

    async def chargers_overview(self) -> list[ChargerOverview]:
        uid = await self.user_id()
        data = await self.transport.request(
            "GET",
            f"/users/{uid}/chargers/status",
            params={"id": "overview"},
        )
        items = _ensure_list(data, "chargers")
        return [ChargerOverview.from_dict(c) for c in items if isinstance(c, dict)]

    async def charger_overview(self, serial: str) -> ChargerOverview:
        uid = await self.user_id()
        data = await self.transport.request(
            "GET",
            f"/users/{uid}/chargers/{serial}/status",
            params={"id": "overview"},
        )
        if not isinstance(data, dict):
            raise RatioAuthError("unexpected response for charger_overview")
        return ChargerOverview.from_dict(data)

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------
    async def _send_command(
        self,
        serial: str,
        command_id: str,
        body: dict[str, Any],
    ) -> None:
        uid = await self.user_id()
        await self.transport.request(
            "PUT",
            f"/users/{uid}/chargers/{serial}/command",
            params={"id": command_id},
            json=body,
        )

    async def start_charge(
        self, serial: str, vehicle_id: str | None = None
    ) -> None:
        params: dict[str, Any] = {}
        if vehicle_id is not None:
            params["vehicleId"] = vehicle_id
        body: dict[str, Any] = {
            "transactionId": _new_transaction_id(),
            "command": "start-charge",
            "startCommandParameters": params,
        }
        await self._send_command(serial, "start-charge", body)

    async def stop_charge(self, serial: str) -> None:
        body = {
            "transactionId": _new_transaction_id(),
            "command": "stop-charge",
        }
        await self._send_command(serial, "stop-charge", body)

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------
    async def _get_settings(self, serial: str, kind: str) -> Any:
        uid = await self.user_id()
        return await self.transport.request(
            "GET",
            f"/users/{uid}/chargers/{serial}/settings",
            params={"id": kind},
        )

    async def _put_settings(
        self, serial: str, kind: str, body: dict[str, Any]
    ) -> None:
        uid = await self.user_id()
        await self.transport.request(
            "PUT",
            f"/users/{uid}/chargers/{serial}/settings",
            params={"id": kind},
            json=body,
        )

    @staticmethod
    def _coerce_body(value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        to_dict = getattr(value, "to_dict", None)
        if callable(to_dict):
            return to_dict()
        if dataclasses.is_dataclass(value):
            # Best-effort fallback for dataclass models without an
            # explicit ``to_dict`` (e.g. UserSettings/ChargeSchedule).
            return dataclasses.asdict(value)
        raise TypeError(f"cannot serialise {type(value).__name__} to JSON body")

    async def user_settings(self, serial: str) -> UserSettings:
        data = await self._get_settings(serial, "user")
        return UserSettings.from_dict(data or {})

    async def set_user_settings(
        self, serial: str, settings: UserSettings | dict
    ) -> None:
        await self._put_settings(serial, "user", self._coerce_body(settings))

    async def charge_schedule(self, serial: str) -> ChargeSchedule:
        data = await self._get_settings(serial, "chargeSchedule")
        return ChargeSchedule.from_dict(data or {})

    async def set_charge_schedule(
        self, serial: str, schedule: ChargeSchedule | dict
    ) -> None:
        await self._put_settings(
            serial, "chargeSchedule", self._coerce_body(schedule)
        )

    async def solar_settings(self, serial: str) -> SolarSettings:
        data = await self._get_settings(serial, "solar")
        return SolarSettings.from_dict(data or {})

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------
    async def session_history(
        self,
        *,
        begin_time: datetime | int | None = None,
        end_time: datetime | int | None = None,
        vehicle_id: str | None = None,
        serial_number: str | None = None,
        next_token: str | None = None,
    ) -> SessionHistoryPage:
        uid = await self.user_id()
        params: dict[str, Any] = {}
        b = _epoch_seconds(begin_time)
        e = _epoch_seconds(end_time)
        # NOTE: APK uses epoch seconds; not 100% confirmed against live
        # cloud — TODO verify if cloud expects ms instead.
        if b is not None:
            params["beginTime"] = b
        if e is not None:
            params["endTime"] = e
        if vehicle_id is not None:
            params["vehicleId"] = vehicle_id
        if serial_number is not None:
            params["serialNumber"] = serial_number
        if next_token is not None:
            params["nextToken"] = next_token
        data = await self.transport.request(
            "GET", f"/users/{uid}/session-history", params=params or None
        )
        return SessionHistoryPage.from_dict(data or {})

    # ------------------------------------------------------------------
    # Vehicles
    # ------------------------------------------------------------------
    async def vehicles(self) -> list[Vehicle]:
        uid = await self.user_id()
        data = await self.transport.request("GET", f"/users/{uid}/vehicles")
        items = _ensure_list(data, "vehicles")
        return [Vehicle.from_dict(v) for v in items if isinstance(v, dict)]

    async def add_vehicle(self, vehicle: Vehicle | dict) -> Vehicle:
        uid = await self.user_id()
        body = self._coerce_body(vehicle)
        data = await self.transport.request(
            "POST", f"/users/{uid}/vehicles", json=body
        )
        if isinstance(data, dict):
            return Vehicle.from_dict(data)
        # Some APIs echo nothing — return what was sent.
        return Vehicle.from_dict(body)

    async def remove_vehicle(self, vehicle_id: str) -> None:
        uid = await self.user_id()
        await self.transport.request(
            "DELETE", f"/users/{uid}/vehicles/{vehicle_id}"
        )


__all__ = ["RatioClient"]
