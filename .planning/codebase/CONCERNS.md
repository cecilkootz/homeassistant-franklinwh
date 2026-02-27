# Codebase Concerns

**Analysis Date:** 2026-02-27

## Tech Debt

**Incomplete Mode Type Detection:**
- Issue: `async_set_battery_reserve()` cannot preserve the current operation mode when updating SOC percentage. It defaults to `self_consumption` mode for all updates, potentially overriding user-configured modes.
- Files: `coordinator.py:210-240`
- Impact: Users changing battery reserve while in `time_of_use` or other modes will have their mode reset to `self_consumption`, losing their intended mode configuration.
- Fix approach: Once the franklinwh API provides mode type information (e.g., `mode.get_type()` or similar), implement mode type detection to preserve the current mode while only updating the SOC value.

**Local API Not Functional:**
- Issue: Configuration fields for local API are defined in constants and partially implemented in coordinator, but the feature is disabled in config flow with hardcoded comments indicating it's "not functional yet".
- Files: `const.py:8-9,16-18`, `config_flow.py:111-120`, `config_flow.py:207-209`, `coordinator.py:40-41,47-48`
- Impact: Code bloat from unused parameters (`use_local_api`, `local_host`) passed through initialization chain. Users cannot use local API even if it becomes available.
- Fix approach: Either complete local API implementation or remove all related code, constants, and configuration options. Keep implementation if planned for future release.

**Client Initialization with Manual Locking:**
- Issue: Client initialization uses a manual `_client_lock` boolean flag (line 54) to prevent concurrent initialization, which is fragile and could fail under race conditions.
- Files: `coordinator.py:50-54,79-91`
- Impact: In theory, rapid concurrent calls to `_async_update_data()` could result in multiple client creation attempts. The flag approach is not atomic and Home Assistant's async executor doesn't fully prevent this.
- Fix approach: Replace with asyncio.Lock or use Home Assistant's built-in mechanisms for first-run initialization in update coordinators.

## Known Issues

**Silent Failures in Switch Setup:**
- Issue: Smart switch discovery catches KeyError for missing "accessoryType" but only logs it; switches won't be created if accessories list is malformed.
- Files: `switch.py:37-46`
- Impact: If FranklinWH API returns accessories without "accessoryType" field, the error is silently logged and users get no smart switches. This could happen if API schema changes or returns partial data.
- Trigger: API returns malformed accessory list without "accessoryType" key.
- Workaround: Check Home Assistant logs for "Expected key 'accessoryType' not found" errors.

**AttributeError Authentication Detection:**
- Issue: `coordinator.py:118-142` attempts to catch authentication errors by checking if "AuthenticationError" is in the type name, which is fragile and specific to the franklinwh library implementation.
- Files: `coordinator.py:118-142`
- Impact: If franklinwh library changes how it raises auth errors (custom exception class, different base classes), authentication failures may not be properly detected as `ConfigEntryAuthFailed`, causing entities to show as unavailable rather than prompting re-auth.
- Trigger: franklinwh library updates its exception structure.
- Workaround: Monitor logs for "Error communicating with API" messages after max failures when auth credentials are invalid.

**Service Calls Without None Validation:**
- Issue: Service handlers in `__init__.py` extract parameters with `.get()` but don't validate they are not None before passing to coordinator methods.
- Files: `__init__.py:69-83`
- Impact: If Home Assistant service framework fails to provide required parameters (edge case), the coordinator methods will receive None and fail with unclear error messages.
- Trigger: Custom service calls with missing parameters.
- Workaround: Not applicable - Home Assistant should enforce schema validation.

**Missing Software Version in Entry Data:**
- Issue: `sw_version` is retrieved from `entry.data.get("sw_version")` in sensor, switch, and config_flow, but it's never written to the config entry during setup.
- Files: `sensor.py:259`, `switch.py:81,161`, `config_flow.py:54`
- Impact: Device version will always be None in Home Assistant UI, limiting diagnostics and device information.
- Fix approach: Add software version retrieval during device validation in `validate_input()` and store it in the config entry.

## Security Considerations

**Credential Handling:**
- Risk: Username and password are stored in Home Assistant config entries and referenced in coordinator initialization. While Home Assistant protects config entries, the credentials are held in memory and passed through the async update chain.
- Files: `coordinator.py:44-45`, `__init__.py:34-35`, `config_flow.py:34-35`
- Current mitigation: Home Assistant handles config entry encryption at rest; credentials are not logged (handled by diagnostics redaction in `diagnostics.py:14`).
- Recommendations: Ensure `token_fetcher` reuses tokens and doesn't continuously re-authenticate. Monitor for credential leaks in exception messages.

