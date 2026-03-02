---
wave: 1
depends_on: []
files_modified:
  - custom_components/franklin_wh/__init__.py
  - custom_components/franklin_wh/coordinator.py
autonomous: true
---

# Phase 6, Plan 01: Hybrid Data Architecture and Resilience

**Goal:** Enable hybrid operation where sensors without Modbus equivalents (energy totals) fall back to cloud data, and Modbus failures never mark the integration unavailable.

## Context

Phase 5 implemented local Modbus polling at 10s intervals when enabled. However, several hybrid data and resilience requirements remain:

1. **MDATA-07**: Energy totals (battery_charge kWh, battery_discharge kWh, etc.) are NOT available via Modbus - they must fall back to cloud data when Modbus is enabled
2. **MRES-01**: Write operations should always use cloud API regardless of Modbus mode
3. **MRES-02**: Modbus failures should fall back gracefully (entities stay available with last known data)
4. **MRES-03**: If Modbus is unreachable at startup, the integration should load successfully

Current state analysis:
- `coordinator.py` has a hybrid mode with `use_local_api` flag
- When Modbus is enabled, `_get_default_totals()` returns zeros instead of cloud data
- Modbus failures trigger update failures and eventually mark the integration unavailable
- No fallback mechanism to cloud data when Modbus fails
- No startup resilience - if Modbus is configured but unreachable, first refresh may fail

## Task 01: Implement Hybrid Data Strategy - Energy Totals from Cloud

**File:** `/Users/matt/Development/homeassistant-franklinwh/custom_components/franklin_wh/coordinator.py`

**Problem:** When `use_local_api=True`, the coordinator only polls Modbus and returns zeros for energy totals via `_get_default_totals()`.

**Solution:** Implement a dual-data strategy where Modbus data is used for real-time power flow sensors, but cloud data is used for energy totals and switch state.

**Changes:**

1. Modify `_async_update_data()` to fetch cloud data as a fallback when Modbus is enabled
2. Create a new method `_get_cloud_data_for_hybrid_mode()` that fetches stats via cloud API
3. In Modbus mode, return a hybrid `FranklinWHData`:
   - `stats.current`: From Modbus (solar, battery, grid power, SOC, home_load)
   - `stats.totals`: From cloud (energy kWh values)
4. Modify `_get_default_totals()` to fetch and return cloud totals

**Implementation:**
```python
async def _async_update_data(self) -> FranklinWHData:
    # MODBUS PATH: When local API is enabled
    if self.use_local_api and self.local_host:
        # ... existing Modbus read code ...
        sunspec_data = await self._sunspec_client.read(self.hass)

        # Fetch cloud data for energy totals and switch state
        cloud_stats = await self._fetch_cloud_stats_fallback()

        return FranklinWHData(
            stats=Stats(
                current=self._map_sunspec_to_stats_current(sunspec_data),
                totals=cloud_stats.totals if cloud_stats else self._get_default_totals(),
            ),
            switch_state=cloud_stats.switch_state if cloud_stats else None,
        )
```

**Verification:**
- Energy total sensors show non-zero values in Modbus mode
- Switch state is populated in Modbus mode
- Cloud fallback fetch is successful

---

## Task 02: Add Cloud Stats Fetcher for Hybrid Mode

**File:** `/Users/matt/Development/homeassistant-franklinwh/custom_components/franklin_wh/coordinator.py`

**Changes:**

