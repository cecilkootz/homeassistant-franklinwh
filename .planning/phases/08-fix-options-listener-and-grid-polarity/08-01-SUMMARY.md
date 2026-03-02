---
phase: 08-fix-options-listener-and-grid-polarity
plan: "01"
subsystem: integration
tags: [home-assistant, config-entry, options-flow, sensor, modbus, grid-power]

requires:
  - phase: 06-hybrid-data-and-resilience
    provides: coordinator hybrid data strategy with Modbus and cloud paths
  - phase: 05-config-flow-and-coordinator-wiring
    provides: options flow and Modbus config constants

provides:
  - Options flow changes (toggle local Modbus) now trigger coordinator reload via add_update_listener
  - grid_use sensor reports correct polarity (positive = importing from grid) in both cloud and Modbus modes

affects: [coordinator, sensor, config-entry, options-flow]

tech-stack:
  added: []
  patterns:
    - "Options update listener registered unconditionally after async_forward_entry_setups"
    - "Single sign normalization point: coordinator.py is canonical, sensor.py is sign-neutral"

key-files:
  created: []
  modified:
    - custom_components/franklin_wh/__init__.py
    - custom_components/franklin_wh/sensor.py

key-decisions:
  - "add_update_listener placed after async_forward_entry_setups, unconditionally — no conditional guard"
  - "coordinator.py:233 is the single canonical negation point for grid_use; sensor.py value_fn is sign-neutral"

patterns-established:
  - "Sign normalization belongs in coordinator, not in sensor value_fn"

requirements-completed: [MCONF-02, MDATA-04]

duration: 5min
completed: 2026-03-01
---

# Phase 08 Plan 01: Fix Options Listener and Grid Polarity Summary

**Surgical 2-file patch: options flow now reloads coordinator on save, and grid_use polarity is corrected by removing duplicate * -1 in sensor.py**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-01T19:10:00Z
- **Completed:** 2026-03-01T19:15:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- MCONF-02 fixed: `entry.add_update_listener(async_reload_entry)` registered unconditionally in `async_setup_entry`, so toggling local Modbus in the options flow now takes effect without an HA restart
- MDATA-04 fixed: removed `* -1` from `grid_use` `value_fn` in sensor.py — coordinator.py already applies the single correct negation at line 233

## Task Commits

Each task was committed atomically:

1. **Task 1: Register options update listener in async_setup_entry** - `7048f26` (fix)
2. **Task 2: Remove double negation from grid_use sensor** - `5e0ea65` (fix)

**Plan metadata:** (docs commit follows)

## Files Created/Modified
- `custom_components/franklin_wh/__init__.py` - Added `entry.add_update_listener(async_reload_entry)` after `async_forward_entry_setups`
- `custom_components/franklin_wh/sensor.py` - Removed `* -1` from `grid_use` value_fn

## Decisions Made
- Listener added unconditionally (not inside any `if use_local_api`) so all options changes are handled regardless of mode
- coordinator.py line 233 left untouched — it is the canonical sign normalization point for both cloud and Modbus paths

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Both audit gaps (MCONF-02, MDATA-04) closed
- v1.2 milestone requirements fully satisfied
- No known remaining gaps

---
*Phase: 08-fix-options-listener-and-grid-polarity*
*Completed: 2026-03-01*
