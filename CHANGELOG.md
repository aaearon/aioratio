# Changelog

## [0.6.0] — 2026-05-02

### Added

- `diagnostics(serial)` → `ChargerDiagnostics`: read-only system info per
  charger (CPC serial, firmware/hardware versions, WiFi/ethernet network
  status, backend connectivity, live OCPP connection status).
- `ocpp_settings(serial)` → `InstallerOcppSettings`: installer OCPP
  settings including `enabled`, `cpms` (configured CPMS), and
  `charge_point_identifier`. Each field exposes `*_status: OcppFieldStatus`
  metadata (`is_change_allowed`, `change_not_allowed_reason`) populated from
  the `ValueDTOWithReason` GET shape.
- `set_ocpp_settings(serial, settings)`: write OCPP settings. Accepts
  `InstallerOcppSettings` (recommended) or a flat dict. `to_dict()` emits
  the flat PUT shape (`{enabled, cpms, chargePointIdentifier}`) without
  metadata wrappers.
- `cpms_options(serial)` → `list[CpmsConfig]`: list operator-provided CPMS
  options from the charger-level CPMS endpoint. Returns `[]` gracefully on
  403 or API error (operator may not expose options).
- New models: `ChargerDiagnostics`, `ProductInformation`,
  `ConnectivityController`, `MainController`, `NetworkStatus`, `WifiStatus`,
  `EthernetStatus`, `Ipv4`, `BackendStatus`, `OcppDiagnosticStatus`,
  `InstallerOcppSettings`, `CpmsConfig`, `OcppFieldStatus` — all exported
  from `aioratio.models`.

### Changed / Fixed

- `CpmsConfig` now stores `cpid_type` (from `ConfigurableCpms.cpidType`) so
  callers know the identifier format required by a given operator.
- `InstallerOcppSettings.from_dict` correctly distinguishes the GET
  `ValueDTOWithReason` wrapper from a flat `CpmsConfig` dict.
- `cpms_options()` re-raises `RatioRateLimitError` instead of swallowing it
  as an empty list — only 403/404 (operator not configured) returns `[]`.
- `Self` import uses `try/except ImportError` fallback to `typing_extensions`
  for environments that run below the declared `python_requires = ">=3.11"`
  (e.g. CI matrix). Not a supported configuration change.

### Sources

All wire shapes confirmed against decompiled APK 3.9.1:
`ChargerDiagnosticsDTO.kt`, `InstallerOcppSettings.java`,
`ChargePointIdentifier.java`, `ConfiguredCpms.java`,
`ConfigurableCpms.java`, `ValueDTOWithReason.java`,
`RequestPath.java` (ChargerConfigOcppCpmsList path).

---

## [0.5.0] — 2025-04-xx

- `grant_upgrade_permission(serial, firmware_update_job_ids)`: approve
  queued firmware update jobs.
- `set_solar_settings` HTTP 502 fix: emit flat integers in PUT body
  (not nested `{value: N}` wrappers). Smoke-tested live.
- `ScheduleSlot.to_dict()`, `ChargeSchedule.to_dict()`, improved
  `UpperLowerLimitSetting.to_dict()`.

## [0.4.0]

- `set_solar_settings`, `SolarSettings.to_dict()`.

## [0.3.0]

- `charge_schedule`, `set_charge_schedule`, `ChargeSchedule`, `ScheduleSlot`.

## [0.2.0]

- `vehicles`, `add_vehicle`, `remove_vehicle`.
- `session_history`, `SessionHistoryPage`.

## [0.1.0]

- Initial release: auth, `chargers_overview`, `user_settings`, `solar_settings`.
