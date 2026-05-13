"""Hardware smoke test for ``aioratio[ble]``.

Usage::

    python scripts/ble_smoke.py <bonded-charger-mac>

Walks every priority READ command and prints what the charger returned.
Not shipped in the wheel — only useful next to a powered charger.

Prerequisites:
  * ``pip install aioratio[ble]``
  * The charger must already be bonded with the host's BlueZ stack (use
    ``bluetoothctl pair <mac>`` or the Ratio mobile app). Otherwise the
    bleak connect will fail with ``org.bluez.Error.ConnectionAttemptFailed``
    once the RPA rotates.
"""

from __future__ import annotations

import asyncio
import sys
from pprint import pprint

from aioratio import BleClient


async def main(address: str) -> None:
    client = await BleClient.from_address(address)
    await client.connect()
    print(f"Connected. protocol_version = {client.protocol_version}")
    try:
        for name in (
            "get_charger_status",
            "get_charger_sensor_values",
            "get_user_settings",
            "get_solar_settings",
            "get_time_settings",
        ):
            method = getattr(client, name)
            print(f"\n--- {name}() ---")
            try:
                pprint(await method())
            except Exception as exc:  # noqa: BLE001
                print(f"  ERROR: {type(exc).__name__}: {exc}")
        print("\n--- wifi_scan() ---")
        try:
            for ap in await client.wifi_scan():
                print(f"  {ap.ssid!r} rssi={ap.rssi}")
        except Exception as exc:  # noqa: BLE001
            print(f"  ERROR: {type(exc).__name__}: {exc}")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: ble_smoke.py <bonded-charger-mac>", file=sys.stderr)
        raise SystemExit(2)
    asyncio.run(main(sys.argv[1]))
