---
phase: 04-modbus-client-layer
verified: 2026-02-28T00:00:00Z
status: passed
score: 9/9 must-haves verified
re_verification: false
---

# Phase 4: Modbus Client Layer Verification Report

**Phase Goal:** A standalone SunSpec Modbus TCP client exists that reads the four required models and returns typed data without blocking the HA event loop
**Verified:** 2026-02-28
**Status:** PASSED
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | pysunspec2==1.3.3 appears in manifest.json requirements array | VERIFIED | Line 12 of manifest.json: `"requirements": ["pysunspec2==1.3.3"]` |
| 2 | SunSpecData dataclass exists with fields: battery_soc, battery_dc_power, solar_power, grid_ac_power, home_load | VERIFIED | sunspec_client.py lines 18-39: all five fields present with type annotations |
| 3 | SunSpecModbusClient class accepts host, port, slave_id constructor arguments | VERIFIED | sunspec_client.py line 57: `def __init__(self, host: str, port: int, slave_id: int) -> None` stored as `_host`, `_port`, `_slave_id` |
| 4 | All Modbus I/O is wrapped in synchronous _read_blocking() — never on HA event loop | VERIFIED | sunspec_client.py lines 69-155: connect/scan/read/disconnect all inside `_read_blocking()`; async `read()` body contains only `await hass.async_add_executor_job(self._read_blocking)` |
| 5 | read() is async and dispatches _read_blocking via hass.async_add_executor_job() | VERIFIED | sunspec_client.py line 166: `return await hass.async_add_executor_job(self._read_blocking)` |
| 6 | home_load is computed as solar_power + battery_dc_power - grid_ac_power | VERIFIED | sunspec_client.py line 136: `home_load = solar_power + battery_dc_power - grid_ac_power` |
| 7 | Model 502 absence is handled with a guard and descriptive RuntimeError | VERIFIED | sunspec_client.py lines 100-107: `if 502 not in device.models: raise RuntimeError(...)` with full inspection guidance |
| 8 | Model 714 DCW falls back to summing port-group values if model-level DCW is None | VERIFIED | sunspec_client.py lines 122-131: reads `DCW.cvalue`, if None sums `DCSrc` group with debug log |
| 9 | HA will pip-install pysunspec2 (PyPI distribution name, not sunspec2) | VERIFIED | manifest.json uses `pysunspec2==1.3.3` (PyPI name), not `sunspec2` (import name) |

**Score:** 9/9 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `custom_components/franklin_wh/manifest.json` | pysunspec2==1.3.3 in requirements | VERIFIED | File exists, valid JSON, requirements array contains exactly `"pysunspec2==1.3.3"`, no other fields changed |
| `custom_components/franklin_wh/sunspec_client.py` | SunSpecData dataclass and SunSpecModbusClient class | VERIFIED | 167-line file, fully implemented, no stubs or placeholders |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `SunSpecModbusClient.read()` | `SunSpecModbusClient._read_blocking()` | `hass.async_add_executor_job` | WIRED | Line 166: `return await hass.async_add_executor_job(self._read_blocking)` |
| `SunSpecModbusClient._read_blocking()` | `device.models[713/714/701/502]` | `device.scan()` then `model.read()` | WIRED | Lines 95, 110-113: `device.scan(connect=False, full_model_read=False)` followed by individual `model[N][0].read()` calls |
| `manifest.json` | `PyPI pysunspec2` | requirements array entry | WIRED | `"pysunspec2==1.3.3"` present in requirements array; correct PyPI distribution name used |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| MDATA-01 | 04-01, 04-02 | Read battery SoC from Model 713 | SATISFIED | `float(device.models[713][0].SoC.cvalue)` → `battery_soc` field in SunSpecData |
| MDATA-02 | 04-01, 04-02 | Read battery DC power from Model 714 | SATISFIED | `device.models[714][0].DCW.cvalue` with DCSrc fallback → `battery_dc_power` field |
| MDATA-03 | 04-01, 04-02 | Read solar production from Model 502 | SATISFIED | `float(device.models[502][0].OutPw.cvalue)` → `solar_power` field (with model 502 guard) |
| MDATA-04 | 04-01, 04-02 | Read grid AC power from Model 701 | SATISFIED | `float(device.models[701][0].W.cvalue)` → `grid_ac_power` field |
| MDATA-05 | 04-02 | Calculate home load: `solar + battery_dc - grid_ac` | SATISFIED | `home_load = solar_power + battery_dc_power - grid_ac_power` (line 136) with SunSpec sign conventions documented |

No orphaned requirements: MDATA-06 and MDATA-07 are mapped to Phase 5 and Phase 6 respectively in REQUIREMENTS.md — correctly out of scope for Phase 4.

### Anti-Patterns Found

None. No TODO/FIXME/HACK/placeholder comments, no empty implementations, no stub returns.

### Human Verification Required

#### 1. Real Hardware Validation — Model 502 Presence

**Test:** Connect to a live FranklinWH aGate and observe whether `device.models.keys()` includes model 502 after `scan()`.
**Expected:** Either model 502 is present and solar power is read correctly, or the RuntimeError fires with useful guidance identifying which model actually provides solar data.
**Why human:** The FranklinWH SunSpec Alliance registry lists models 1 and 701-715 only. Model 502 absence is a documented open question that requires real hardware to resolve.

#### 2. Real Hardware Validation — Model 714 DCW Fallback Path

**Test:** On a live device, verify whether `device.models[714][0].DCW.cvalue` returns a non-None value or requires the DCSrc port-group fallback.
**Expected:** Either the model-level value is populated (fallback path never triggers) or the debug log "Model 714 model-level DCW is None" appears and the per-port sum produces a correct watt value.
**Why human:** Which code path executes depends on firmware behavior that cannot be determined without a real device.

### Gaps Summary

No gaps. All automated checks passed.

---

_Verified: 2026-02-28_
_Verifier: Claude (gsd-verifier)_
