"""Tests for RatioClient and the private _CloudTransport."""

from __future__ import annotations

import base64
import json
import re
import time
from datetime import UTC, datetime
from typing import Any, cast

import aiohttp
import pytest
from aiohttp import web

from aioratio.auth import CognitoSrpAuth
from aioratio.client import RatioClient
from aioratio.exceptions import (
    RatioApiError,
    RatioAuthError,
    RatioConnectionError,
    RatioRateLimitError,
)
from aioratio.models import (
    ChargerOverview,
    ChargeSchedule,
    ChargeScheduleUpdate,
    CpmsConfig,
    DelayedStartSetting,
    OcppSettingsUpdate,
    ScheduleSlot,
    SolarSettingsUpdate,
    UserSettings,
    Vehicle,
)
from aioratio.token_store import MemoryTokenStore, TokenBundle

# ---------------------------------------------------------------------------
# Fixtures / fakes
# ---------------------------------------------------------------------------


def _make_id_token(sub: str = "user-abc") -> str:
    header = base64.urlsafe_b64encode(b'{"alg":"none"}').rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(json.dumps({"sub": sub}).encode()).rstrip(b"=").decode()
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
        self.calls.append({"method": method, "path": path, "params": params, "json": json})
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
    client._transport = cast(Any, fake)
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

        assert client._auth is not None
        client._auth.get_access_token = cast(Any, _fake_get_access_token)
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
    # "Smart" is a real ChargingMode value (Basic/Smart/SmartSolar/PureSolar).
    settings = UserSettings.from_dict(
        {"chargingMode": {"value": "Smart", "allowedValues": ["Basic", "Smart"]}}
    )
    fake.calls.clear()
    fake.queue(None)
    await client.set_user_settings("S1", settings)
    call = fake.calls[0]
    assert call["method"] == "PUT"
    body = call["json"]
    assert "transactionId" in body
    inner = body["userSettings"]
    assert "chargingMode" in inner
    assert "charging_mode" not in inner
    # SetUserSettings types chargingMode as a nullable String, not a value object.
    assert inner["chargingMode"] == "Smart"
    # Read-only metadata (allowedValues, lower, upper) must not appear in a PUT body
    assert inner == {"chargingMode": "Smart"}


_EMPTY_WEEK = {
    "monday": [],
    "tuesday": [],
    "wednesday": [],
    "thursday": [],
    "friday": [],
    "saturday": [],
    "sunday": [],
}


def _assert_transaction_id(body: dict) -> None:
    """``_new_transaction_id()`` is ``uuid.uuid4().hex[:16]``."""
    assert re.fullmatch(r"[0-9a-f]{16}", body["transactionId"])


async def test_set_charge_schedule_week_plan_exact_body(client_with_fake_transport):
    """Mirrors ``WeekPlanViewModel.java:99`` (mask 10): enabled + scheduleType +
    weekSchedule, and nothing else.
    """
    client, fake = client_with_fake_transport
    fake.queue(None)
    update = ChargeScheduleUpdate(
        enabled=True,
        schedule_type="WeekSchedule",
        slots=[ScheduleSlot(start="22:00", end="06:00", days=["monday", "tuesday"])],
    )
    await client.set_charge_schedule("S1", update)

    call = fake.calls[0]
    assert call["method"] == "PUT"
    assert call["path"] == "/users/user-abc/chargers/S1/settings"
    assert call["params"] == {"id": "chargeSchedule"}
    body = call["json"]
    _assert_transaction_id(body)
    assert set(body) == {"transactionId", "chargeScheduleSettings"}
    slot = {"beginTimeHour": 22, "beginTimeMinute": 0, "endTimeHour": 6, "endTimeMinute": 0}
    assert body["chargeScheduleSettings"] == {
        "enabled": True,
        "scheduleType": "WeekSchedule",
        "weekSchedule": {**_EMPTY_WEEK, "monday": [slot], "tuesday": [slot]},
    }


