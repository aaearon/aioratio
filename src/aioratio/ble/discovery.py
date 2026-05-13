"""Helpers for identifying Ratio chargers from BLE advertisement data.

Use these in a Home Assistant ``async_step_bluetooth`` handler — or any custom
scanner loop — to filter advert data down to actual Ratio chargers without
duplicating the matcher logic that ``[bluetooth]`` matchers in ``manifest.json``
already encode.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from .const import ADVERT_LOCAL_NAME_PREFIX, ADVERT_MANUFACTURER_ID

__all__ = ["RatioAdvertisement", "parse_advertisement", "parse_service_info"]


class _ServiceInfoLike(Protocol):
    name: str | None
    manufacturer_data: Mapping[int, bytes]


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
    so callers can pass ``adv.local_name`` and ``adv.manufacturer_data`` through.
    For Home Assistant ``BluetoothServiceInfoBleak`` callers — which expose
    ``.name`` rather than ``.local_name`` — use :func:`parse_service_info`.
    """
    if not local_name or not local_name.startswith(ADVERT_LOCAL_NAME_PREFIX):
        return None
    payload = manufacturer_data.get(ADVERT_MANUFACTURER_ID)
    if not payload:
        return None
    return RatioAdvertisement(local_name=local_name, manufacturer_byte=payload[0])


def parse_service_info(info: _ServiceInfoLike) -> RatioAdvertisement | None:
    """Return a :class:`RatioAdvertisement` for Home Assistant service info.

    HA's ``BluetoothServiceInfoBleak`` exposes ``.name`` (assigned from
    ``advertisement_data.local_name`` with a device-name/address fallback) and
    ``.manufacturer_data``. This wrapper duck-types on those attributes so the
    library does not need to import Home Assistant.
    """
    return parse_advertisement(info.name, info.manufacturer_data)
