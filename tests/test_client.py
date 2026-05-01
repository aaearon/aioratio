"""Tests for RatioClient and the private _CloudTransport."""
from __future__ import annotations

import asyncio
import base64
import json
import time
from datetime import datetime, timezone
from typing import Any

import aiohttp
import pytest
from aiohttp import web

from aioratio.client import RatioClient
from aioratio.exceptions import (
    RatioApiError,
    RatioAuthError,
    RatioConnectionError,
    RatioRateLimitError,
)
from aioratio.models import (
    ChargeSchedule,
    ChargerOverview,
    UserSettings,
    Vehicle,
)
from aioratio.token_store import MemoryTokenStore, TokenBundle


# ---------------------------------------------------------------------------
# Fixtures / fakes
# ---------------------------------------------------------------------------


def _make_id_token(sub: str = "user-abc") -> str:
    header = base64.urlsafe_b64encode(b'{"alg":"none"}').rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(
        json.dumps({"sub": sub}).encode()
    ).rstrip(b"=").decode()
    return f"{header}.{payload}.sig"


def _make_bundle(*, access: str = "ACCESS", sub: str = "user-abc") -> TokenBundle:
    return TokenBundle(
        access_token=access,
        id_token=_make_id_token(sub),
        refresh_token="REFRESH",
        expires_at=time.time() + 3600,
    )


