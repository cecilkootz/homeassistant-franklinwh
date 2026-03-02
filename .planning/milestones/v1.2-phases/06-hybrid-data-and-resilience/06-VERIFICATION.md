---
phase: 06-hybrid-data-and-resilience
verified: 2026-03-01T05:00:00Z
status: passed
score: 4/4 must-haves verified
re_verification:
  previous_status: passed
  previous_score: 4/4
  gaps_closed: []
  gaps_remaining: []
  regressions: []
---

# Phase 06: Hybrid Data Architecture and Resilience Verification Report

**Phase Goal:** Sensors without Modbus equivalents use cloud data, and Modbus failures never mark the integration unavailable.
**Verified:** 2026-03-01T05:00:00Z
**Status:** passed
**Re-verification:** Yes — regression check against previous passing verification

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | Energy total sensors (battery_charge kWh, battery_discharge kWh, etc.) report cloud values when local Modbus is enabled | VERIFIED | `coordinator.py` lines 120-131: `_fetch_cloud_stats_fallback()` called in Modbus path, `cloud_stats.totals` used for `Stats.totals` |
| 2  | Write operations (set_operation_mode, set_battery_reserve, smart switches) always route to the cloud API regardless of Modbus mode | VERIFIED | Lines 310, 338, 370: all three write methods call `self.client` (cloud API) directly |
| 3  | When Modbus connection fails mid-operation, entities remain available showing last known data and a warning is logged | VERIFIED | Lines 133-142: all exceptions caught, warning logged, `_sunspec_client` reset to None, fall-through to cloud path |
| 4  | If Modbus is configured but unreachable at HA startup, the integration loads successfully and serves cloud data | VERIFIED | `__init__.py` lines 67-93: startup exceptions checked for Modbus keywords; when `use_local_api and is_modbus_error`, warning logged and setup continues without re-raising |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `custom_components/franklin_wh/coordinator.py` | Hybrid data strategy implementation | VERIFIED | Contains `_fetch_cloud_stats_fallback()` (lines 260-304), Modbus exception handling with cloud fallback (lines 133-142), hybrid Stats construction (lines 126-132) |
| `custom_components/franklin_wh/__init__.py` | Startup resilience implementation | VERIFIED | Lines 67-93 handle Modbus failures at startup; Modbus keyword check determines whether to re-raise or continue |
| `FranklinWHCoordinator._fetch_cloud_stats_fallback()` | Cloud fallback fetcher | VERIFIED | Lines 260-304; thread-safe via `async_add_executor_job`, returns None on failure, never propagates exceptions |
| `FranklinWHCoordinator._map_sunspec_to_stats_current()` | SunSpec to Stats.current mapping | VERIFIED | Lines 220-240; maps Modbus watts to kW, sets default values for fields unavailable via Modbus |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `coordinator.py:_async_update_data()` | `_fetch_cloud_stats_fallback()` | Await call in Modbus path | WIRED | Line 121 calls method; lines 129-131 consume `cloud_stats.totals` and `cloud_stats.switch_state` |
| `coordinator.py:_async_update_data()` | `_map_sunspec_to_stats_current()` | Maps SunSpecData to Stats.current | WIRED | Line 128 calls method with `sunspec_data` result |
| `__init__.py:async_setup_entry()` | Cloud fallback on Modbus startup failure | Exception handler with keyword detection | WIRED | Lines 69-75 build `is_modbus_error`; line 77 gates cloud-continue path |
| `async_set_operation_mode()` | `client.set_mode()` | Cloud API call | WIRED | Line 338 |
| `async_set_battery_reserve()` | `client.set_mode()` | Cloud API call | WIRED | Line 370 |
| `async_set_switch_state()` | `client.set_smart_switch_state()` | Cloud API call | WIRED | Line 310 |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| MDATA-07 | 06-PLAN.md | Energy totals continue using cloud data when local Modbus is enabled | SATISFIED | `coordinator.py` lines 120-131: Modbus path fetches cloud totals via `_fetch_cloud_stats_fallback()` and uses them in `Stats(totals=...)` |
| MRES-01 | 06-PLAN.md | Write operations use cloud API regardless of Modbus mode | SATISFIED | All three write methods (`async_set_switch_state`, `async_set_operation_mode`, `async_set_battery_reserve`) call `self.client` which is the cloud API client |
| MRES-02 | 06-PLAN.md | Modbus connection failures fall back gracefully; entities stay available; warning logged | SATISFIED | Lines 133-142: exception caught, `_LOGGER.warning(...)` called, `_sunspec_client = None` to reset, execution falls through to cloud path; plus general failure counter (lines 174-218) keeps entities available for up to 3 failures |
| MRES-03 | 06-PLAN.md | If Modbus unreachable at startup, integration loads successfully using cloud data | SATISFIED | `__init__.py` lines 67-93: `ConfigEntryAuthFailed` re-raised; all other exceptions during `use_local_api` startup that match Modbus keywords are caught, warning logged, and setup continues |

No orphaned requirements. REQUIREMENTS.md traceability table confirms MDATA-07, MRES-01, MRES-02, MRES-03 all assigned to Phase 6 with status Complete.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `coordinator.py` | 242-258 | `_get_default_totals()` returns all zeros | INFO | This is the last-resort fallback when both Modbus and cloud fetch fail; expected behavior for resilience, not a stub |
| `coordinator.py` | 367 | TODO comment about mode type detection | INFO | Pre-existing limitation in `async_set_battery_reserve`; unrelated to Phase 6 requirements |

No blockers or warnings.

### Human Verification Required

None — all functionality is deterministic and verifiable through code inspection.

### Gaps Summary

No gaps. All four requirements are implemented and verified. Code matches the claims from the previous verification. No regressions detected.

1. **MDATA-07** — Hybrid strategy implemented: Modbus provides real-time power flow (current values), cloud provides energy totals (kWh)
2. **MRES-01** — All three write methods call the cloud `self.client` directly, unaffected by `use_local_api` flag
3. **MRES-02** — Mid-operation Modbus failures caught, warning logged, `_sunspec_client` reset, cloud path used for that cycle
4. **MRES-03** — Startup exception handler distinguishes Modbus errors from auth errors; Modbus errors allow setup to complete

---

_Verified: 2026-03-01T05:00:00Z_
_Verifier: Claude (gsd-verifier)_
