"""``ProductInformationResponse`` parsing."""

from __future__ import annotations

from aioratio.ble.models import ProductInformationResponse


def test_full_payload_with_connectivity_serial_number() -> None:
    """v3.13.2 firmware adds ``serialNumber`` to ``connectivityController``."""
    raw = {
        "transaction": "t",
        "result": "success",
        "connectivityController": {
            "serialNumber": "SN-CONN-0001",
            "firmwareVersion": "3.13.2",
            "hardwareVersion": "C5",
        },
        "mainController": {
            # main_controller doesn't include hardwareVersion on the v3.13.2 wire
            "serialNumber": "SN-MAIN-0001",
            "firmwareVersion": "02.03.03",
            "hardwareType": "101",
        },
    }
    parsed = ProductInformationResponse.from_dict(raw)
    assert parsed.main_controller is not None
    assert parsed.main_controller.serial_number == "SN-MAIN-0001"
    assert parsed.main_controller.firmware_version == "02.03.03"
    assert parsed.main_controller.hardware_type == "101"
    assert parsed.main_controller.hardware_version is None
    assert parsed.connectivity_controller is not None
    assert parsed.connectivity_controller.serial_number == "SN-CONN-0001"
    assert parsed.connectivity_controller.firmware_version == "3.13.2"


def test_payload_without_subcontrollers() -> None:
    raw = {"transaction": "t", "result": "success"}
    parsed = ProductInformationResponse.from_dict(raw)
    assert parsed.main_controller is None
    assert parsed.connectivity_controller is None
