---
gsd_state_version: 1.0
milestone: v1.2
milestone_name: SunSpec/Modbus Local API
status: completed
last_updated: "2026-03-01T22:53:43.475Z"
progress:
  total_phases: 5
  completed_phases: 4
  total_plans: 7
  completed_plans: 5
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-01 after v1.2 milestone)

**Core value:** FranklinWH energy management data and controls in Home Assistant via first-class HACS integration
**Current focus:** Planning next milestone

## Current Position

Phase: 6 — Hybrid Data and Resilience
Plan: 06-01 (completed)
Status: Phase complete
Last activity: 2026-03-01 — Phase 06 execution completed

Progress: [████████░░] 100% (v1.2 in progress)

## Performance Metrics

**Velocity:**
- Total plans completed: 6
- Average duration: 9 min
- Total execution time: 54 min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 03-vendor-and-wire-http-client | 2/2 | 18 min | 9 min |
| 04-modbus-client-layer | 2/2 | 20 min | 10 min |
| 05-config-flow-and-coordinator-wiring | 2/2 | 7 min | 3.5 min |
| 06-hybrid-data-and-resilience | 1/1 | 7 min | 7 min |

*Updated after each plan completion*
| Phase 04 P01 | 2 | 1 tasks | 1 files |
| Phase 04 P02 | 5 | 1 tasks | 1 files |
| Phase 05 P01 | 2 | 2 tasks | 2 files |
| Phase 05 P02 | 3 | 3 tasks | 3 files |
| Phase 06 P01 | 1 | 4 tasks | 2 files |
| Phase 07 P01 | 5 | 2 tasks | 2 files |
| Phase 08-fix-options-listener-and-grid-polarity P01 | 5 | 2 tasks | 2 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Prior milestone decisions preserved for context:

- [v1.0 Setup]: Move files via `git mv` to preserve git history
- [v1.0 01-01]: Used Python to edit hacs.json to avoid manual JSON formatting errors
- [v1.0 02-01]: manifest.json keys must be alphabetically sorted after domain/name (hassfest requirement)
- [v1.0 02-01]: validate.yaml was disabled_fork on GitHub — enabled via API
- [v1.1 03-01]: Vendor franklinwh PyPI library verbatim into custom_components to allow targeted modifications without forking
- [v1.1 03-01]: TokenFetcher injected session called directly (not as context manager) since HA manages the client lifecycle
- [v1.1 03-01]: Client falls back to get_client() when no session injected, preserving upstream behavior
- [Phase 03-02]: Pass HA httpx session into both TokenFetcher and Client at construction (not stored globally)
- [Phase 03-02]: franklinwh removed from manifest.json requirements as it is now fully vendored
- [Phase 04-01]: Use PyPI distribution name pysunspec2 (not sunspec2) in manifest.json — sunspec2 would fail HA pip install
- [Phase 04-02]: Model 502 guard raises RuntimeError with hardware inspection guidance; model uncertainty documented as open question
- [Phase 04-02]: No exception catching in sunspec_client — exceptions propagate to coordinator for retry/fallback
- [Phase 05-01]: Added CONF_LOCAL_PORT, CONF_LOCAL_SLAVE_ID, DEFAULT_LOCAL_PORT, DEFAULT_LOCAL_SLAVE_ID to const.py
- [Phase 05-01]: Activated Modbus fields in config_flow.py async_step_user and async_step_init
- [Phase 05-02]: Updated coordinator with local_port/slave_id params and SunSpecModbusClient integration
- [Phase 05-02]: Updated __init__.py to read Modbus settings from entry.options
- [Phase 06-01]: Hybrid data strategy - Modbus for power flow, cloud for energy totals and switch state
- [Phase 06-01]: Cloud fallback via _fetch_cloud_stats_fallback() returns None on failure (no exception propagation)
- [Phase 06-01]: Modbus client reset on failure allows recovery when Modbus becomes available again
- [Phase 06-01]: Startup Modbus failures log warning and continue with cloud-only mode
- [Phase 07]: Use nested .get() for options-with-data-fallback so explicit False in options is honored
- [Phase 07]: franklinwh client uses async httpx — direct await is correct; async_add_executor_job was an incorrect wrapping
- [Phase 08]: add_update_listener placed unconditionally after async_forward_entry_setups — options changes always handled
- [Phase 08]: coordinator.py:233 is canonical sign normalization for grid_use; sensor.py value_fn is sign-neutral

### v1.2 Implementation Notes

- pySunSpec2 (`sunspec2` PyPI package) is synchronous blocking I/O — must run in executor, never on the HA event loop
- Phase 05 completed: Modbus config flow constants and coordinator wiring are implemented
- Phase 06 completed: Hybrid data strategy and resilience mechanisms implemented
- User can configure Modbus host, port (502 default), slave ID (1 default) during setup
- Local mode can be toggled via options flow without re-entering cloud credentials
- When local mode enabled, coordinator polls Modbus at 10s interval; otherwise 60s for cloud
- Energy totals (kWh) are fetched from cloud when Modbus is enabled (MDATA-07)
- Modbus failures fall back to cloud automatically with warning logged (MRES-02)
- Integration loads successfully even when Modbus unreachable at startup (MRES-03)

### Pending Todos

None - Phase 06 complete, v1.2 milestone in progress.

### Blockers/Concerns

None.

## Session Continuity

Last session: 2026-03-01
Stopped at: Phase 06-01 execution completed
Resume file: None

## Phase 06 Summary

**Status:** v1.2 milestone complete

**Plans Executed:**
- 06-01: Hybrid Data Architecture and Resilience (4 tasks)

**Files Modified:**
- custom_components/franklin_wh/coordinator.py - Hybrid data strategy, cloud fallback fetcher, graceful degradation
- custom_components/franklin_wh/__init__.py - Startup resilience for Modbus failures

**Requirements Met:**
- MDATA-07: Energy total sensors use cloud data when local Modbus is enabled
- MRES-01: Write operations (set_operation_mode, set_battery_reserve, smart switches) use cloud API
- MRES-02: Modbus connection failures fall back gracefully (entities stay available)
- MRES-03: Integration loads successfully when Modbus unreachable at startup

**Verification:** See 06-01-SUMMARY.md

## Phase 05 Summary

**Status:** COMPLETE

**Plans Executed:**
- 05-01: Modbus Configuration Constants and Config Flow Activation (2 tasks)
- 05-02: Coordinator Wiring and Options Storage (3 tasks)

**Files Modified:**
- custom_components/franklin_wh/const.py - Added 4 Modbus constants
- custom_components/franklin_wh/config_flow.py - Activated Modbus fields in 2 flows
- custom_components/franklin_wh/__init__.py - Read options, pass to coordinator
- custom_components/franklin_wh/coordinator.py - SunSpecModbusClient integration

**Verification:** PASSED - See 05-VERIFICATION.md
