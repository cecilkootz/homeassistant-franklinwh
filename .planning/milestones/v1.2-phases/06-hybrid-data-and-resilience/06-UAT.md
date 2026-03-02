---
status: testing
phase: 06-hybrid-data-and-resilience
source: [06-01-SUMMARY.md]
started: 2026-03-01T06:00:00Z
updated: 2026-03-01T06:00:00Z
---

## Current Test

<!-- OVERWRITE each test - shows where we are -->

number: 1
name: Integration Loads with Modbus Unreachable
expected: |
  When Modbus is unreachable at startup, the integration still loads successfully
  in cloud-only mode (does not raise ConfigEntryNotReady). A warning is logged but
  all entities remain available using cloud data.
awaiting: user response

## Tests

### 1. Integration Loads with Modbus Unreachable
expected: When Modbus is unreachable at startup, the integration still loads successfully in cloud-only mode (does not raise ConfigEntryNotReady). A warning is logged but all entities remain available using cloud data.
result: [pending]

### 2. Real-Time Power Flow Sensors from Modbus
expected: When Modbus is reachable, sensors for solar power, battery power, grid power, home load, and battery SOC show real-time values (updated each poll cycle, not just from cloud).
result: [pending]

### 3. Energy Totals from Cloud
expected: Energy total sensors (kWh values) are populated from the cloud API, not Modbus. These should show cumulative energy figures distinct from the real-time power flow readings.
result: [pending]

### 4. Graceful Degradation on Modbus Failure
expected: When Modbus becomes unreachable during operation (after a successful start), entities remain available with their last known values. A warning is logged, but no entities become unavailable/unknown due to the Modbus failure alone.
result: [pending]

### 5. Switch State in Hybrid Mode
expected: Smart switch state is available in the UI even when the integration is running in hybrid mode (Modbus + cloud). The switch state is fetched from the cloud API alongside energy totals.
result: [pending]

## Summary

total: 5
passed: 0
issues: 0
pending: 5
skipped: 0

## Gaps

[none yet]
