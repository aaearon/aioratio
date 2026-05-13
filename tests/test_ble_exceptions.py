"""All BLE exceptions must descend from ``RatioError``."""

from __future__ import annotations

from aioratio.exceptions import (
    RatioBleConnectionError,
    RatioBleError,
    RatioBleNotBondedError,
    RatioBleProtocolError,
    RatioBleUnsupportedCommandError,
    RatioError,
)


def test_ble_error_inherits_from_ratio_error() -> None:
    assert issubclass(RatioBleError, RatioError)


def test_ble_subclasses_inherit_from_ble_error() -> None:
    for cls in (
        RatioBleConnectionError,
        RatioBleProtocolError,
        RatioBleNotBondedError,
        RatioBleUnsupportedCommandError,
    ):
        assert issubclass(cls, RatioBleError)
        assert issubclass(cls, RatioError)