async def test_set_charge_schedule_delayed_start_exact_body(client_with_fake_transport):
    """Mirrors ``DelayedStartViewModel.java:125`` (mask 18) — no ``weekSchedule``,
    so the stored week plan is left intact.
    """
    client, fake = client_with_fake_transport
    fake.queue(None)
    await client.set_charge_schedule(
        "S1",
        ChargeScheduleUpdate(
            enabled=True,
            schedule_type="DelayedStart",
            delayed_start=DelayedStartSetting(
                begin_time_hour=7, begin_time_minute=0, charging_mode="Smart"
            ),
        ),
    )

    body = fake.calls[0]["json"]
    _assert_transaction_id(body)
    assert set(body) == {"transactionId", "chargeScheduleSettings"}
    assert body["chargeScheduleSettings"] == {
        "enabled": True,
        "scheduleType": "DelayedStart",
        "delayedStart": {"beginTimeHour": 7, "beginTimeMinute": 0, "chargingMode": "Smart"},
    }


async def test_set_charge_schedule_enabled_and_offset_exact_body(client_with_fake_transport):
    """Mirrors ``ChargeScheduleViewModel.java:127`` (mask 24)."""
    client, fake = client_with_fake_transport
    fake.queue(None)
    await client.set_charge_schedule(
        "S1",
        ChargeScheduleUpdate(
            enabled=True,
            randomized_time_offset_enabled=True,
            schedule_type="WeekSchedule",
        ),
    )

    body = fake.calls[0]["json"]
    _assert_transaction_id(body)
    assert body["chargeScheduleSettings"] == {
        "enabled": True,
        "randomizedTimeOffsetEnabled": True,
        "scheduleType": "WeekSchedule",
    }


async def test_set_charge_schedule_rejects_get_model(client_with_fake_transport):
    """Regression: ``_coerce_body()`` falls back to ``dataclasses.asdict()`` for
    any object without ``to_dict()``, so deleting ``ChargeSchedule.to_dict()``
    alone would silently produce a worse body. The GET model must be refused
    before any request is made.
    """
    client, fake = client_with_fake_transport
    schedule = ChargeSchedule(
        enabled=True,
        schedule_type="WeekSchedule",
        slots=[ScheduleSlot(start="22:00", end="06:00", days=["monday"])],
    )
    with pytest.raises(TypeError, match="ChargeScheduleUpdate"):
        await client.set_charge_schedule("S1", schedule)
    assert fake.calls == []


async def test_charge_schedule_get_and_set(client_with_fake_transport):
    client, fake = client_with_fake_transport
    fake.queue({"enabled": True, "scheduleType": "WeekSchedule", "slots": []})
    sched = await client.charge_schedule("S1")
    assert isinstance(sched, ChargeSchedule)
    assert sched.enabled is True
    assert sched.schedule_type == "WeekSchedule"
    assert fake.calls[-1]["params"] == {"id": "chargeSchedule"}

    fake.queue(None)
    await client.set_charge_schedule("S1", {"enabled": False})
    last = fake.calls[-1]
    assert last["method"] == "PUT"
    assert last["params"] == {"id": "chargeSchedule"}
    body = last["json"]
    _assert_transaction_id(body)
    assert body["chargeScheduleSettings"] == {"enabled": False}


async def test_set_solar_settings_update_exact_body(client_with_fake_transport):
    """``SetSolarSettings`` takes bare integers; only the changed key is sent."""
    client, fake = client_with_fake_transport
    fake.queue(None)
    await client.set_solar_settings("S1", SolarSettingsUpdate(pure_solar_starting_current=6))

    call = fake.calls[0]
    assert call["method"] == "PUT"
    assert call["params"] == {"id": "solar"}
    body = call["json"]
    _assert_transaction_id(body)
    assert set(body) == {"transactionId", "solarSettings"}
    assert body["solarSettings"] == {"pureSolarStartingCurrent": 6}


async def test_set_ocpp_settings_update_exact_body(client_with_fake_transport):
    """``SetInstallerOcppSettings``: enabled/cpms/chargePointIdentifier, all optional."""
    client, fake = client_with_fake_transport
    fake.queue(None)
    await client.set_ocpp_settings(
        "S1",
        OcppSettingsUpdate(
            enabled=True,
            cpms=CpmsConfig(central_system="Ratio", url="wss://ocpp.example/v16"),
        ),
    )

    call = fake.calls[0]
    assert call["params"] == {"id": "installerOcpp"}
    body = call["json"]
    _assert_transaction_id(body)
    assert set(body) == {"transactionId", "installerOcppSettings"}
    assert body["installerOcppSettings"] == {
        "enabled": True,
        "cpms": {"centralSystem": "Ratio", "url": "wss://ocpp.example/v16"},
    }


