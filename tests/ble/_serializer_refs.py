"""Frozen reference of every wire key extracted from the BLE ``$$serializer.java``
descriptors. ``test_models_*.py`` asserts that ``to_dict()`` outputs only keys
that appear in this table — protecting against rename drift.

Source: ``rg 'addElement\\("([^"]+)"' .../ble/*$$serializer.java`` plus the
``SerializedNames.java`` constants for TimeSettings.
"""

from __future__ import annotations

from typing import Final

SERIALIZER_KEYS: Final[dict[str, tuple[str, ...]]] = {
    # Common header (every IPC frame has these two when result-bearing).
    "GenericIpcTransactionResponse": ("transaction", "result"),
    # Charger ops (charger/data/data_source/ble/).
    "ChargeControlRequest": ("transaction", "control"),
    "ChargeControlResponse": ("transaction", "result"),
    "ChargerStatusRequest": ("transaction",),
    "ChargerStatusResponse": (
        "transaction",
        "result",
        "cloudConnectionState",
        "isChargeStartAllowed",
        "isChargeStopAllowed",
        "indicators",
    ),
    "ChargeStatusIndicators": (
        "chargingState",
        "actualChargingPower",
        "isVehicleConnected",
        "isChargeSessionActive",
        "isPowerReducedByDSO",
        "isChargingPaused",
        "isChargingAuthorized",
        "isChargingDisabled",
        "isChargingDisabledReason",
        "errors",
    ),
    "GetChargerSensorValuesResponse": (
        "transaction",
        "result",
        "actualMainsVoltagePhase1",
        "actualMainsVoltagePhase2",
        "actualMainsVoltagePhase3",
        "actualSensorBoxCurrentPhase1",
        "actualSensorBoxCurrentPhase2",
        "actualSensorBoxCurrentPhase3",
    ),
    "GetProductInformationResponse": (
        "transaction",
        "result",
        "connectivityController",
        "mainController",
    ),
    "GetProductInformationResponse$ConnectivityController": (
        "firmwareVersion",
        "hardwareVersion",
    ),
    "GetProductInformationResponse$MainController": (
        "serialNumber",
        "firmwareVersion",
        "hardwareVersion",
        "hardwareType",
    ),
    # Settings (charger_settings/data/data_source/ble/).
    "GetUserSettingsResponse": (
        "transaction",
        "result",
        "startMode",
        "cableSettings",
        "minimumChargingCurrent",
        "maximumChargingCurrent",
        "chargingMode",
    ),
    "SetUserSettingsRequest": (
        # No descriptor file in the decompile, but the SetUserSettingsRequest.java
        # `private final` declarations list these fields and the write$Self method
        # encodes them in this order:
        "transaction",
        "startMode",
        "cableSettings",
        "minimumChargingCurrent",
        "maximumChargingCurrent",
        "chargingMode",
    ),
    "GetSolarSettingsResponse": (
        "transaction",
        "result",
        "smartSolarStartingCurrent",
        "pureSolarStartingCurrent",
        "sunOffDelayMinutes",
        "sunOnDelayMinutes",
    ),
    "SetSolarSettingsRequest": (
        "transaction",
        "smartSolarStartingCurrent",
        "pureSolarStartingCurrent",
        "sunOffDelayMinutes",
        "sunOnDelayMinutes",
    ),
    "GetTimeSettingsResponse": (
        # SerializedNames.TIMEZONE_ID == "timeZoneAreaLocation"
        # SerializedNames.POSIX == "timeZonePosix"
        "timeZoneAreaLocation",
        "timeZonePosix",
        "transaction",
        "result",
    ),
    "SetTimeSettingsRequest": (
        "timeZoneAreaLocation",
        "timeZonePosix",
        "transaction",
    ),
    # Wi-Fi onboarding (charger_onboarding/data/data_source/ble/).
    "WifiScanResponse": ("transaction", "numberOfFoundNetworks", "result"),
    "WifiAccessPointRequest": ("transaction", "index"),
    "WifiAccessPointResponse": ("transaction", "index", "ssid", "rssi", "result"),
    "WifiConnectRequest": ("transaction", "ssid", "password"),
    "WifiConnectResponse": ("transaction", "result"),
}
