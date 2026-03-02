---
phase: 04-modbus-client-layer
plan: "02"
subsystem: modbus-client
tags: [sunspec, modbus, pysunspec2, executor, dataclass]
dependency_graph:
  requires:
    - pysunspec2==1.3.3 (already in manifest.json)
  provides:
    - SunSpecData dataclass
    - SunSpecModbusClient class
  affects:
    - coordinator.py (Phase 5 will import SunSpecModbusClient)
tech_stack:
  added:
    - pysunspec2==1.3.3 (already pinned in manifest.json from 04-01)
  patterns:
    - connect-per-read Modbus lifecycle
    - hass.async_add_executor_job for blocking pySunSpec2 I/O
    - .cvalue for scale-factor-applied SunSpec point reads
key_files:
  created:
    - custom_components/franklin_wh/sunspec_client.py
  modified: []
decisions:
  - "Model 502 guard raises RuntimeError with hardware inspection guidance rather than returning 0; solar model uncertainty documented as open question for real hardware validation"
  - "Model 714 DCW fallback: reads model-level sum first; if None, sums DCSrc port group values; mirrors research recommendation"
  - "No exception catching in client — exceptions propagate to coordinator (Phase 5) for retry/fallback, consistent with existing consecutive-failure pattern"
metrics:
  duration: "5 min"
  completed: "2026-02-28"
  tasks_completed: 1
  files_created: 1
  files_modified: 0
---

# Phase 4 Plan 02: SunSpec Modbus Client Summary

**One-liner:** SunSpecModbusClient class with pySunSpec2 connect-per-read lifecycle, executor dispatch, and typed SunSpecData return for Models 502/701/713/714.

## What Was Built

`custom_components/franklin_wh/sunspec_client.py` — a new standalone file providing:

- **SunSpecData** — `@dataclass` with five fields: `battery_soc`, `battery_dc_power`, `solar_power`, `grid_ac_power`, `home_load`. All power values in watts with SunSpec sign conventions documented per-field.
- **SunSpecModbusClient** — class with `__init__(host, port, slave_id)`, synchronous `_read_blocking()`, and async `read(hass)`.

## Implementation Details

The client uses a connect-per-read lifecycle (CONTEXT.md decision). `_read_blocking()` creates a fresh `SunSpecModbusClientDeviceTCP` on each call, runs `connect()`, `scan(connect=False, full_model_read=False)`, individual `model.read()` calls, value extraction with `.cvalue`, and `disconnect()` in a `finally` block.

`read(hass)` is the sole async entry point and dispatches `_read_blocking` via `hass.async_add_executor_job`, ensuring no blocking Modbus I/O ever runs on the HA event loop.

### home_load Formula

```python
home_load = solar_power + battery_dc_power - grid_ac_power
```

Uses native SunSpec sign conventions without negation: Model 701 W (positive=export), Model 714 DCW (positive=discharge), Model 502 OutPw (positive=production).

### Model 502 Guard

FranklinWH's SunSpec Alliance registry lists models 1 and 701-715 — model 502 is not registered. After `scan()`, the client checks `502 not in device.models` and raises a `RuntimeError` with instructions to inspect `device.models.keys()` on real hardware.

### Model 714 DCW Fallback

Reads model-level `DCW.cvalue` first. If `None`, sums `DCSrc` port group per-port DCW values with a debug log. If the device only populates per-port values (see research open question 2), the fallback handles it transparently.

## Deviations from Plan

None — plan executed exactly as written.

The verify assertion in the plan used `'502 in device.models'` but the implementation correctly uses `'502 not in device.models'` (the guard condition). The structural check was adjusted to match the correct guard form.

## Self-Check

### Files Created

- [x] `custom_components/franklin_wh/sunspec_client.py` — FOUND

### Commits

- [x] `c3b63cd` feat(04-02): add SunSpecModbusClient and SunSpecData — FOUND

## Self-Check: PASSED