async def test_add_vehicle_body_omits_null_fields(client_with_fake_transport):
    """``Vehicle$$serializer`` marks all four keys optional and the app writes
    under ``explicitNulls=false`` — a POST must not carry explicit nulls.
    """
    client, fake = client_with_fake_transport
    fake.queue({"vehicleId": "v9", "vehicleName": "BMW", "licensePlate": "AB-12-CD"})
    out = await client.add_vehicle(Vehicle(vehicle_name="BMW", license_plate="AB-12-CD"))

    call = fake.calls[0]
    assert call["method"] == "POST"
    assert call["path"] == "/users/user-abc/vehicles"
    assert call["json"] == {"vehicleName": "BMW", "licensePlate": "AB-12-CD"}
    assert out.vehicle_id == "v9"


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
    begin = datetime(2026, 1, 1, tzinfo=UTC)
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


class _FakeAuth(CognitoSrpAuth):
    """Drop-in stand-in for CognitoSrpAuth in transport-level tests."""

    def __init__(self, store, token: str = "TOKEN0") -> None:
        super().__init__(
            email="fake@example.com",
            password="fake",
            token_store=store,
            session=None,
        )
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
    client._auth = auth
    from aioratio._transport import _CloudTransport

    client._transport = _CloudTransport(auth=auth, session=session, base_url=base_url)
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
        transport = _CloudTransport(auth=auth, session=session, base_url="http://127.0.0.1:1")
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
    payload = {"sunOnDelayMinutes": 5}
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
    assert inner["sunOnDelayMinutes"] == 5


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


# ---------------------------------------------------------------------------
# diagnostics / ocpp_settings / set_ocpp_settings / cpms_options
# ---------------------------------------------------------------------------

from aioratio.models import ChargerDiagnostics, InstallerOcppSettings


async def test_diagnostics_get_url_and_parses(client_with_fake_transport):
    client, fake = client_with_fake_transport
    fake.queue(
        {
            "productInformation": {
                "mainController": {"firmwareVersion": "4.0", "serialNumber": "CPC-1"}
            },
            "backendStatus": {"connected": True},
        }
    )
    result = await client.diagnostics("SER1")
    call = fake.calls[0]
    assert call["method"] == "GET"
    assert call["path"] == "/users/user-abc/chargers/SER1/status"
    assert call["params"] == {"id": "diagnostics"}
    assert isinstance(result, ChargerDiagnostics)
    assert result.product_information is not None
    assert result.product_information.main_controller is not None
    assert result.product_information.main_controller.serial_number == "CPC-1"
    assert result.backend_status is not None
    assert result.backend_status.connected is True


async def test_diagnostics_url_encodes_serial(client_with_fake_transport):
    client, fake = client_with_fake_transport
    fake.queue({})
    await client.diagnostics("S/1 X")
    assert fake.calls[0]["path"] == "/users/user-abc/chargers/S%2F1%20X/status"


async def test_diagnostics_none_response_returns_empty(client_with_fake_transport):
    client, fake = client_with_fake_transport
    fake.queue(None)
    result = await client.diagnostics("SER1")
    assert isinstance(result, ChargerDiagnostics)
    assert result.backend_status is None


async def test_ocpp_settings_get_strips_envelope(client_with_fake_transport):
    client, fake = client_with_fake_transport
    fake.queue(
        {
            "installerOcppSettings": {
                "enabled": {"value": True, "isChangeAllowed": True, "changeNotAllowedReason": None},
                "cpms": {
                    "value": {"centralSystem": "Op", "url": "ws://op.com"},
                    "isChangeAllowed": True,
                    "changeNotAllowedReason": None,
                },
                "chargePointIdentifier": {
                    "value": "CP-1",
                    "isChangeAllowed": True,
                    "changeNotAllowedReason": None,
                    "maxLength": 48,
                },
            }
        }
    )
    result = await client.ocpp_settings("SER1")
    call = fake.calls[0]
    assert call["method"] == "GET"
    assert call["path"] == "/users/user-abc/chargers/SER1/settings"
    assert call["params"] == {"id": "installerOcpp"}
    assert isinstance(result, InstallerOcppSettings)
    assert result.enabled is True
    assert result.cpms is not None
    assert result.cpms.url == "ws://op.com"
    assert result.charge_point_identifier == "CP-1"
    assert result.charge_point_identifier_max_length == 48


