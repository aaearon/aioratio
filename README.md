# aioratio

Async Python client for the [Ratio](https://ratio.energy/) EV Charging cloud API.

[![PyPI](https://img.shields.io/pypi/v/aioratio.svg)](https://pypi.org/project/aioratio/)
[![Python](https://img.shields.io/pypi/pyversions/aioratio.svg)](https://pypi.org/project/aioratio/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## What this is

A standalone, async, dependency-light Python client for the cloud API behind
the official Ratio EV Charging mobile app. Authenticates via AWS Cognito
(USER_SRP_AUTH + DEVICE_SRP_AUTH), persists device and refresh tokens,
exposes typed dataclass models for chargers, sessions, settings, and
vehicles. Designed to be embedded in Home Assistant integrations or used
directly from scripts.

This is an unofficial library. Not affiliated with Ratio.

## Why a separate library

The previous community Home Assistant integration ([RowanRamasray/Ratio_Ev_Charger](https://github.com/RowanRamasray/Ratio_Ev_Charger)) bundled `boto3` and `warrant` inside the custom component, fused protocol logic with `homeassistant.core`, and only covered part of the API surface. `aioratio` extracts the protocol layer into a pure-async, HA-free library so any Python consumer can use it and the HA integration becomes a thin wrapper.

## Install

```bash
pip install aioratio
```

Requires Python 3.11+. Only runtime dep is `aiohttp>=3.9`.

## Quick start

```python
import asyncio
import aiohttp
from aioratio import RatioClient, JsonFileTokenStore

async def main() -> None:
    async with aiohttp.ClientSession() as session:
        client = RatioClient(
            email="you@example.com",
            password="...",
            token_store=JsonFileTokenStore("ratio-tokens.json"),
            session=session,
        )
        async with client:
            chargers = await client.chargers_overview()
            for c in chargers:
                print(c.serial_number, c.cloud_connection_state)

            await client.start_charge(chargers[0].serial_number,
                                      vehicle_id="<your-vehicle-id>")

asyncio.run(main())
```

The token store persists access/refresh tokens **and** Cognito device
metadata (DeviceKey, DeviceGroupKey, DevicePassword) so subsequent runs
go through the DEVICE_SRP_AUTH fast path without re-prompting.

## Public API

`RatioClient` is the entry point. Construct with email + password (and
optionally a `TokenStore`), use as an async context manager.

| Method | Returns | Notes |
|---|---|---|
| `login()` | `None` | Force a fresh login. Idempotent. |
| `user_id()` | `str` | Cognito `sub` claim from the IdToken. |
| `chargers()` | `list[Charger]` | Bare charger registry. |
| `chargers_overview()` | `list[ChargerOverview]` | Aggregate status of all chargers (single call). |
| `charger_overview(serial)` | `ChargerOverview` | Single-charger full state. |
| `start_charge(serial, vehicle_id=None)` | `None` | `vehicle_id` is optional but recommended; if omitted, the client sends an empty `startCommandParameters` object. |
| `stop_charge(serial)` | `None` | |
| `user_settings(serial)` | `UserSettings` | |
| `set_user_settings(serial, settings)` | `None` | Accepts `UserSettings` dataclass (recommended) or a pre-formed camelCase dict. |
| `charge_schedule(serial)` | `ChargeSchedule` | |
| `set_charge_schedule(serial, schedule)` | `None` | |
| `solar_settings(serial)` | `SolarSettings` | |
| `set_solar_settings(serial, settings)` | `None` | Accepts `SolarSettings` dataclass (recommended) or a pre-formed camelCase dict. |
| `grant_upgrade_permission(serial, firmware_update_job_ids)` | `None` | Approve queued firmware update jobs by id. Raises `ValueError` if the list is empty. |
| `session_history(...)` | `SessionHistoryPage` | Paginated; pass `next_token` to continue. |
| `vehicles()` | `list[Vehicle]` | |
| `add_vehicle(vehicle)` | `Vehicle` | |
| `remove_vehicle(vehicle_id)` | `None` | |

Errors:

- `RatioAuthError` -- credentials invalid, refresh expired, unsupported Cognito challenge.
- `RatioApiError` -- non-2xx response from the REST API. Also raised when calling methods on a closed client.
- `RatioRateLimitError` -- HTTP 429.
- `RatioConnectionError` -- network/timeout failure.
- `RatioError` -- common base.

All public methods raise `RatioApiError("client is closed")` after `close()` has been called. User-supplied path segments (serial numbers, user IDs, vehicle IDs) are percent-encoded to prevent path traversal.

Token storage:

- `JsonFileTokenStore(path)` — atomic writes, mode 0o600.
- `MemoryTokenStore()` — for tests / ephemeral CLI use.
- `TokenStore` (ABC) — implement `load()` / `save()` / `clear()` to plug into other backends (e.g. HA's `Store` helper).

## Architecture

```
+-------------------+       +-----------------+       +------------+
|   RatioClient     |  -->  | _CloudTransport |  -->  | aiohttp    |
|  (public façade)  |       |  (private)      |       +------------+
+-------------------+       +-----------------+
        |                           |
        |                           v 401 retry once via auth
        v
+-------------------+       +-----------------+
| CognitoSrpAuth    |  -->  | TokenStore      |
| USER_SRP +        |       | (Memory/JSON)   |
| DEVICE_SRP +      |       +-----------------+
| REFRESH_TOKEN     |
+-------------------+
        |
        v
+-------------------+
| srp.py            |
| Cognito SRP-6a    |
+-------------------+
```

Files under `src/aioratio/`:

- `client.py` — public `RatioClient` async context manager.
- `_transport.py` -- private aiohttp transport. 401 -> invalidate_access_token -> retry once.
- `auth.py` -- `CognitoSrpAuth` driver: USER_SRP first-login, ConfirmDevice + UpdateDeviceStatus, REFRESH_TOKEN_AUTH (with rotation handling), DEVICE_SRP_AUTH second-login. Refresh serialised via `asyncio.Lock`. Accepts a `timeout` parameter (default 30s) for Cognito HTTP calls. Exposes `invalidate_access_token()` for callers to force a refresh on the next access.
- `srp.py` — pure-Python Cognito SRP-6a (3072-bit MODP, `Caldera Derived Key` HKDF, Java-style timestamp). Uses Java `BigInteger.toByteArray()` (`padHex`) semantics throughout — variable length with `0x00` sign byte when high bit set. Both `UserSrp` and `DeviceSrp` variants.
- `token_store.py` — `TokenBundle` dataclass + `TokenStore` ABC + `MemoryTokenStore` + `JsonFileTokenStore` (atomic write).
- `models/` — dataclasses derived from APK DTOs: `Charger`, `ChargerOverview`, `ChargerStatus`, `UserSettings`, `ChargeSchedule`, `SolarSettings`, `Session`, `SessionHistoryPage`, `Vehicle`, plus nested types. All have a `from_dict()` classmethod tolerant of unknown fields.
- `exceptions.py`, `const.py`.

## Cognito specifics (notes for maintainers and LLMs)

The Ratio user pool uses `USER_SRP_AUTH` with no client secret. Pool `eu-west-1_mH4sFjLoF`, client `78cs05mc0hc5ibqv1tui22n962`, region `eu-west-1`, API base `https://8q4y72fwo3.execute-api.eu-west-1.amazonaws.com/prod` — all centralised in `const.py`.

Confirmed-live behaviours:

- First login flow: `InitiateAuth(USER_SRP_AUTH)` → `RespondToAuthChallenge(PASSWORD_VERIFIER)` → tokens + `NewDeviceMetadata` → `ConfirmDevice` (with our generated device verifier) → `UpdateDeviceStatus(remembered)`.
- Subsequent login on a remembered device: PASSWORD_VERIFIER → `DEVICE_SRP_AUTH` → `DEVICE_PASSWORD_VERIFIER` → tokens.
- `REFRESH_TOKEN_AUTH` does **not** rotate the refresh token (server keeps the existing one; library handles either case).
- `compute_x` uses the format `poolName + username + ":" + password` (no colon between pool and user). All `salt`, `verifier`, `A`, `B`, `u`, `S` use Java `BigInteger.toByteArray` byte semantics, not fixed-length padding.
- `start-charge` requires `startCommandParameters` to always be present in the body (empty object is accepted; missing object is not).

## Development

```bash
git clone https://github.com/aaearon/aioratio
cd aioratio
uv venv --python 3.11        # or python3.11 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/pytest -q
```

Tests are run with ``pytest``. Live smoke against a real account
lives in `scripts/smoke.py` (reads creds from `../.env`).

The SRP vector tests are intentionally self-consistent and do not catch
encoding bugs against Cognito — see commit `0283fb5` for two real bugs that
slipped past them. Live smoke is the source of truth.

## Status

Early. Used in production by [`home-assistant-ratio`](https://github.com/aaearon/home-assistant-ratio). Field nullability across some models is best-effort against the decompiled APK; flag mismatches as issues.

- **`set_solar_settings` HTTP 502** ([#9](https://github.com/aaearon/aioratio/issues/9)): `UpperLowerLimitSetting.to_dict()` now echoes back the full raw GET response shape (including `isChangeAllowed`, `lowerLimit`, `upperLimit`) instead of emitting only `{"value": N}`. This is the most likely fix; if the 502 persists, the next step is mitmproxy capture of the app's actual PUT payload.
- `ScheduleSlot` and `ChargeSchedule` now have explicit `to_dict()` methods for controlled serialisation.

## License

MIT.

## Disclaimer

Unofficial. Reverse-engineered from the public Android APK and observed
Cognito traffic. Use at your own risk; the API is not contractually
stable. No affiliation with Ratio.
