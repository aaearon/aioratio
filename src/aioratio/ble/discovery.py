"""Helpers for identifying Ratio chargers from BLE advertisement data.

Use these in a Home Assistant ``async_step_bluetooth`` handler — or any custom
scanner loop — to filter advert data down to actual Ratio chargers without
duplicating the matcher logic that ``[bluetooth]`` matchers in ``manifest.json``
already encode.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from .const import ADVERT_LOCAL_NAME_PREFIX, ADVERT_MANUFACTURER_ID

__all__ = ["RatioAdvertisement", "parse_advertisement"]


@dataclass(frozen=True)
class RatioAdvertisement:
    """Parsed Ratio EV charger BLE advertisement.

    ``manufacturer_byte`` is the first byte of the manufacturer-data payload.
    Do not interpret it as the IPC protocol version: chargers advertising
    ``0x03`` have been observed reporting ``0x06`` (BASELINE_4_0_0) on the
    Version characteristic. Read the characteristic after connecting for the
    authoritative version.
    """

    local_name: str
    manufacturer_byte: int


def parse_advertisement(
    local_name: str | None,
    manufacturer_data: Mapping[int, bytes],
) -> RatioAdvertisement | None:
    """Return a :class:`RatioAdvertisement` if the advert is a Ratio charger.

    The argument shapes match :class:`bleak.backends.scanner.AdvertisementData`,
    so callers can pass the fields straight through. Home Assistant's
    ``BluetoothServiceInfoBleak`` exposes the same fields.
    """
    if not local_name or not local_name.startswith(ADVERT_LOCAL_NAME_PREFIX):
        return None
    payload = manufacturer_data.get(ADVERT_MANUFACTURER_ID)
    if not payload:
        return None
    return RatioAdvertisement(local_name=local_name, manufacturer_byte=payload[0])
