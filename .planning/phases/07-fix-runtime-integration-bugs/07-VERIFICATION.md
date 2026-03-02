---
phase: 07-fix-runtime-integration-bugs
verified: 2026-03-01T00:00:00Z
status: passed
score: 4/4 must-haves verified
gaps: []
---

# Phase 07: Fix Runtime Integration Bugs — Verification Report

**Phase Goal:** Fix runtime integration bugs that prevent Modbus from activating on first setup and energy totals from working in hybrid mode.
**Verified:** 2026-03-01
**Status:** PASSED
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `__init__.py` reads Modbus settings from `entry.options` first, falling back to `entry.data` for all four keys | VERIFIED | Lines 44–47 of `__init__.py` use nested `.get()` pattern for all four keys: `CONF_USE_LOCAL_API`, `CONF_LOCAL_HOST`, `CONF_LOCAL_PORT`, `CONF_LOCAL_SLAVE_ID` |
| 2 | `_fetch_cloud_stats_fallback()` calls `self.client.get_stats()` and `self.client.get_smart_switch_state()` with direct `await`, not `async_add_executor_job` | VERIFIED | Lines 284 and 291 of `coordinator.py` use `await self.client.get_stats()` and `await self.client.get_smart_switch_state()` respectively. Zero `async_add_executor_job` calls remain anywhere in the file. |
| 3 | The misleading executor comment at coordinator.py line 283 is removed or corrected | VERIFIED | The comment "Fetch stats via executor (HA's httpx is not thread-safe)" is absent. No executor comment exists in `_fetch_cloud_stats_fallback()`. |
| 4 | `_fetch_cloud_stats_fallback()` retains all existing try/except blocks and None-return-on-failure contract | VERIFIED | Lines 283–301 preserve the outer try/except (lines 283/296–298), inner switch_state try/except (lines 290/292–293), None-guard on stats (line 285–287), and None returns on all failure paths. |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `custom_components/franklin_wh/__init__.py` | Modbus settings read with options-then-data fallback | VERIFIED | Lines 44–47 implement nested `.get()` pattern exactly as specified. Syntax valid. Committed at f4c8ea2. |
| `custom_components/franklin_wh/coordinator.py` | `_fetch_cloud_stats_fallback()` uses direct await for cloud client calls | VERIFIED | Lines 284, 291 use direct `await`. No `async_add_executor_job` for cloud methods. Syntax valid. Committed at 8f76efa. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `__init__.py` `async_setup_entry` | `FranklinWHCoordinator.__init__()` | `use_local_api`, `local_host`, `local_port`, `local_slave_id` kwargs | WIRED | Lines 50–59: all four Modbus values passed as kwargs to coordinator constructor. `entry.data` path correctly surfaces first-setup values. |
| `_fetch_cloud_stats_fallback()` | `FranklinWHData` return with energy totals | `await self.client.get_stats()` | WIRED | Line 284 awaits `get_stats()`, result assigned to `stats`. Line 295 constructs and returns `FranklinWHData(stats=stats, switch_state=switch_state)`. |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| MCONF-01 | 07-01-PLAN.md | User who configures Modbus during initial setup has `use_local_api=True` and `local_host` set when coordinator initializes | SATISFIED | `entry.data.get(CONF_USE_LOCAL_API, False)` and `entry.data.get(CONF_LOCAL_HOST)` are now the fallback when `entry.options` is empty (first setup). Coordinator receives correct values. |
| MDATA-06 | 07-01-PLAN.md | Integration polls Modbus at 10-second interval when local Modbus is enabled | SATISFIED | MDATA-06 is contingent on `use_local_api` being `True`. With Bug 1 fixed, first-setup users with Modbus configured will now correctly enable the 10-second polling path. No coordinator polling logic was changed (it was already correct). |
| MDATA-07 | 07-01-PLAN.md | Sensors with no Modbus equivalent continue to use cloud data when local Modbus is enabled | SATISFIED | `_fetch_cloud_stats_fallback()` now correctly awaits async cloud client calls, returning `FranklinWHData` with energy totals instead of silently returning `None`. |

No orphaned requirements: all three requirement IDs declared in the plan are accounted for.

Note from REQUIREMENTS.md traceability table: MCONF-01 is listed under "Phase 5" as the original delivery phase. Phase 7 fixes the runtime bug that prevented it from working correctly on first setup — a bug-fix pass, not a re-delivery. The REQUIREMENTS.md correctly marks MCONF-01 as complete.

### Anti-Patterns Found

None. Both modified files are syntactically valid. No TODO/FIXME/placeholder patterns. No stub returns. No empty implementations.

### Human Verification Required

#### 1. Modbus activates on first setup (end-to-end)

**Test:** Configure a new integration entry with Modbus enabled (host, port, slave ID filled in). Restart HA without visiting the options flow. Check that the coordinator uses the 10-second poll interval and Modbus sensors populate.
**Expected:** Modbus sensors show live data within 10 seconds of startup. No "use_local_api=False" in debug logs.
**Why human:** Requires a real HA instance with a FranklinWH gateway and Modbus device. Cannot verify actual coordinator branching programmatically without runtime execution.

#### 2. Energy totals appear in hybrid mode (end-to-end)

**Test:** With Modbus enabled, observe that `battery_charge_kwh` and similar energy total sensors display values (not "unavailable").
**Expected:** Cloud fallback path returns real stats; energy total sensors show numeric values.
**Why human:** Requires live cloud API access and a real gateway. Cannot verify async httpx behavior or actual cloud response handling without runtime execution.

## Gaps Summary

No gaps. All four must-have truths are verified. Both artifacts exist, are substantive, and are correctly wired. Commits f4c8ea2 and 8f76efa exist in git log and implement exactly the changes specified in the plan.

---

_Verified: 2026-03-01_
_Verifier: Claude (gsd-verifier)_
