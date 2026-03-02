---
phase: 07-fix-runtime-integration-bugs
plan: "01"
subsystem: coordinator, integration-setup
tags: [bug-fix, modbus, hybrid-data, async]
dependency_graph:
  requires: [06-01]
  provides: [MCONF-01, MDATA-06, MDATA-07]
  affects: [__init__.py, coordinator.py]
tech_stack:
  added: []
  patterns: [options-with-data-fallback, direct-await-async-client]
key_files:
  created: []
  modified:
    - custom_components/franklin_wh/__init__.py
    - custom_components/franklin_wh/coordinator.py
decisions:
  - "Use nested .get() for options-with-data-fallback so explicit False in options is honored (not short-circuited by 'or' operator)"
  - "franklinwh client uses async httpx — direct await is correct; async_add_executor_job was an incorrect wrapping"
metrics:
  duration: 5 min
  completed: "2026-03-01"
  tasks_completed: 2
  files_modified: 2
---

# Phase 07 Plan 01: Fix Runtime Integration Bugs Summary

Two surgical bug fixes for wiring mistakes identified in the v1.2 milestone audit: Modbus settings not read from entry.data on first setup, and async cloud client methods incorrectly wrapped in executor jobs.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Fix entry.data / entry.options split in __init__.py | f4c8ea2 | custom_components/franklin_wh/__init__.py |
| 2 | Fix async coroutine calls in coordinator.py _fetch_cloud_stats_fallback | 8f76efa | custom_components/franklin_wh/coordinator.py |

## What Was Built

**Bug 1 — Modbus not activating on first setup (MCONF-01, MDATA-06)**

`__init__.py` was reading all four Modbus config keys (`CONF_USE_LOCAL_API`, `CONF_LOCAL_HOST`, `CONF_LOCAL_PORT`, `CONF_LOCAL_SLAVE_ID`) exclusively from `entry.options`. On first setup, `entry.options` is always empty — HA only populates it after the options flow runs. This meant `use_local_api` was always `False` on first load, silently disabling Modbus even when the user configured it during setup.

Fix: nested `.get()` pattern — `entry.options.get(KEY, entry.data.get(KEY, default))` — so options-flow users (non-empty options) get options values, and first-setup users get entry.data values.

**Bug 2 — Energy totals silently returning None in hybrid mode (MDATA-07)**

`_fetch_cloud_stats_fallback()` was wrapping `self.client.get_stats()` and `self.client.get_smart_switch_state()` in `async_add_executor_job()`. The franklinwh client uses async httpx which is not a blocking synchronous library — it is an async coroutine. Passing a coroutine function to `async_add_executor_job` returns a coroutine object without awaiting it; `stats` received a coroutine object instead of data, causing the function to fail silently and return None.

Fix: replace both executor-wrapped calls with direct `await self.client.get_stats()` and `await self.client.get_smart_switch_state()`. All surrounding try/except blocks and None-return-on-failure contract preserved.

## Decisions Made

- Use nested `.get()` for the fallback pattern (not the `or` operator) so an explicit `False` stored by the options flow is honored rather than short-circuited to check entry.data
- The misleading comment "HA's httpx is not thread-safe" was removed — the franklinwh client is async-native and belongs on the event loop

## Verification

```
__init__.py OK
coordinator.py OK
```

Four `entry.data.get` matches in `__init__.py` (one per Modbus config key). No `async_add_executor_job` calls for `get_stats` or `get_smart_switch_state` in coordinator.py. Direct await pattern found at both the non-Modbus path (lines 145, 159) and `_fetch_cloud_stats_fallback` (lines 284, 291).

## Deviations from Plan

None - plan executed exactly as written.

## Requirements Met

- MCONF-01: Modbus activates on first setup — `use_local_api=True` and `local_host` are correctly read from entry.data when options is empty
- MDATA-06: 10-second update interval applies as designed when Modbus is configured on first setup
- MDATA-07: `_fetch_cloud_stats_fallback()` successfully awaits async coroutines, returning FranklinWHData with energy totals instead of silently returning None

## Self-Check: PASSED

- f4c8ea2 exists in git log
- 8f76efa exists in git log
- custom_components/franklin_wh/__init__.py modified with four entry.data.get fallbacks
- custom_components/franklin_wh/coordinator.py modified with direct await calls
