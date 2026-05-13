"""Inspiro IPC BLE constants.

Sources confirmed against the decompiled v3.9.1 app:
  - ``nl/ratio/ev/charger/core/bluetooth/BluetoothManager.java``
  - ``nl/ratio/ev/charger/core/bluetooth/BleProtocolVersions.java``

The advertised manufacturer ID is empirically ``0x0BFF`` (3071) and the advert
manufacturer payload is a single byte equal to the device's IPC protocol version
(observed: ``0x03`` = BASELINE_3_0_0).
"""

from __future__ import annotations

from typing import Final

# GATT service + characteristic UUIDs ("Insp IPC" ASCII prefix).
SERVICE_UUID: Final[str] = "496e7370-2049-5043-2073-657276696365"
RX_CHAR_UUID: Final[str] = "496e7370-2049-5043-2043-686172205258"  # write
TX_CHAR_UUID: Final[str] = "496e7370-2049-5043-2043-686172205458"  # notify
VERSION_CHAR_UUID: Final[str] = "496e7370-2049-5043-2043-686172205665"  # read

# BleProtocolVersions enum (BluetoothManager BLE handshake target).
PROTOCOL_BASIS: Final[int] = 1
PROTOCOL_BASELINE_2_3_0: Final[int] = 2
PROTOCOL_BASELINE_3_0_0: Final[int] = 3
PROTOCOL_BASELINE_3_3_0: Final[int] = 4
PROTOCOL_BASELINE_3_5_0: Final[int] = 5
PROTOCOL_BASELINE_4_0_0: Final[int] = 6

# Discovery filters (Phase 0 capture).
ADVERT_LOCAL_NAME_PREFIX: Final[str] = "RATIO_"
ADVERT_MANUFACTURER_ID: Final[int] = 0x0BFF  # 3071
