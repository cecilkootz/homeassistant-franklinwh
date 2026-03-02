---
phase: 08-fix-options-listener-and-grid-polarity
verified: 2026-03-01T19:30:00Z
status: passed
score: 4/4 must-haves verified
---

# Phase 08: Fix Options Listener and Grid Polarity — Verification Report

**Phase Goal:** Fix two runtime integration bugs found by the v1.2 milestone audit — options flow listener not registered (MCONF-02) and grid polarity sign inverted (MDATA-04).
**Verified:** 2026-03-01T19:30:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #   | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 1   | `async_setup_entry` in `__init__.py` calls `entry.add_update_listener(async_reload_entry)` unconditionally, after `async_forward_entry_setups` | VERIFIED | Line 104 of `__init__.py` — directly follows `async_forward_entry_setups` at line 101, no enclosing `if` block |
| 2   | `sensor.py` `grid_use` `value_fn` does not apply `* -1` — returns `data.stats.current.grid_use` directly | VERIFIED | Line 99 of `sensor.py`: `lambda data: data.stats.current.grid_use if data.stats else None` — no `* -1` present |
| 3   | `coordinator.py` line 233 is unchanged — `grid_use = -sunspec_data.grid_ac_power / 1000.0` remains the sole sign normalization | VERIFIED | `grep` confirms line 233: `grid_use=-sunspec_data.grid_ac_power / 1000.0` — untouched |
| 4   | `async_reload_entry` function in `__init__.py` is not modified — still calls `async_unload_entry` then `async_setup_entry` | VERIFIED | `async_reload_entry` body confirmed: `await async_unload_entry(hass, entry)` then `await async_setup_entry(hass, entry)` |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Status | Details |
| -------- | ------ | ------- |
| `custom_components/franklin_wh/__init__.py` | VERIFIED | Syntactically valid (AST parse OK); `add_update_listener` present once, unconditionally, after `async_forward_entry_setups` |
| `custom_components/franklin_wh/sensor.py` | VERIFIED | Syntactically valid (AST parse OK); `grid_use` `value_fn` is sign-neutral — no `* -1` |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| Options flow save | `async_reload_entry` | `entry.add_update_listener` in `async_setup_entry` | WIRED | Line 104 of `__init__.py` registers the listener unconditionally; `async_reload_entry` calls unload then setup |
| `grid_use` sensor | coordinator value | `data.stats.current.grid_use` (no modifier) | WIRED | `sensor.py:99` reads value directly; `coordinator.py:233` is the single negation point |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| MCONF-02 | 08-01-PLAN.md | User can enable/disable local Modbus via options flow without re-entering credentials — options changes take effect without HA restart | SATISFIED | `add_update_listener(async_reload_entry)` wired unconditionally at `__init__.py:104`; `async_reload_entry` reloads coordinator with new options |
| MDATA-04 | 08-01-PLAN.md | Integration reads grid AC power from SunSpec Model 701; reports positive when importing — single negation in coordinator is canonical | SATISFIED | `coordinator.py:233` applies single negation; `sensor.py:99` `value_fn` is sign-neutral — double inversion removed |

Both requirements marked Complete in REQUIREMENTS.md at lines 11 and 19 respectively. No orphaned requirements.

### Anti-Patterns Found

None detected in modified files. No TODOs, FIXMEs, placeholder returns, or empty handlers introduced.

### Human Verification Required

#### 1. Options flow end-to-end reload

**Test:** In a running Home Assistant instance, open the FranklinWH integration, enter Options, toggle "Use local Modbus", and save.
**Expected:** The integration reloads without requiring an HA restart. Entities briefly become unavailable then restore with the new mode active.
**Why human:** Requires a live HA instance with the integration loaded — cannot verify the HA config entry lifecycle programmatically.

#### 2. Grid polarity in live Modbus mode

**Test:** With local Modbus enabled and the Franklin WH system importing power from the grid, observe the `sensor.franklin_wh_grid_use` value.
**Expected:** Value is positive when importing (consuming from grid), negative when exporting (sending to grid).
**Why human:** Requires physical hardware and a live Modbus connection to confirm sign convention is correct end-to-end.

### Gaps Summary

No gaps. Both MCONF-02 and MDATA-04 are fully addressed:

- `__init__.py` now registers `entry.add_update_listener(async_reload_entry)` unconditionally after platform setup, closing MCONF-02.
- `sensor.py` `grid_use` `value_fn` no longer applies `* -1`, leaving `coordinator.py:233` as the single canonical sign normalization point, closing MDATA-04.

Both files pass AST syntax validation. The `async_reload_entry` function and `coordinator.py:233` are confirmed untouched.

---

_Verified: 2026-03-01T19:30:00Z_
_Verifier: Claude (gsd-verifier)_