async def test_set_ocpp_settings_put_body_flat(client_with_fake_transport):
    client, fake = client_with_fake_transport
    fake.queue(None)
    settings = InstallerOcppSettings(
        enabled=True,
        cpms=CpmsConfig(central_system="Op", url="ws://op.com"),
        charge_point_identifier="NEW-CP",
    )
    await client.set_ocpp_settings("SER1", settings)
    call = fake.calls[0]
    assert call["method"] == "PUT"
    assert call["path"] == "/users/user-abc/chargers/SER1/settings"
    assert call["params"] == {"id": "installerOcpp"}
    body = call["json"]
    assert "transactionId" in body
    inner = body["installerOcppSettings"]
    assert inner == {
        "enabled": True,
        "cpms": {"centralSystem": "Op", "url": "ws://op.com"},
        "chargePointIdentifier": "NEW-CP",
    }
    assert "enabledStatus" not in inner
    assert "isChangeAllowed" not in inner


async def test_set_ocpp_settings_partial_body(client_with_fake_transport):
    client, fake = client_with_fake_transport
    fake.queue(None)
    settings = InstallerOcppSettings(charge_point_identifier="ONLY-CPID")
    await client.set_ocpp_settings("SER1", settings)
    inner = fake.calls[0]["json"]["installerOcppSettings"]
    assert inner == {"chargePointIdentifier": "ONLY-CPID"}


async def test_cpms_options_lists(client_with_fake_transport):
    client, fake = client_with_fake_transport
    fake.queue(
        {
            "cpmsList": [
                {"name": "Op A", "url": "ws://a.example.com", "cpidType": "EV_NETWORK"},
                {"name": "Op B", "url": "ws://b.example.com", "cpidType": "EV_NETWORK"},
            ]
        }
    )
    result = await client.cpms_options("SER1")
    call = fake.calls[0]
    assert call["method"] == "GET"
    assert "charge-point-management-systems" in call["path"]
    assert len(result) == 2
    assert all(isinstance(c, CpmsConfig) for c in result)
    assert result[0].central_system == "Op A"
    assert result[1].url == "ws://b.example.com"


async def test_cpms_options_empty_response_returns_empty_list(client_with_fake_transport):
    client, fake = client_with_fake_transport
    fake.queue({"cpmsList": []})
    result = await client.cpms_options("SER1")
    assert result == []


async def test_cpms_options_none_response_returns_empty_list(client_with_fake_transport):
    client, fake = client_with_fake_transport
    fake.queue(None)
    result = await client.cpms_options("SER1")
    assert result == []


async def test_cpms_options_403_returns_empty_list(client_with_fake_transport):
    from aioratio.exceptions import RatioApiError

    client, fake = client_with_fake_transport
    fake.queue(RatioApiError("HTTP 403", status=403))
    result = await client.cpms_options("SER1")
    assert result == []


async def test_cpms_options_404_returns_empty_list(client_with_fake_transport):
    from aioratio.exceptions import RatioApiError

    client, fake = client_with_fake_transport
    fake.queue(RatioApiError("HTTP 404", status=404))
    result = await client.cpms_options("SER1")
    assert result == []


async def test_cpms_options_500_propagates(client_with_fake_transport):
    import pytest

    from aioratio.exceptions import RatioApiError

    client, fake = client_with_fake_transport
    fake.queue(RatioApiError("HTTP 500", status=500))
    with pytest.raises(RatioApiError):
        await client.cpms_options("SER1")


async def test_cpms_options_unknown_status_propagates(client_with_fake_transport):
    """Errors without a status code (legacy/unknown) should not be silently swallowed."""
    import pytest

    from aioratio.exceptions import RatioApiError

    client, fake = client_with_fake_transport
    fake.queue(RatioApiError("legacy error without status"))
    with pytest.raises(RatioApiError):
        await client.cpms_options("SER1")


# ---------------------------------------------------------------------------
# set_user_settings PUT wire contract
#
# SetUserSettings$$serializer.java descriptor (verbatim):
#   addElement("startMode", true)              -> nullable String
#   addElement("cableSettings", true)          -> nullable String
#   addElement("minimumChargingCurrent", true) -> nullable Int
#   addElement("maximumChargingCurrent", true) -> nullable Int
#   addElement("chargingMode", true)           -> nullable String
#
# ChargerSettingsCloudDataSource.setUserIntSetting() constructs
#   new SetUserSettings(null, null, null, boxInt(i), null, 23, null)
# and core/JsonKt.java sets explicitNulls=false, so the real wire body is
#   {"transactionId": "...", "userSettings": {"maximumChargingCurrent": 16}}
# ---------------------------------------------------------------------------

