# Changelog

## [Unreleased]

## [0.8.0] — 2026-05-09

### Added

- Module-level loggers (`aioratio.auth`, `aioratio.client`, `aioratio.token_store`,
  `aioratio._transport`) emit DEBUG-level events for login, refresh, 401 retry,
  rate-limit hits, and HTTP failures. No credentials, tokens, or device passwords
  are ever logged. Note the transport logger uses the leading-underscore module
  name because the module is private (`aioratio._transport`).
- `RatioApiError.status` attribute carries the originating HTTP status code
  (or `None` if the error was not raised from an HTTP response). Existing
  call sites that construct `RatioApiError("...")` keep working unchanged.
- `__version__` is now exported from the top-level `aioratio` package.

### Changed

- **BREAKING:** `cpms_options(serial)` now only returns `[]` for HTTP 403/404
  responses; other transport failures (5xx, rate-limit, malformed JSON) now
  propagate as `RatioApiError` / `RatioRateLimitError` instead of being
  silently swallowed. **Callers that relied on the empty-list fallback for
  non-403/404 errors must add explicit error handling.** The downstream
  `home-assistant-ratio` integration already wraps this call in its own
  per-call try/except in the coordinator, so HACS users do not need to act.
- `ScheduleSlot.to_dict()` now validates `start`/`end` strings against
  `^(?:[01]?\d|2[0-3]):[0-5]\d$` and raises a clear `ValueError`. The previous
  behaviour was to fail later inside `int(...)` with a confusing trace.
  Both zero-padded (`07:00`) and single-digit-hour (`7:00`) forms are
  accepted so direct callers aren't BC-broken.
- Tightened `_CloudTransport.request()` and `_get_settings()` return
  annotations from `Any` to `dict[str, Any] | list[Any] | None` /
  `dict[str, Any] | None` for stronger downstream type-checking.
- `RatioClient.user_id()` now caches the decoded `sub` claim per ID token,
  skipping the JWT base64-decode + JSON parse on every authenticated call.
  (The underlying `auth.get_access_token()` still loads the token store as
  before; only the parse is cached.)
- Dependency: `aiohttp>=3.9,<5` (previously unbounded upper).

### Internal

- Added `[tool.ruff]` config and applied auto-fixable lint/format pass.
- Added `.pre-commit-config.yaml` for ruff + mypy + standard hygiene hooks.
- Removed unreachable Python 3.10 typing fallbacks (package is `>=3.11`).
- Added regression coverage for `cpms_options` 403/404/5xx/no-status branches.

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
