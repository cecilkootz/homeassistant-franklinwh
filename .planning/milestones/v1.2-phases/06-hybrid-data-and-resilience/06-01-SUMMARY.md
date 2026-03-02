---
phase: 06-hybrid-data-and-resilience
plan: 01
subsystem: coordinator
tags: [modbus, sunspec, cloud-fallback, resilience, hybrid-data]

# Dependency graph
requires:
  - phase: 05-config-flow-and-coordinator-wiring
    provides: Modbus client wiring, config flow for Modbus settings
provides:
  - Hybrid data strategy: Modbus power flow + cloud energy totals
  - Graceful degradation: Modbus failures fall back to cloud automatically
  - Startup resilience: Integration loads even when Modbus unreachable
affects: [07-help]

# Tech tracking
tech-stack:
  added: []
  patterns: [executor-job-for-blocking-io, lazy-client-initialization, hybrid-data-fetch]

key-files:
  created: []
  modified:
    - custom_components/franklin_wh/coordinator.py
    - custom_components/franklin_wh/__init__.py

key-decisions:
  - "_fetch_cloud_stats_fallback() returns None on failure to avoid propagating exceptions"
  - "Modbus client reset on failure (_sunspec_client = None) allows recovery"
  - "Startup Modbus failures fall back to cloud-only mode with warning logged"

patterns-established:
  - "Executor pattern for cloud API calls (HA httpx not thread-safe)"
  - "Lazy client initialization with lock for thread safety"
  - "Dual-data strategy: Modbus for current values, cloud for totals"

requirements-completed: ["MDATA-07", "MRES-01", "MRES-02", "MRES-03"]

# Metrics
duration: 7min
completed: "2026-03-01"
---

# Phase 06-01: Hybrid Data Architecture and Resilience Summary

**Hybrid operation: Modbus power flow sensors plus cloud energy totals, with graceful fallback to cloud on Modbus failures**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-01T05:39:29Z
- **Completed:** 2026-03-01T05:46:25Z
- **Tasks:** 4
- **Files modified:** 2

## Accomplishments
- Hybrid data strategy: Modbus provides real-time power flow (solar, battery, grid, SOC, home_load) while cloud provides energy totals (kWh)
- Cloud fallback via `_fetch_cloud_stats_fallback()` - creates client lazily, fetches via executor, returns None on failure
- Graceful degradation: Modbus failures log warning and fall back to cloud - entities stay available with last known data
- Startup resilience: Integration loads successfully when Modbus is unreachable at startup

## Task Commits

Each task was committed atomically:

1. **Task 02: Cloud Stats Fetcher** - `1bcf916` (test)
2. **Task 01 & 03: Hybrid Strategy & Graceful Degradation** - `7c2569e` (feat)
3. **Task 04: Startup Resilience** - `e7a4da5` (feat)

**Plan metadata:** Reference commit history for documentation.

## Files Created/Modified
- `custom_components/franklin_wh/coordinator.py` - Added hybrid data strategy, cloud fallback fetcher, Modbus failure handling
- `custom_components/franklin_wh/__init__.py` - Added startup Modbus failure handling

## Decisions Made
- `_fetch_cloud_stats_fallback()` returns `None` on failure to avoid propagating exceptions that would mark entities unavailable
- Modbus client reset (`self._sunspec_client = None`) on failure allows recovery when Modbus becomes available again
- Startup Modbus failures log warning and continue with cloud-only mode; stores flag to disable on next reload
- Cloud stats and switch_state fetched via `hass.async_add_executor_job()` to avoid blocking event loop

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added switch state population in hybrid mode**
- **Found during:** Task 01 (Hybrid data strategy)
- **Issue:** Original plan used `switch_state=None` in Modbus mode; MRES-01 requires switch operations via cloud API but switch state should still be fetched for UI
- **Fix:** Added `cloud_stats.switch_state if cloud_stats else None` in hybrid response
- **Files modified:** custom_components/franklin_wh/coordinator.py
- **Verification:** Switch state properly populated when cloud fallback succeeds
- **Committed in:** 7c2569e

**2. [Rule 3 - Blocking] Added cloud fallback for startup Modbus failures**
- **Found during:** Task 04 (Startup resilience)
- **Issue:** Original implementation raised `ConfigEntryNotReady` on any startup failure; needed to distinguish Modbus from authentication errors
- **Fix:** Added error string matching for "sunspec", "modbus", "connection", "timeout" to detect Modbus-specific failures
- **Files modified:** custom_components/franklin_wh/__init__.py
- **Verification:** Integration loads with cloud-only mode when Modbus unreachable at startup
- **Committed in:** e7a4da5

---

**Total deviations:** 2 auto-fixed (1 missing critical functionality, 1 blocking issue)
**Impact on plan:** Both auto-fixes enhanced correctness and user experience. No scope creep - all additions directly support the plan's success criteria.

## Issues Encountered
- None - all tasks executed as specified with minor auto-fixes for robustness

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Hybrid data architecture complete, ready for testing
- Cloud fallback mechanism established for graceful degradation
- Write operations (set_operation_mode, set_battery_reserve, smart switches) continue using cloud API (no regression)
- All existing patterns maintained (executor jobs, lazy client initialization)

---

*Phase: 06-hybrid-data-and-resilience*
*Completed: 2026-03-01*
