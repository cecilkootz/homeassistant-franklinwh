# Requirements: homeassistant-franklinwh

**Defined:** 2026-02-27
**Core Value:** FranklinWH energy management data and controls in Home Assistant via first-class HACS integration

## v1.2 Requirements

### Modbus Configuration (MCONF)

- [ ] **MCONF-01**: User can optionally configure a Modbus TCP host, port (default 502), and slave ID (default 1) during initial integration setup
- [ ] **MCONF-02**: User can enable or disable local Modbus mode via the options flow without re-entering cloud credentials

### Modbus Data (MDATA)

- [ ] **MDATA-01**: Integration reads battery state of charge from SunSpec Model 713 when local Modbus is enabled
- [ ] **MDATA-02**: Integration reads battery DC power (charge/discharge) from SunSpec Model 714 when local Modbus is enabled
- [ ] **MDATA-03**: Integration reads solar production power from SunSpec Model 502 when local Modbus is enabled
- [ ] **MDATA-04**: Integration reads grid AC power from SunSpec Model 701 when local Modbus is enabled
- [ ] **MDATA-05**: Integration calculates home load from Modbus data using the formula `solar_power + battery_dc_power − grid_ac_power` (SunSpec sign conventions: discharge/export positive). This is a best-effort calculation; values may differ slightly from cloud-reported home load due to DC bus measurements (Models 502, 714) being mixed with AC bus measurements (Model 701) without inverter efficiency correction.
- [ ] **MDATA-06**: Integration polls Modbus at 10-second interval when local Modbus is enabled (vs 60s cloud)
- [ ] **MDATA-07**: Sensors with no Modbus equivalent (energy totals: battery_charge kWh, battery_discharge kWh, etc.) continue to use cloud data when local Modbus is enabled

### Modbus Resilience (MRES)

- [ ] **MRES-01**: Write operations (set_operation_mode, set_battery_reserve, smart switches) continue using the cloud API when local Modbus is enabled
- [ ] **MRES-02**: Modbus connection failures fall back gracefully (entities stay available with last known data) and log a warning
- [ ] **MRES-03**: If Modbus is configured but unreachable at startup, integration loads successfully using cloud data only

## Future Requirements

### Testing

- **TEST-01**: Unit tests for Modbus client and SunSpec model parsing
- **TEST-02**: Integration tests for coordinator hybrid mode

## Out of Scope

| Feature | Reason |
|---------|--------|
| Modbus write operations (set_operation_mode via Modbus) | No confirmed SunSpec register mapping for FranklinWH mode control |
| Replacing cloud credentials entirely | Cloud still required for write operations and energy totals |
| Adding unit/integration tests | Separate milestone concern |
| Fixing BUG-01 (config_flow executor/coroutine) | Pre-existing, deferred |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| MCONF-01 | Phase 5 | Pending |
| MCONF-02 | Phase 5 | Pending |
| MDATA-01 | Phase 4 | Pending |
| MDATA-02 | Phase 4 | Pending |
| MDATA-03 | Phase 4 | Pending |
| MDATA-04 | Phase 4 | Pending |
| MDATA-05 | Phase 4 | Pending |
| MDATA-06 | Phase 5 | Pending |
| MDATA-07 | Phase 6 | Pending |
| MRES-01 | Phase 6 | Pending |
| MRES-02 | Phase 6 | Pending |
| MRES-03 | Phase 6 | Pending |

**Coverage:**
- v1.2 requirements: 11 total
- Mapped to phases: 11
- Unmapped: 0 ✓

---
*Requirements defined: 2026-02-27*
*Last updated: 2026-02-27 after initial definition*
