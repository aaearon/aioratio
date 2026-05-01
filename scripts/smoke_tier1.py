"""Live smoke for Tier 1 additions: set_solar_settings round-trip,
grant_upgrade_permission availability inspection.

Reads credentials from ../.env and tokens from ./smoke.tokens.json
(reuse existing smoke.py login state).
"""
from __future__ import annotations

import asyncio
import dataclasses
from pathlib import Path

import aiohttp

from aioratio import RatioClient
from aioratio.token_store import JsonFileTokenStore


REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = REPO_ROOT.parent / ".env"
TOKENS_PATH = REPO_ROOT / "smoke.tokens.json"


def load_env() -> tuple[str, str]:
    env: dict[str, str] = {}
    for line in ENV_PATH.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip()
    return env["RATIO_USERNAME"], env["RATIO_PASSWORD"]


async def main() -> None:
    email, password = load_env()
    store = JsonFileTokenStore(TOKENS_PATH)

    async with aiohttp.ClientSession() as s:
        client = RatioClient(email=email, password=password, token_store=store, session=s)

        print("=== chargers_overview ===")
        overviews = await client.chargers_overview()
        if not overviews:
            print("no chargers; aborting")
            return
        serial = overviews[0].serial_number
        print(f"using serial={serial[:6]}...{serial[-4:]}")

        # --- Solar settings round-trip ---
        print("\n=== solar_settings GET ===")
        solar = await client.solar_settings(serial)
        print(f"solar fields: {[f.name for f in dataclasses.fields(solar)]}")
        sun_off = solar.sun_off_delay_minutes
        print(f"current sun_off_delay_minutes={sun_off}")

        if sun_off is not None and sun_off.value is not None:
            original = sun_off.value
            new_value = original + 1 if original < (sun_off.upper or 9999) else original - 1
            print(f"\n=== set_solar_settings (sun_off_delay_minutes {original} -> {new_value}) ===")
            modified = dataclasses.replace(
                solar,
                sun_off_delay_minutes=dataclasses.replace(sun_off, value=new_value),
            )
            try:
                await client.set_solar_settings(serial, modified)
                print("PUT accepted")
            except Exception as e:
                print(f"PUT raised: {type(e).__name__}: {e}")
                return

            print("\n=== solar_settings GET (verify) ===")
            verify = await client.solar_settings(serial)
            got = verify.sun_off_delay_minutes.value if verify.sun_off_delay_minutes else None
            print(f"sun_off_delay_minutes={got} (expected {new_value})")

            print(f"\n=== restore original value ({original}) ===")
            restored = dataclasses.replace(solar, sun_off_delay_minutes=sun_off)
            await client.set_solar_settings(serial, restored)
            print("restore PUT accepted")
        else:
            print("no sun_off_delay_minutes value to round-trip; skipping write")

        # --- Firmware status / grant_upgrade_permission visibility ---
        print("\n=== firmware status ===")
        ov = overviews[0]
        fws = getattr(ov, "charger_firmware_status", None)
        if fws is None:
            print("no charger_firmware_status on overview")
        else:
            print(f"  is_firmware_update_available={getattr(fws, 'is_firmware_update_available', None)}")
            print(f"  is_firmware_update_allowed={getattr(fws, 'is_firmware_update_allowed', None)}")
            print(f"  firmware_update_status={getattr(fws, 'firmware_update_status', None)}")
            jobs = getattr(fws, "firmware_update_jobs", []) or []
            print(f"  firmware_update_jobs: {len(jobs)}")
            ids = [getattr(j, "job_id", None) or getattr(j, "id", None) for j in jobs]
            ids = [i for i in ids if i]
            print(f"  job ids: {ids}")
            available = (
                getattr(fws, "is_firmware_update_available", False)
                and not getattr(fws, "is_firmware_update_allowed", False)
                and bool(ids)
            )
            print(f"  grant button would be AVAILABLE: {available}")
            if available:
                print("  (skipping actual grant call — non-destructive smoke)")


if __name__ == "__main__":
    asyncio.run(main())
