# Changelog

## [Unreleased]

- BLE: BleClient.connect() now releases the transport if read_version() fails
- BLE: _BOND_REQUIRED_MARKERS expanded with ATT 0x0c / Insufficient Encryption Key Size
- BLE tests: added serializer-key drift coverage for Network/Ocpp/Backend response models
- BLE: new parse_service_info() helper for HA BluetoothServiceInfoBleak

## [0.10.0] — 2026-05-13

### Added

- Optional BLE subpackage (`aioratio.ble`) installed via `pip install aioratio[ble]`.
  Cloud-only installs do NOT pull in `bleak`; `aioratio.BleClient` is resolved
  lazily and raises `RuntimeError` with an install hint if the extras are missing.
- `BleClient` covers every read command plus the user-level writes
  (`charge_control`, `set_user_settings`, `set_solar_settings`,
  `set_time_settings`) and the Wi-Fi recovery flow (`wifi_scan`, `wifi_connect`).
  Each command is gated against the charger's reported Inspiro IPC protocol
  version; calls below the minimum raise `RatioBleUnsupportedCommandError`
  before any wire write.
- BLE request/response dataclasses live under `aioratio.ble.models`. JSON keys
  are taken verbatim from the decompiled `<Class>$$serializer.java` descriptors
  (plus `SerializedNames.java` for the TimeSettings fields); the frozen
  reference table is at `tests/ble/_serializer_refs.py`.
- Get*Settings responses expose `SettableValue` envelopes
  (`{value, isChangeAllowed, allowedValues?, lowerLimit?, upperLimit?}`); Set\*
  updates still emit flat values — the wire is asymmetric.
- `GetNetworkStatusResponse`, `GetOcppStatusResponse`,
  `GetBackendStatusResponse` are fully modelled (`WifiInfo` / `EthernetInfo` /
  `Ipv4Info` / `OcppCpms`), exposed via `get_network_status()`,
  `get_ocpp_status()`, `get_backend_status()`.
- Wi-Fi SSID and OCPP `centralSystem` / `url` fields are base64-encoded on the
  wire; models decode and surface plain text on `ssid` / `central_system` /
  `url` with `*_raw` companion attributes for the encoded form.
  `BleClient.wifi_connect()` base64-encodes the SSID on the way out.
- `ChargerSensorValuesResponse` voltages are deciV (0.1 V) and currents are
  deciA; `voltage_phase_{1,2,3}_volts` / `current_phase_{1,2,3}_amps`
  convenience properties scale them.
- New exceptions: `RatioBleError`, `RatioBleConnectionError`,
  `RatioBleProtocolError`, `RatioBleNotBondedError`,
  `RatioBleUnsupportedCommandError`. All descend from `RatioError`.
- `aioratio.ble.const` exposes the Inspiro IPC GATT UUIDs, advertisement
  filters (manufacturer ID `0x0BFF` / 3071), and `BleProtocolVersions`.
- `aioratio.ble.parse_advertisement(local_name, manufacturer_data)` /
  `RatioAdvertisement`: discovery helper for HA's `async_step_bluetooth`
  (and any custom scanner) — accepts the same shape as
  `bleak.backends.scanner.AdvertisementData`, returns `None` for non-Ratio
  adverts. Surfaces the manufacturer byte but does not interpret it as the
  protocol version (see notes).
- `BleClient` is now an async context manager: `async with BleClient(...) as c:`
  calls `connect()` / `disconnect()` automatically.
- `BleClient.from_service_info(discovery_info)` classmethod constructs from
  anything carrying a `BLEDevice` on `.device` — matches the shape of HA's
  `home_assistant_bluetooth.BluetoothServiceInfoBleak` without aioratio
  importing the HA-only type.
- `BleClient.connect()` now distinguishes auth/bond failures from generic
  transport failures: peers reporting Insufficient Authentication /
  Insufficient Encryption / ATT 0x05 / ATT 0x0f raise `RatioBleNotBondedError`
  instead of the generic `RatioBleConnectionError`, letting HA UX surface a
  "please pair the charger" hint.
- `scripts/ble_smoke.py` walks the priority reads against a real charger
  (excluded from the wheel).

### Notes

- Bonding is required: the charger returns
  `BleakGATTProtocolError: Insufficient Authentication` on every GATT
  operation until pair completes. Pairing uses a per-device PIN printed in
  the charger documentation, so `BleClient` cannot auto-bond. On Linux /
  Home Assistant, callers register their own `org.bluez.Agent1` (e.g. via
  `python-dbus-fast`, which HA already ships) with `KeyboardOnly` /
  `KeyboardDisplay` capability and supply the PIN from `RequestPasskey`;
  HACS precedent: `phurth/ha-onecontrol`, `nogic1008/ha_lixil_shutter`.
  On Windows / macOS the OS Bluetooth dialog handles passkey entry. The
  Home Assistant `bluetooth` integration itself does **not** perform SMP
  pairing — that lives in the consuming integration's config flow.
- `IpcTransactionResult` is lowercase `"success"` / `"failed"` on the wire
  even though the decompiled descriptor implied title case;
  `is_success()` is case-insensitive defensively.
- One charger reports `protocolVersion = 6` (BASELINE_4_0_0) from the Version
  characteristic but advertises `0x03` in manufacturer data — the advertised
  byte is **not** the IPC protocol version; trust the characteristic read.
- `[ble]` extras pin `bleak>=0.22,<4`.


## [0.9.1] — 2026-05-13

### Fixed

- `OcppDiagnosticStatus.cpms_name` now reads the `centralSystem` key from the
  cloud `ocppStatus.cpms` object. Previously it looked up `name` (which the
  cloud never emits), so `cpms_name` was always `None` for real payloads.
  Verified against `ConfiguredCpms$$serializer.java` and a live capture.

## [0.9.0] — 2026-05-10

### Fixed

- `FirmwareUpdateJob` now parses the cloud payload fields `firmwareUpdateJobId`,
  `firmwareUpdateJobRequiresPermission`, `firmwareUpdateJobType`, and
  `firmwareUpdateJobStatus`. Previously the parser looked for `jobId`/`id`/`type`/
  `status` (none of which the cloud actually emits), so `job_id` was silently
  `None` for every real payload — silently breaking `grant_upgrade_permission`
  flows that rely on populated job IDs.

### Changed (BREAKING)

- `FirmwareUpdateJob.raw` field removed. The schema is now fully decoded from
  `FirmwareUpdateJobDTO$$serializer.java` so the raw-payload escape hatch is no
  longer needed.
- `FirmwareUpdateJob.from_dict` no longer recognizes the legacy/incorrect
  `jobId` / `id` / `type` / `status` flat keys. Callers passing those keys must
  switch to the real cloud keys (`firmwareUpdateJob*` prefix).
- New `FirmwareUpdateJob.requires_permission: bool` field (defaults to `True`,
  matching the kotlinx default).

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
