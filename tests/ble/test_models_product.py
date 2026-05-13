"""``ProductInformationResponse`` parsing."""

from __future__ import annotations

from aioratio.ble.models import ProductInformationResponse


def test_full_payload() -> None:
    raw = {
        "transaction": "t",
        "result": "Success",
        "connectivityController": {
            "firmwareVersion": "4.1.2",
            "hardwareVersion": "B1",
        },
        "mainController": {
            "serialNumber": "P00000000013428",
            "firmwareVersion": "3.9.1",
            "hardwareVersion": "A2",
            "hardwareType": "Inspiro",
        },
    }
    parsed = ProductInformationResponse.from_dict(raw)
    assert parsed.main_controller is not None
    assert parsed.main_controller.serial_number == "P00000000013428"
    assert parsed.connectivity_controller is not None
    assert parsed.connectivity_controller.firmware_version == "4.1.2"


def test_payload_without_subcontrollers() -> None:
    raw = {"transaction": "t", "result": "Success"}
    parsed = ProductInformationResponse.from_dict(raw)
    assert parsed.main_controller is None
    assert parsed.connectivity_controller is None