class FakeTransport:
    """Captures calls and returns canned responses."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self._responses: list[Any] = []

    def queue(self, response: Any) -> None:
        self._responses.append(response)

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> Any:
        self.calls.append(
            {"method": method, "path": path, "params": params, "json": json}
        )
        if not self._responses:
            return None
        resp = self._responses.pop(0)
        if isinstance(resp, Exception):
            raise resp
        return resp


@pytest.fixture
async def client_with_fake_transport():
    bundle = _make_bundle()
    store = MemoryTokenStore()
    await store.save(bundle)
    session = aiohttp.ClientSession()
    client = RatioClient(token_store=store, session=session)
    fake = FakeTransport()
    client._transport = fake  # type: ignore[assignment]
    try:
        yield client, fake
    finally:
        await session.close()


# ---------------------------------------------------------------------------
# user_id helper
# ---------------------------------------------------------------------------


async def test_user_id_from_id_token():
    bundle = _make_bundle(sub="abc-123")
    store = MemoryTokenStore()
    await store.save(bundle)
    async with aiohttp.ClientSession() as session:
        client = RatioClient(token_store=store, session=session)
        # Avoid hitting the real auth flow – stub get_access_token.

        async def _fake_get_access_token() -> str:
            return bundle.access_token

        client._auth.get_access_token = _fake_get_access_token  # type: ignore[assignment]
        assert await client.user_id() == "abc-123"


# ---------------------------------------------------------------------------
# Charger endpoints
# ---------------------------------------------------------------------------


async def test_chargers_overview_get_request_shape(client_with_fake_transport):
    client, fake = client_with_fake_transport
    fake.queue({"chargers": []})
    await client.chargers_overview()
    call = fake.calls[0]
    assert call["method"] == "GET"
    assert call["path"] == "/users/user-abc/chargers/status"
    assert call["params"] == {"id": "overview"}
    assert call["json"] is None


async def test_chargers_overview_parses_models(client_with_fake_transport):
    client, fake = client_with_fake_transport
    fake.queue(
        {
            "chargers": [
                {"serialNumber": "A1", "cloudConnectionState": "CONNECTED"},
                {"serialNumber": "B2"},
            ]
        }
    )
    out = await client.chargers_overview()
    assert len(out) == 2
    assert all(isinstance(o, ChargerOverview) for o in out)
    assert out[0].serial_number == "A1"
    assert out[0].cloud_connection_state == "CONNECTED"


async def test_chargers_overview_handles_bare_list_response(
    client_with_fake_transport,
):
    client, fake = client_with_fake_transport
    fake.queue([{"serialNumber": "X"}])
    out = await client.chargers_overview()
    assert len(out) == 1
    assert out[0].serial_number == "X"


async def test_charger_overview_single(client_with_fake_transport):
    client, fake = client_with_fake_transport
    fake.queue({"serialNumber": "S1"})
    out = await client.charger_overview("S1")
    assert isinstance(out, ChargerOverview)
    assert out.serial_number == "S1"
    call = fake.calls[0]
    assert call["path"] == "/users/user-abc/chargers/S1/status"
    assert call["params"] == {"id": "overview"}


async def test_chargers_list(client_with_fake_transport):
    client, fake = client_with_fake_transport
    fake.queue([{"serialNumber": "Z"}])
    out = await client.chargers()
    assert len(out) == 1
    assert out[0].serial_number == "Z"


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


async def test_start_charge_includes_transaction_id_and_vehicle(
    client_with_fake_transport,
):
    client, fake = client_with_fake_transport
    fake.queue(None)
    await client.start_charge("SER1", vehicle_id="V42")
    call = fake.calls[0]
    assert call["method"] == "PUT"
    assert call["path"] == "/users/user-abc/chargers/SER1/command"
    assert call["params"] == {"id": "start-charge"}
    body = call["json"]
    assert body["command"] == "start-charge"
    assert isinstance(body["transactionId"], str)
    assert len(body["transactionId"]) == 16
    int(body["transactionId"], 16)  # is hex
    assert body["startCommandParameters"] == {"vehicleId": "V42"}


async def test_start_charge_no_vehicle_id(client_with_fake_transport):
    client, fake = client_with_fake_transport
    fake.queue(None)
    await client.start_charge("SER1")
    body = fake.calls[0]["json"]
    assert body["startCommandParameters"] == {}
    assert body["command"] == "start-charge"
    assert len(body["transactionId"]) == 16


async def test_stop_charge_request_shape(client_with_fake_transport):
    client, fake = client_with_fake_transport
    fake.queue(None)
    await client.stop_charge("SER1")
    call = fake.calls[0]
    assert call["method"] == "PUT"
    assert call["path"] == "/users/user-abc/chargers/SER1/command"
    assert call["params"] == {"id": "stop-charge"}
    assert call["json"]["command"] == "stop-charge"
    assert len(call["json"]["transactionId"]) == 16


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


async def test_user_settings_get_and_parse(client_with_fake_transport):
    client, fake = client_with_fake_transport
    fake.queue(
        {
            "chargingMode": {
                "value": "SMART_SOLAR",
                "allowedValues": ["SMART_SOLAR", "FAST"],
            }
        }
    )
    settings = await client.user_settings("S1")
    assert isinstance(settings, UserSettings)
    assert settings.charging_mode is not None
    assert settings.charging_mode.value == "SMART_SOLAR"
    call = fake.calls[0]
    assert call["method"] == "GET"
    assert call["path"] == "/users/user-abc/chargers/S1/settings"
    assert call["params"] == {"id": "user"}


async def test_set_user_settings_put_body_dict(client_with_fake_transport):
    client, fake = client_with_fake_transport
    fake.queue(None)
    payload = {"chargingMode": "FAST"}
    await client.set_user_settings("S1", payload)
    call = fake.calls[0]
    assert call["method"] == "PUT"
    assert call["params"] == {"id": "user"}
    body = call["json"]
    assert "transactionId" in body and len(body["transactionId"]) == 16
    assert body["userSettings"] == payload


async def test_set_user_settings_put_body_model(client_with_fake_transport):
    client, fake = client_with_fake_transport
    fake.queue(None)
    settings = UserSettings.from_dict({"chargingMode": {"value": "FAST"}})
    fake.calls.clear()
    fake.queue(None)
    await client.set_user_settings("S1", settings)
    call = fake.calls[0]
    assert call["method"] == "PUT"
    body = call["json"]
    assert "transactionId" in body
    inner = body["userSettings"]
    # API expects camelCase keys; dataclasses.asdict produces snake_case.
    # The client must convert.
    assert "chargingMode" in inner
    assert "charging_mode" not in inner
    assert inner["chargingMode"]["value"] == "FAST"
    # Nested fields also converted (allowed_values -> allowedValues)
    assert "allowedValues" in inner["chargingMode"]
    assert "allowed_values" not in inner["chargingMode"]


async def test_set_charge_schedule_camel_case_keys(client_with_fake_transport):
    from aioratio.models import ChargeSchedule, ScheduleSlot

    client, fake = client_with_fake_transport
    fake.queue(None)
    schedule = ChargeSchedule(
        enabled=True,
        schedule_type="WEEKLY",
        randomized_time_offset_enabled=True,
        delayed_start="07:00",
        slots=[ScheduleSlot(start="22:00", end="06:00", days=["MON", "TUE"])],
    )
    await client.set_charge_schedule("S1", schedule)
    inner = fake.calls[0]["json"]["chargeScheduleSettings"]
    assert "scheduleType" in inner and inner["scheduleType"] == "WEEKLY"
    assert "randomizedTimeOffsetEnabled" in inner
    assert "delayedStart" in inner
    assert "schedule_type" not in inner
    assert inner["slots"][0]["days"] == ["MON", "TUE"]


async def test_charge_schedule_get_and_set(client_with_fake_transport):
    client, fake = client_with_fake_transport
    fake.queue({"enabled": True, "scheduleType": "WEEKLY", "slots": []})
    sched = await client.charge_schedule("S1")
    assert isinstance(sched, ChargeSchedule)
    assert sched.enabled is True
    assert fake.calls[-1]["params"] == {"id": "chargeSchedule"}

    fake.queue(None)
    await client.set_charge_schedule("S1", {"enabled": False})
    last = fake.calls[-1]
    assert last["method"] == "PUT"
    assert last["params"] == {"id": "chargeSchedule"}
    body = last["json"]
    assert "transactionId" in body
    assert body["chargeScheduleSettings"] == {"enabled": False}


async def test_user_settings_get_strips_envelope(client_with_fake_transport):
    """Live cloud wraps the response in a userSettings envelope."""
    client, fake = client_with_fake_transport
    fake.queue(
        {
            "userSettings": {
                "chargingMode": {
                    "value": "PureSolar",
                    "allowedValues": ["Smart", "SmartSolar", "PureSolar"],
                }
            }
        }
    )
    settings = await client.user_settings("S1")
    assert settings.charging_mode is not None
    assert settings.charging_mode.value == "PureSolar"
    assert settings.charging_mode.allowed_values == ["Smart", "SmartSolar", "PureSolar"]


async def test_solar_settings_get(client_with_fake_transport):
    client, fake = client_with_fake_transport
    fake.queue({"sunOnDelayMinutes": {"value": 5, "lower": 1, "upper": 30}})
    out = await client.solar_settings("S1")
    assert out.sun_on_delay_minutes is not None
    assert out.sun_on_delay_minutes.value == 5.0


# ---------------------------------------------------------------------------
# Session history
# ---------------------------------------------------------------------------


async def test_session_history_query_params(client_with_fake_transport):
    client, fake = client_with_fake_transport
    fake.queue({"chargeSessions": [], "nextToken": "tok2"})
    begin = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end_epoch = int(begin.timestamp()) + 3600
    page = await client.session_history(
        begin_time=begin,
        end_time=end_epoch,
        vehicle_id="V1",
        serial_number="S1",
        next_token="tok1",
    )
    assert page.next_token == "tok2"
    call = fake.calls[0]
    assert call["method"] == "GET"
    assert call["path"] == "/users/user-abc/session-history"
    p = call["params"]
    assert p["beginTime"] == int(begin.timestamp())
    assert p["endTime"] == end_epoch
    assert p["vehicleId"] == "V1"
    assert p["serialNumber"] == "S1"
    assert p["nextToken"] == "tok1"


# ---------------------------------------------------------------------------
# Vehicles
# ---------------------------------------------------------------------------


async def test_vehicles_list_and_add_and_remove(client_with_fake_transport):
    client, fake = client_with_fake_transport
    fake.queue([{"vehicleId": "v1", "vehicleName": "Tesla"}])
    vs = await client.vehicles()
    assert len(vs) == 1 and vs[0].vehicle_id == "v1"
    assert fake.calls[-1]["method"] == "GET"
    assert fake.calls[-1]["path"] == "/users/user-abc/vehicles"

    fake.queue({"vehicleId": "v2", "vehicleName": "BMW"})
    out = await client.add_vehicle({"vehicleName": "BMW"})
    assert isinstance(out, Vehicle)
    assert out.vehicle_id == "v2"
    assert fake.calls[-1]["method"] == "POST"
    assert fake.calls[-1]["json"] == {"vehicleName": "BMW"}

    fake.queue(None)
    await client.remove_vehicle("v2")
    last = fake.calls[-1]
    assert last["method"] == "DELETE"
    assert last["path"] == "/users/user-abc/vehicles/v2"


# ---------------------------------------------------------------------------
# Lifecycle / session ownership
# ---------------------------------------------------------------------------


async def test_async_context_manager_closes_owned_session():
    bundle = _make_bundle()
    store = MemoryTokenStore()
    await store.save(bundle)
    async with RatioClient(token_store=store) as client:
        sess = client._session
        assert sess is not None
        assert not sess.closed
    assert sess.closed


async def test_supplied_session_not_closed_on_exit():
    bundle = _make_bundle()
    store = MemoryTokenStore()
    await store.save(bundle)
    session = aiohttp.ClientSession()
    try:
        async with RatioClient(token_store=store, session=session) as client:
            assert client._session is session
        assert not session.closed
    finally:
        await session.close()


# ---------------------------------------------------------------------------
# HTTP-level tests against an in-process aiohttp server
# ---------------------------------------------------------------------------


class _FakeAuth:
    """Drop-in stand-in for CognitoSrpAuth in transport-level tests."""

    def __init__(self, store, token: str = "TOKEN0") -> None:
        self._token_store = store
        self.token = token
        self.calls = 0

    async def get_access_token(self) -> str:
        self.calls += 1
        return self.token

    async def invalidate_access_token(self) -> None:
        bundle = await self._token_store.load()
        if bundle is not None:
            bundle.expires_at = 0.0
            await self._token_store.save(bundle)


async def _start_server(handler) -> tuple[web.AppRunner, str]:
    app = web.Application()
    app.router.add_route("*", "/{tail:.*}", handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    server = runner.addresses[0] if hasattr(runner, "addresses") else None
    # aiohttp <3.10 lacks addresses; fall back.
    if server is None:
        sock = site._server.sockets[0]  # type: ignore[union-attr]
        host, port = sock.getsockname()[:2]
    else:
        host, port = server[:2]
    base_url = f"http://{host}:{port}"
    return runner, base_url


async def _make_http_client(base_url: str, auth) -> tuple[RatioClient, aiohttp.ClientSession]:
    session = aiohttp.ClientSession()
    store = MemoryTokenStore()
    await store.save(_make_bundle())
    client = RatioClient(token_store=store, session=session, base_url=base_url)
    # Replace the real auth with our fake.
    client._auth = auth  # type: ignore[assignment]
    from aioratio._transport import _CloudTransport

    client._transport = _CloudTransport(
        auth=auth, session=session, base_url=base_url
    )
    return client, session


async def test_401_triggers_one_retry_then_raises():
    attempts = {"n": 0}

    async def handler(request: web.Request) -> web.Response:
        attempts["n"] += 1
        return web.Response(status=401, text="nope")

    runner, base_url = await _start_server(handler)
    try:
        store = MemoryTokenStore()
        await store.save(_make_bundle())
        auth = _FakeAuth(store)
        client, session = await _make_http_client(base_url, auth)
        try:
            with pytest.raises(RatioAuthError):
                await client.transport.request("GET", "/foo")
            assert attempts["n"] == 2
            # auth.get_access_token called once per attempt
            assert auth.calls == 2
        finally:
            await session.close()
    finally:
        await runner.cleanup()


async def test_401_then_200_succeeds_after_refresh():
    state = {"n": 0}

    async def handler(request: web.Request) -> web.Response:
        state["n"] += 1
        if state["n"] == 1:
            return web.Response(status=401)
        return web.json_response({"ok": True})

    runner, base_url = await _start_server(handler)
    try:
        store = MemoryTokenStore()
        await store.save(_make_bundle())
        auth = _FakeAuth(store)
        client, session = await _make_http_client(base_url, auth)
        try:
            out = await client.transport.request("GET", "/foo")
            assert out == {"ok": True}
            assert state["n"] == 2
            assert auth.calls == 2
        finally:
            await session.close()
    finally:
        await runner.cleanup()


async def test_429_raises_rate_limit():
    async def handler(request: web.Request) -> web.Response:
        return web.Response(status=429, headers={"Retry-After": "5"})

    runner, base_url = await _start_server(handler)
    try:
        store = MemoryTokenStore()
        await store.save(_make_bundle())
        auth = _FakeAuth(store)
        client, session = await _make_http_client(base_url, auth)
        try:
            with pytest.raises(RatioRateLimitError):
                await client.transport.request("GET", "/foo")
        finally:
            await session.close()
    finally:
        await runner.cleanup()


async def test_5xx_raises_api_error():
    async def handler(request: web.Request) -> web.Response:
        return web.Response(status=503, text="boom")

    runner, base_url = await _start_server(handler)
    try:
        store = MemoryTokenStore()
        await store.save(_make_bundle())
        auth = _FakeAuth(store)
        client, session = await _make_http_client(base_url, auth)
        try:
            with pytest.raises(RatioApiError):
                await client.transport.request("GET", "/foo")
        finally:
            await session.close()
    finally:
        await runner.cleanup()


async def test_network_error_raises_connection_error():
    # Connect to a closed port to provoke a ClientConnectionError.
    store = MemoryTokenStore()
    await store.save(_make_bundle())
    auth = _FakeAuth(store)
    session = aiohttp.ClientSession()
    try:
        from aioratio._transport import _CloudTransport

        # 127.0.0.1:1 is reliably refused.
        transport = _CloudTransport(
            auth=auth, session=session, base_url="http://127.0.0.1:1"
        )
        with pytest.raises(RatioConnectionError):
            await transport.request("GET", "/foo")
    finally:
        await session.close()


async def test_authorization_header_sent():
    captured: dict[str, Any] = {}

    async def handler(request: web.Request) -> web.Response:
        captured["auth"] = request.headers.get("Authorization")
        captured["ua"] = request.headers.get("User-Agent")
        return web.json_response({"ok": True})

    runner, base_url = await _start_server(handler)
    try:
        store = MemoryTokenStore()
        await store.save(_make_bundle())
        auth = _FakeAuth(store, token="TKN-XYZ")
        client, session = await _make_http_client(base_url, auth)
        try:
            await client.transport.request("GET", "/x")
            assert captured["auth"] == "Bearer TKN-XYZ"
            assert captured["ua"] is not None
        finally:
            await session.close()
    finally:
        await runner.cleanup()


# ---------------------------------------------------------------------------
# Client hardening tests
# ---------------------------------------------------------------------------


async def test_url_encoding_special_chars(client_with_fake_transport):
    """User-supplied serial with special chars must be URL-encoded."""
    client, fake = client_with_fake_transport
    fake.queue({"serialNumber": "S/1"})
    await client.charger_overview("S/1")
    call = fake.calls[0]
    assert "%2F" in call["path"]
    assert "S/1" not in call["path"]


async def test_closed_client_raises():
    """After close(), public methods must raise RatioApiError."""
    bundle = _make_bundle()
    store = MemoryTokenStore()
    await store.save(bundle)
    async with aiohttp.ClientSession() as session:
        client = RatioClient(token_store=store, session=session)
        await client.close()
        with pytest.raises(RatioApiError, match="closed"):
            await client.chargers()


async def test_ensure_list_unexpected_type_raises():
    """_ensure_list with non-list/non-dict/non-None raises RatioApiError."""
    from aioratio.client import _ensure_list

    with pytest.raises(RatioApiError, match="unexpected response type"):
        _ensure_list("not-a-list-or-dict", "key")


async def test_ensure_list_none_returns_empty():
    """_ensure_list with None returns []."""
    from aioratio.client import _ensure_list

    assert _ensure_list(None, "key") == []


# ---------------------------------------------------------------------------
# set_solar_settings / grant_upgrade_permission
# ---------------------------------------------------------------------------


async def test_set_solar_settings_put_body_dict(client_with_fake_transport):
    client, fake = client_with_fake_transport
    fake.queue(None)
    payload = {"sunOnDelayMinutes": {"value": 5}}
    await client.set_solar_settings("S1", payload)
    call = fake.calls[0]
    assert call["method"] == "PUT"
    assert call["path"] == "/users/user-abc/chargers/S1/settings"
    assert call["params"] == {"id": "solar"}
    body = call["json"]
    assert "transactionId" in body and len(body["transactionId"]) == 16
    int(body["transactionId"], 16)
    assert body["solarSettings"] == payload


async def test_set_solar_settings_put_body_model(client_with_fake_transport):
    from aioratio.models import SolarSettings, UpperLowerLimitSetting

    client, fake = client_with_fake_transport
    fake.queue(None)
    settings = SolarSettings(
        sun_on_delay_minutes=UpperLowerLimitSetting(value=5.0, lower=1.0, upper=30.0),
    )
    await client.set_solar_settings("S1", settings)
    inner = fake.calls[0]["json"]["solarSettings"]
    assert "sunOnDelayMinutes" in inner
    assert "sun_on_delay_minutes" not in inner
    assert inner["sunOnDelayMinutes"]["value"] == 5.0


async def test_set_solar_settings_url_encodes_serial(client_with_fake_transport):
    client, fake = client_with_fake_transport
    fake.queue(None)
    await client.set_solar_settings("S/1 X", {"foo": "bar"})
    assert fake.calls[0]["path"] == "/users/user-abc/chargers/S%2F1%20X/settings"


async def test_grant_upgrade_permission_happy_path(client_with_fake_transport):
    client, fake = client_with_fake_transport
    fake.queue(None)
    await client.grant_upgrade_permission("SER1", ["job-1", "job-2"])
    call = fake.calls[0]
    assert call["method"] == "PUT"
    assert call["path"] == "/users/user-abc/chargers/SER1/command"
    assert call["params"] == {"id": "grant-upgrade-permission"}
    body = call["json"]
    assert body["command"] == "grant-upgrade-permission"
    assert isinstance(body["transactionId"], str)
    assert len(body["transactionId"]) == 16
    int(body["transactionId"], 16)
    assert body["grantUpgradePermissionParameters"] == {
        "firmwareUpdateJobIds": ["job-1", "job-2"],
    }


async def test_grant_upgrade_permission_empty_list_raises(client_with_fake_transport):
    client, _fake = client_with_fake_transport
    with pytest.raises(ValueError, match="firmware_update_job_ids"):
        await client.grant_upgrade_permission("SER1", [])
