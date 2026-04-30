"""Live smoke test against the user's real Ratio account.

Reads credentials from ../.env. Persists tokens to ./smoke.tokens.json
(in cleartext — gitignored). Run multiple times to exercise refresh
and DEVICE_SRP_AUTH paths.

Usage:
    python3 scripts/smoke.py [step]
        step = all | login | overview | refresh | restart | rotation
"""
from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

import aiohttp

from aioratio import RatioClient
from aioratio.auth import CognitoSrpAuth
from aioratio.token_store import JsonFileTokenStore


REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = REPO_ROOT.parent / ".env"
TOKENS_PATH = REPO_ROOT / "smoke.tokens.json"


def load_env() -> tuple[str, str]:
    text = ENV_PATH.read_text()
    env: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip()
    return env["RATIO_USERNAME"], env["RATIO_PASSWORD"]


def redact(s: str | None, keep: int = 4) -> str:
    if not s:
        return "<none>"
    if len(s) <= keep * 2:
        return "***"
    return f"{s[:keep]}...{s[-keep:]}"


async def show_bundle(store: JsonFileTokenStore, label: str) -> None:
    b = await store.load()
    if b is None:
        print(f"  [{label}] bundle: None")
        return
    print(
        f"  [{label}] access={redact(b.access_token)} "
        f"refresh={redact(b.refresh_token)} "
        f"device_key={redact(b.device_key)} "
        f"device_password={redact(b.device_password)} "
        f"expires_in={int(b.expires_at - time.time())}s"
    )


async def step_login(email: str, password: str) -> None:
    """Step 1: First login from clean state. Removes any existing tokens."""
    print("\n=== STEP 1: First login (clean state) ===")
    if TOKENS_PATH.exists():
        TOKENS_PATH.unlink()
        print("  removed existing token file")
    store = JsonFileTokenStore(TOKENS_PATH)
    async with aiohttp.ClientSession() as s:
        client = RatioClient(email=email, password=password, token_store=store, session=s)
        await client.login()
        print("  login OK")
        await show_bundle(store, "post-login")


async def step_overview(email: str, password: str) -> None:
    """Step 2: chargers_overview returns expected data."""
    print("\n=== STEP 2: chargers_overview ===")
    store = JsonFileTokenStore(TOKENS_PATH)
    async with aiohttp.ClientSession() as s:
        client = RatioClient(email=email, password=password, token_store=store, session=s)
        overviews = await client.chargers_overview()
        print(f"  got {len(overviews)} charger(s)")
        for o in overviews:
            print(f"    serial={redact(o.serial_number, 6)} status={getattr(o, 'status', None)}")
            # Dump full structure (sanitised) for fixture capture
            from dataclasses import asdict
            print(f"    raw fields: {list(asdict(o).keys())}")


async def step_refresh(email: str, password: str) -> None:
    """Step 3: force-expire access token, observe refresh succeeds."""
    print("\n=== STEP 3: refresh round-trip ===")
    store = JsonFileTokenStore(TOKENS_PATH)
    bundle = await store.load()
    if bundle is None:
        print("  no bundle — run login first")
        return
    old_access = bundle.access_token
    old_refresh = bundle.refresh_token
    # Force-expire
    bundle.expires_at = 0
    await store.save(bundle)
    print(f"  forced expiry; old_access={redact(old_access)}")
    async with aiohttp.ClientSession() as s:
        client = RatioClient(email=email, password=password, token_store=store, session=s)
        overviews = await client.chargers_overview()
        print(f"  request after expiry succeeded, {len(overviews)} chargers")
    new = await store.load()
    assert new is not None
    print(f"  new_access={redact(new.access_token)}")
    assert new.access_token != old_access, "access token did not rotate"
    print("  access token rotated OK")
    rotated = new.refresh_token != old_refresh
    print(f"  refresh token rotation: {'YES' if rotated else 'NO (kept old)'}")


async def step_restart(email: str, password: str) -> None:
    """Step 4: drop in-memory state, reload from store, observe DEVICE_SRP_AUTH path on next login."""
    print("\n=== STEP 4: restart simulation (DEVICE_SRP_AUTH path) ===")
    store = JsonFileTokenStore(TOKENS_PATH)
    bundle = await store.load()
    if bundle is None or bundle.device_key is None:
        print("  no device bundle — run login first")
        return
    # Force a full login (not refresh) by using the auth driver directly
    print(f"  using device_key={redact(bundle.device_key)}")
    # Patch _cognito_call to log challenge progression
    challenges: list[str] = []

    async with aiohttp.ClientSession() as s:
        auth = CognitoSrpAuth(
            email=email, password=password, token_store=store, session=s,
        )
        orig = auth._cognito_call

        async def trace(target, body):
            r = await orig(target, body)
            cn = r.get("ChallengeName")
            if cn:
                challenges.append(cn)
                print(f"    challenge: {cn}")
            elif "AuthenticationResult" in r:
                print("    AuthenticationResult received")
            return r

        auth._cognito_call = trace  # type: ignore[assignment]
        await auth.login()
    print(f"  challenge sequence: {challenges}")
    if "DEVICE_SRP_AUTH" in challenges and "DEVICE_PASSWORD_VERIFIER" in challenges:
        print("  DEVICE_SRP_AUTH path exercised OK")
    else:
        print("  WARNING: device path not exercised — check device persistence")


async def step_commands(email: str, password: str) -> None:
    """Step 5: start_charge + stop_charge against real charger (car must NOT be plugged)."""
    print("\n=== STEP 5: start/stop charge commands ===")
    store = JsonFileTokenStore(TOKENS_PATH)
    async with aiohttp.ClientSession() as s:
        client = RatioClient(email=email, password=password, token_store=store, session=s)
        overviews = await client.chargers_overview()
        if not overviews:
            print("  no chargers")
            return
        serial = overviews[0].serial_number
        print(f"  using serial={redact(serial, 6)}")
        try:
            print("  -> start_charge (no vehicle_id)")
            await client.start_charge(serial)
            print("  start_charge accepted")
        except Exception as e:
            print(f"  start_charge raised: {type(e).__name__}: {e}")
        await asyncio.sleep(2)
        try:
            print("  -> stop_charge")
            await client.stop_charge(serial)
            print("  stop_charge accepted")
        except Exception as e:
            print(f"  stop_charge raised: {type(e).__name__}: {e}")


async def main() -> None:
    step = sys.argv[1] if len(sys.argv) > 1 else "all"
    email, password = load_env()
    print(f"User: {email}")

    if step in ("all", "login"):
        await step_login(email, password)
    if step in ("all", "overview"):
        await step_overview(email, password)
    if step in ("all", "refresh"):
        await step_refresh(email, password)
    if step in ("all", "restart"):
        await step_restart(email, password)
    if step in ("all", "commands"):
        await step_commands(email, password)


if __name__ == "__main__":
    asyncio.run(main())
