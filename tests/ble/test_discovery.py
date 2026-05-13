"""``parse_advertisement`` — match Ratio chargers in BLE scan results."""

from __future__ import annotations

from aioratio.ble.const import ADVERT_MANUFACTURER_ID
from aioratio.ble.discovery import RatioAdvertisement, parse_advertisement


def test_returns_none_when_local_name_is_none() -> None:
    assert parse_advertisement(None, {ADVERT_MANUFACTURER_ID: b"\x03"}) is None


def test_returns_none_when_local_name_prefix_mismatch() -> None:
    assert parse_advertisement("Ember Mug", {ADVERT_MANUFACTURER_ID: b"\x03"}) is None


def test_returns_none_when_manufacturer_id_missing() -> None:
    # Wrong manufacturer ID (e.g. some other vendor at 0x004C).
    assert parse_advertisement("RATIO_ABC", {0x004C: b"\x03"}) is None


def test_returns_none_when_manufacturer_payload_empty() -> None:
    assert parse_advertisement("RATIO_ABC", {ADVERT_MANUFACTURER_ID: b""}) is None


def test_returns_advertisement_with_local_name_and_manufacturer_byte() -> None:
    adv = parse_advertisement("RATIO_ABC", {ADVERT_MANUFACTURER_ID: b"\x03\xff"})
    assert adv == RatioAdvertisement(local_name="RATIO_ABC", manufacturer_byte=0x03)


def test_manufacturer_byte_is_first_byte_only() -> None:
    # Defensive: even if the advert carries trailing bytes, we surface only the
    # first one. The remainder is not interpreted today.
    adv = parse_advertisement("RATIO_XYZ", {ADVERT_MANUFACTURER_ID: b"\x06\x11\x22"})
    assert adv is not None
    assert adv.manufacturer_byte == 0x06


def test_dataclass_is_hashable() -> None:
    # Lets HA cache discovery results in a set/dict if it wants.
    adv1 = RatioAdvertisement(local_name="RATIO_A", manufacturer_byte=3)
    adv2 = RatioAdvertisement(local_name="RATIO_A", manufacturer_byte=3)
    assert hash(adv1) == hash(adv2)
    assert {adv1, adv2} == {adv1}