**Broad Exception Handling in Config Flow:**
- Risk: `except Exception:` catches all exceptions including network errors, type errors, and programming errors, masking root causes.
- Files: `config_flow.py:104,152`
- Current mitigation: Exception is logged with `_LOGGER.exception()` for debugging.
- Recommendations: Consider narrowing exception types to catch network and authentication errors specifically, letting programming errors propagate.

**Accessory Type Matching:**
- Risk: Smart switches are created based on `AccessoryType.SMART_CIRCUIT_MODULE.value` comparison, but if the franklinwh library changes enum values without updating this code, smart switches won't be discovered.
- Files: `switch.py:40`
- Current mitigation: None.
- Recommendations: Add logging of matched accessory types during setup to verify the comparison works correctly.

## Performance Bottlenecks

**Repeated Attribute Access in Sensors:**
- Problem: Each sensor's `native_value` property calls `value_fn` which accesses nested attributes (`data.stats.current.battery_soc`). With 23 sensors polling every 60 seconds, this creates repeated object traversal.
- Files: `sensor.py:262-274`, particularly the value_fn lambdas
- Cause: No caching of stats data between sensor updates; Home Assistant calls each entity's property independently.
- Improvement path: Consider caching computed values in `FranklinWHData` class or using lazy evaluation.

**Switch State Detection:**
- Problem: Smart switches are created for every SMART_CIRCUIT_MODULE found (hardcoded loop `range(3)`), but switches are only populated with actual state if they exist in the API response.
- Files: `switch.py:37-44`
- Cause: Loop creates up to 3 switches regardless of how many actually exist; if device only has 2 switches, Switch 3 will be perpetually unavailable.
- Improvement path: Use actual count from API response to determine how many switches to create.

**API Call During Setup:**
- Problem: `switch.py:33-35` calls `async_config_entry_first_refresh()` again during async_setup_entry, even though it was already called in `__init__.py:52`. This causes duplicate initial API calls.
- Files: `switch.py:33`, `__init__.py:52`
- Cause: Both initialization and platform setup call first_refresh to ensure data is available.
- Improvement path: Store refresh completion status or use coordinator's built-in first refresh mechanism to prevent duplicates.

## Fragile Areas

**Stats Data Attribute Extraction:**
- Files: `sensor.py:46-211`, `coordinator.py:99-103`
- Why fragile: Sensors rely on specific attribute names being present in stats objects (`battery_soc`, `solar_production`, etc.). If franklinwh library changes attribute names or structure, sensors will silently return None instead of values.
- Safe modification: Always wrap attribute access in try-except, test thoroughly with actual device data.
- Test coverage: Sensor value functions have no unit tests; only safe through integration testing with real device.

**Mode String Mapping:**
- Files: `coordinator.py:185-192`
- Why fragile: Mode mapping is hardcoded in `async_set_operation_mode()`. If franklinwh library adds new modes or renames existing ones, the mapping becomes incomplete/incorrect.
- Safe modification: Consider moving mode mapping to constants or creating a bidirectional lookup; add validation that mode_map covers all supported modes.
- Test coverage: No tests for mode setting; only covered by integration testing.

**Error Detection via String Matching:**
- Files: `coordinator.py:118-122,146-147`, `config_flow.py:59-77`
- Why fragile: Error type detection uses `"auth" in str(err).lower()` and `"AuthenticationError" in str(type(err))`. This is brittle - error messages or class names can change between library versions.
- Safe modification: Check franklinwh library source directly for exception types rather than string matching. Request public exception classes from the library if not available.
- Test coverage: Auth error detection untested; only works if franklinwh errors contain expected strings.

**Divisor Assumptions in Sensors:**
- Files: `sensor.py:163,179,195,203`
- Why fragile: Some sensors divide API values by 1000 (e.g., `switch_1_use / 1000`) without documentation of why. If API changes units, these become incorrect.
- Safe modification: Add comments explaining unit conversions; document expected API units; add unit tests for conversion functions.
- Test coverage: Conversion factors have no tests.

