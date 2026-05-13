"""BLE subpackage (``aioratio[ble]`` extras).

Importing this package fails fast with a helpful message if ``bleak`` is not
installed, since every BLE code path depends on it.
"""

from __future__ import annotations

from ._bleak_check import require_bleak

require_bleak()

from .client import BleClient  # noqa: E402
from .discovery import RatioAdvertisement, parse_advertisement  # noqa: E402

__all__ = ["BleClient", "RatioAdvertisement", "parse_advertisement"]