_GET_USER_SETTINGS_PAYLOAD: dict[str, Any] = {
    "cableSettings": {
        "value": "LockAutomatically",
        "isChangeAllowed": True,
        "allowedValues": ["LockAlways", "LockWhenCarConnected", "LockAutomatically"],
    },
    "chargingMode": {
        "value": "SmartSolar",
        "isChangeAllowed": True,
        "allowedValues": ["Basic", "Smart", "SmartSolar", "PureSolar"],
    },
    "maximumChargingCurrent": {
        "isChangeAllowed": True,
        "lowerLimit": 6,
        "upperLimit": 32,
        "value": 16,
    },
    "minimumChargingCurrent": {
        "isChangeAllowed": True,
        "lowerLimit": 6,
        "upperLimit": 16,
        "value": 6,
    },
    "startMode": {
        "value": "Auto",
        "isChangeAllowed": True,
        "allowedValues": ["Auto", "Manual"],
    },
}


async def test_set_user_settings_sparse_max_current_body(client_with_fake_transport):
    """Only max current populated -> the body carries exactly that one key."""
    from aioratio.models import UpperLowerLimitSetting

    client, fake = client_with_fake_transport
    fake.queue(None)
    settings = UserSettings(maximum_charging_current=UpperLowerLimitSetting(value=6))
    await client.set_user_settings("S1", settings)

    call = fake.calls[0]
    assert call["method"] == "PUT"
    assert call["params"] == {"id": "user"}
    body = call["json"]
    assert set(body) == {"transactionId", "userSettings"}
    assert isinstance(body["transactionId"], str)
    assert body["userSettings"] == {"maximumChargingCurrent": 6}


async def test_set_user_settings_max_current_does_not_resend_cable_settings_object(
    client_with_fake_transport,
):
    """Regression: HTTP 400 'Changing setting "cableSettings" ... is out of range'.

    A UserSettings loaded from the GET response and mutated to change only the
    maximum charging current must never PUT ``cableSettings`` as a nested
    ``{"value": ...}`` object — the server rejects the whole request.
    """
    client, fake = client_with_fake_transport
    fake.queue(None)
    settings = UserSettings.from_dict(_GET_USER_SETTINGS_PAYLOAD)
    assert settings.maximum_charging_current is not None
    settings.maximum_charging_current.value = 6

    await client.set_user_settings("S1", settings)

    inner = fake.calls[0]["json"]["userSettings"]
    assert not isinstance(inner.get("cableSettings"), dict), (
        f"cableSettings must not be a nested object in a PUT body: {inner.get('cableSettings')!r}"
    )
    assert inner["maximumChargingCurrent"] == 6
    for key, value in inner.items():
        assert not isinstance(value, dict), f"{key} must be a bare scalar, got {value!r}"


async def test_set_user_settings_put_body_never_carries_read_only_metadata(
    client_with_fake_transport,
):
    client, fake = client_with_fake_transport
    fake.queue(None)
    settings = UserSettings.from_dict(_GET_USER_SETTINGS_PAYLOAD)
    await client.set_user_settings("S1", settings)

    inner = fake.calls[0]["json"]["userSettings"]
    serialised = json.dumps(inner)
    for meta in ("isChangeAllowed", "allowedValues", "lowerLimit", "upperLimit"):
        assert meta not in serialised, f"{meta} is GET-only metadata, not a PUT field"
    assert set(inner) <= {
        "startMode",
        "cableSettings",
        "minimumChargingCurrent",
        "maximumChargingCurrent",
        "chargingMode",
    }


async def test_set_user_settings_accepts_sparse_update_model(client_with_fake_transport):
    """UserSettingsUpdate expresses "change only this key" — the app's shape."""
    from aioratio.models import UserSettingsUpdate

    client, fake = client_with_fake_transport
    fake.queue(None)
    await client.set_user_settings("S1", UserSettingsUpdate(maximum_charging_current=16))

    call = fake.calls[0]
    assert call["method"] == "PUT"
    assert call["params"] == {"id": "user"}
    body = call["json"]
    assert set(body) == {"transactionId", "userSettings"}
    assert re.fullmatch(r"[0-9a-f]{16}", body["transactionId"])
    assert body["userSettings"] == {"maximumChargingCurrent": 16}