**Gateway ID Extraction:**
- Files: `sensor.py:256`, `switch.py:78,148`
- Why fragile: Code assumes gateway_id is a string and slices the last 6 characters for display (`gateway_id[-6:]`). If API changes ID format or returns None, slicing fails silently or creates incorrect display names.
- Safe modification: Add validation and fallback for gateway_id display.
- Test coverage: Device naming has no unit tests.

## Scaling Limits

**Fixed Retry Limit:**
- Current capacity: 3 consecutive failures before marking unavailable
- Limit: Network glitches lasting more than 3 minutes (at 60-second intervals) will mark all entities unavailable
- Scaling path: Make failure threshold configurable; consider exponential backoff instead of fixed 3-failure limit.

**Hard-Coded Sensor Count:**
- Current capacity: 23 hardcoded sensors
- Limit: If FranklinWH hardware adds new metrics, integration must be updated and redeployed
- Scaling path: Consider dynamic sensor discovery based on device capabilities from API.

**Fixed Switch Count:**
- Current capacity: Always creates 3 smart switches (hardcoded `range(3)`)
- Limit: Devices with different numbers of switches show missing/extra switches
- Scaling path: Query device capabilities during setup to determine actual switch count.

## Dependencies at Risk

**franklinwh Library API Stability:**
- Risk: Integration depends on franklinwh>=1.0.0. Recent commit (7f78572) shows migration from sync to async API methods was needed. Future versions could have breaking changes.
- Impact: Upgrade to new franklinwh version without corresponding code update could break all data fetching.
- Migration plan: Monitor franklinwh releases; implement version-gated code paths if major API changes occur. Consider pinning to specific franklinwh version range.

**Home Assistant Coordinator Pattern:**
- Risk: DataUpdateCoordinator implementation uses internal coordinator state (`_consecutive_failures`). If Home Assistant changes coordinator base class, this could break.
- Impact: Entity availability management would fail, all entities would show unavailable.
- Migration plan: Monitor Home Assistant coordinator API; test with HA dev branch before major releases.

## Missing Critical Features

**No Mode Status Reporting:**
- Problem: No sensor showing current operation mode. Users can set mode but can't verify if it was applied or what the device is currently running.
- Blocks: Can't create automations based on current mode; can't provide feedback that mode changed.
- Fix approach: Add `async_get_mode()` call in coordinator and create a sensor for current mode.

**No Battery Health/Temperature Reporting:**
- Problem: Battery SOC and energy values exist, but no health status, temperature, or cycle count data.
- Blocks: Can't monitor battery degradation; can't warn of overheating.
- Fix approach: If franklinwh library provides this data, add sensors for it.

**No Switch Load History:**
- Problem: Only current switch load is reported; no historical data for switches.
- Blocks: Can't analyze switch usage patterns.
- Fix approach: Add historical statistics sensors if Home Assistant provides them.

## Test Coverage Gaps

**No Unit Tests for Sensor Value Functions:**
- What's not tested: The 23 sensor `value_fn` lambdas that extract and transform API data
- Files: `sensor.py:39-213`
- Risk: Data transformation errors (unit conversions, attribute access) won't be caught until integration testing
- Priority: High - these are the primary data display mechanism

**No Tests for Error Handling in Coordinator:**
- What's not tested: Authentication error detection, timeout handling, consecutive failure counting, mode setting
- Files: `coordinator.py:75-240`
- Risk: Changes to error handling logic could introduce bugs in entity availability management
- Priority: High - affects user experience during connection problems

**No Tests for Config Flow Validation:**
- What's not tested: Invalid credentials, timeout scenarios, gateway ID validation
- Files: `config_flow.py:29-77`
- Risk: Configuration validation could fail silently or show confusing errors
- Priority: Medium - users experience setup flow less frequently

**No Tests for Service Handlers:**
- What's not tested: Mode setting, battery reserve setting, parameter validation
- Files: `__init__.py:69-108`
- Risk: Service calls could fail with unclear error messages
- Priority: Medium - affects advanced users using automation services

**No Tests for Switch Implementation:**
- What's not tested: Switch turn on/off, grid switch status detection, smart switch state mapping
- Files: `switch.py:51-211`
- Risk: Switch control could fail silently or show incorrect state
- Priority: Medium - affects control functionality

**No Integration Tests:**
- What's not tested: End-to-end flows with real/mocked FranklinWH API
- Risk: Features work in unit tests but fail with actual API
- Priority: High - critical for validating actual behavior

---

*Concerns audit: 2026-02-27*