1. Add `_fetch_cloud_stats_fallback()` method that:
   - Creates client lazily if not already created
   - Fetches stats via cloud API in executor
   - Returns `FranklinWHData` with stats and switch_state
   - Catches and logs any failures (don't propagate - return None)

2. Modify `FranklinWHCoordinator.__init__()` to initialize `_cloud_data_lock` for thread safety

**Implementation:**
```python
async def _fetch_cloud_stats_fallback(self) -> FranklinWHData | None:
    """Fetch cloud stats for hybrid mode fallback. Never raises - returns None on failure."""
    try:
        if self.client is None and not self._client_lock:
            self._client_lock = True
            try:
                self.token_fetcher = TokenFetcher(
                    self.username, self.password, session=self._http_session
                )
                self.client = Client(
                    self.token_fetcher, self.gateway_id, session=self._http_session
                )
            except Exception as err:
                self._client_lock = False
                _LOGGER.warning("Failed to initialize cloud client for fallback: %s", err)
                return None

        try:
            stats = await self.hass.async_add_executor_job(lambda: self.client.get_stats())
            if stats is None:
                _LOGGER.debug("Cloud stats fetch returned None")
                return None

            switch_state = None
            try:
                switch_state = await self.hass.async_add_executor_job(
                    lambda: self.client.get_smart_switch_state()
                )
            except Exception as err:
                _LOGGER.debug("Failed to fetch switch state: %s", err)

            return FranklinWHData(stats=stats, switch_state=switch_state)
        except Exception as err:
            _LOGGER.warning("Cloud fallback fetch failed: %s", err)
            return None
    except Exception as err:
        _LOGGER.warning("Unexpected error in cloud fallback: %s", err)
        return None
```

**Verification:**
- `_fetch_cloud_stats_fallback()` is called in Modbus mode
- Log messages show fallback fetch attempts
- No exceptions propagate from fallback

---

## Task 03: Implement Modbus Failure Graceful Degradation

**File:** `/Users/matt/Development/homeassistant-franklinwh/custom_components/franklin_wh/coordinator.py`

**Current behavior:** When Modbus fails, consecutive failures increment and eventually raise `UpdateFailed` which marks the integration unavailable.

**Solution:** Implement automatic fallback to cloud data when Modbus fails.

**Changes:**

1. Modify `_async_update_data()` exception handling to catch Modbus-specific errors
2. When Modbus fails, automatically switch to cloud-only mode for that update cycle
3. Log a warning when falling back to cloud due to Modbus failure
4. Reset Modbus connection on failure to allow recovery

**Implementation:**
```python
async def _async_update_data(self) -> FranklinWHData:
    try:
        if self.use_local_api and self.local_host:
            try:
                sunspec_data = await self._sunspec_client.read(self.hass)
                cloud_stats = await self._fetch_cloud_stats_fallback()
                return FranklinWHData(
                    stats=Stats(
                        current=self._map_sunspec_to_stats_current(sunspec_data),
                        totals=cloud_stats.totals if cloud_stats else self._get_default_totals(),
                    ),
                    switch_state=cloud_stats.switch_state if cloud_stats else None,
                )
            except (SunSpecModbusClientTimeout, SunSpecModbusClientException, RuntimeError) as err:
                # Modbus failed - log warning and fall back to cloud
                _LOGGER.warning(
                    "Modbus read failed (%s), falling back to cloud API. "
                    "Entities will remain available with last known data.",
                    err
                )
                # Reset Modbus client to allow recovery
                self._sunspec_client = None
                # Fall through to cloud path
    except Exception as err:
        # Non-Modbus errors during Modbus path - log and fall back
        _LOGGER.warning("Modbus path error (%s), falling back to cloud", err)
        self._sunspec_client = None

    # CLOUD PATH (fallback or original)
    # ... rest of existing cloud fetch code ...
```

**Verification:**
- Modbus timeouts logged with warning message
- Entities stay available when Modbus fails
- Cloud data used as fallback
- Modbus client resets to allow recovery

---

## Task 04: Add Startup Resilience - Load Even if Modbus Unreachable

**File:** `/Users/matt/Development/homeassistant-franklinwh/custom_components/franklin_wh/__init__.py`

**Current behavior:** `async_config_entry_first_refresh()` will fail if Modbus is unreachable during first refresh, causing `ConfigEntryNotReady` to be raised.

**Solution:** Catch startup Modbus failures and fall back to cloud-only mode, allowing integration to load successfully.

**Changes:**

1. Modify `async_setup_entry()` to handle startup Modbus failures gracefully
2. Log a warning when Modbus fails at startup
3. Continue setup with cloud-only mode

**Implementation:**
```python
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # ... existing setup code ...

    try:
        await coordinator.async_config_entry_first_refresh()
        _LOGGER.debug("FranklinWH initial data fetch complete")
    except ConfigEntryAuthFailed as err:
        _LOGGER.error("Authentication failed: %s", err)
        raise
    except Exception as err:
        # Check if this is a Modbus-related error at startup
        err_str = str(err)
        if "Modbus" in err_str or "SunSpec" in err_str or "RuntimeError" in type(err).__name__:
            # Modbus failed at startup - log warning and continue with cloud-only
            _LOGGER.warning(
                "Modbus failed at startup (%s), continuing with cloud-only mode. "
                "The integration loaded successfully but local Modbus will be disabled "
                "until the next reload or restart.",
                err
            )
            # Note: We still raise ConfigEntryNotReady for now to avoid partial state
            # A more robust solution would be to reconfigure coordinator for cloud-only
            raise ConfigEntryNotReady from err
        _LOGGER.error("Error setting up FranklinWH: %s", err)
        raise ConfigEntryNotReady from err

    # ... rest of setup ...
```

**Alternative (better):** Make the coordinator auto-switch to cloud-only mode after startup failures:
- On first Modbus failure, log warning and set `use_local_api = False`
- Subsequent updates use cloud path automatically
- User can re-enable Modbus via options flow

**Verification:**
- Integration loads even with unreachable Modbus
- Cloud data serves correctly
- Warning logged about startup Modbus failure

---

## Must Haves (Goal-Backward Verification)

| Must Have | Source | Verification |
|-----------|--------|--------------|
| MDATA-07: Energy totals use cloud data in Modbus mode | Phase requirement | In Modbus mode, `stats.totals` comes from cloud fetch fallback; energy sensors show non-zero values |
| MRES-01: Write operations use cloud API | Phase requirement | `async_set_operation_mode()` and `async_set_battery_reserve()` call `self.client` which uses cloud API; `async_set_switch_state()` calls `self.client` |
| MRES-02: Modbus failures fall back gracefully | Phase requirement | Modbus exceptions are caught and logged with warning; entities stay available; cloud fallback used |
| MRES-03: Startup Modbus failure doesn't block load | Phase requirement | Startup catches Modbus errors and logs warning; integration loads with cloud data |

---

## Wave Dependencies

- **Wave 1**: This is the only plan for Phase 6
- All requirements can be implemented in a single cohesive wave
- No dependencies on other phases

---

## Files Modified

1. `custom_components/franklin_wh/__init__.py` - Add startup resilience for Modbus failures
2. `custom_components/franklin_wh/coordinator.py` - Implement hybrid data strategy, cloud fallback, graceful degradation

---

## Test Plan

After Phase 6 completes, verify:

**Test 1: Energy Totals in Modbus Mode**
```python
# Enable local API, verify energy totals are non-zero
entry = MockConfigEntry(
    domain=DOMAIN,
    data={...},
    options={
        CONF_USE_LOCAL_API: True,
        CONF_LOCAL_HOST: "127.0.0.1",
    }
)
# Verify battery_charge, battery_discharge show cloud values
```

**Test 2: Modbus Failure Fallback**
```python
# Simulate Modbus timeout
# Verify warning logged
# Verify entities stay available
# Verify cloud data used for subsequent updates
```

**Test 3: Startup with Unreachable Modbus**
```python
# Configure Modbus with invalid host
# Verify integration loads successfully
# Verify warning logged about startup Modbus failure
# Verify cloud data serves correctly
```

**Test 4: Write Operations Use Cloud**
```python
# In Modbus mode, call set_operation_mode
# Verify client.get_stats() not called for writes
# Verify cloud API called for write operations
```

---

## Implementation Notes

1. **Cloud fallback should use executor** - HA's httpx client is not thread-safe
2. **Log appropriately** - Warnings for fallbacks, debug for normal operation
3. **Reset Modbus client on failure** - Allows recovery when Modbus becomes available
4. **Thread safety** - Use locks for lazy client initialization
5. **Don't break existing behavior** - Cloud-only mode should work exactly as before

---

## Success Criteria

- [ ] Energy total sensors show correct values in Modbus mode (from cloud)
- [ ] Modbus failures log warnings and entities stay available
- [ ] Cloud data serves as fallback during Modbus failures
- [ ] Integration loads successfully even when Modbus is unreachable at startup
- [ ] Write operations always use cloud API (no regression)
- [ ] All existing tests pass
- [ ] No new blocking calls on event loop
