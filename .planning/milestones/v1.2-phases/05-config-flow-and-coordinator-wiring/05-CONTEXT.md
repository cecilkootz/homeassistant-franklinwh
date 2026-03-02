# Phase 5: Config Flow and Coordinator Wiring - Context

**Gathered:** 2026-02-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire Modbus host/port/slave ID into the setup and options flows, and connect the coordinator to `SunSpecModbusClient` so it polls at 10s when local mode is enabled. Cloud-only behavior must be identical to pre-v1.2 when local mode is disabled.

</domain>

<decisions>
## Implementation Decisions

### Setup flow placement
- Modbus fields (host, port, slave ID) appear on the same screen as cloud credentials (username, password, gateway ID)
- All Modbus fields are optional — user can leave them blank to skip local mode during setup
- Default values: port=502, slave ID=1

### Options flow scope
- Options flow has a toggle to enable/disable local Modbus mode
- Options flow also exposes host, port, and slave ID fields — user can reconfigure without reinstalling
- This replaces the commented-out `CONF_USE_LOCAL_API` / `CONF_LOCAL_HOST` stubs already in the flow

### Config storage
- All Modbus settings (use_local_api, host, port, slave_id) stored in `entry.options`, not `entry.data`
- Allows runtime changes via options flow without reinstalling the integration
- `entry.data` holds only cloud credentials (username, password, gateway_id) — unchanged from today

### Toggle behavior
- Toggling local mode in options takes effect immediately — no HA restart required
- Options save triggers a coordinator reload (HA standard pattern: `async_reload_entry`)
- Coordinator re-initializes with new options on reload; poll interval switches live

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `CONF_USE_LOCAL_API`, `CONF_LOCAL_HOST` already defined in `const.py` — need to add `CONF_LOCAL_PORT` and `CONF_LOCAL_SLAVE_ID`
- `DEFAULT_LOCAL_SCAN_INTERVAL = 10` already in `const.py`
- Coordinator already accepts `use_local_api` / `local_host` constructor params and selects scan interval — needs port/slave_id and actual `SunSpecModbusClient` wiring
- Config flow Modbus fields already commented out in `async_step_user()` — ready to activate
- Options flow Modbus fields similarly commented out in `async_step_init()` — ready to activate
- `SunSpecModbusClient` and `SunSpecData` built in Phase 4 at `sunspec_client.py`

### Established Patterns
- Options changes trigger reload via `async_reload_entry` — standard HA pattern, already used in reauth flow
- Coordinator reads `entry.options` for `scan_interval` today — extend this pattern for Modbus options
- `entry.data` vs `entry.options` split already established: data=credentials, options=tunables

### Integration Points
- `coordinator.py`: `FranklinWHCoordinator.__init__()` gains `local_port` and `local_slave_id` params; `_async_update_data()` gains branch to call `SunSpecModbusClient` when `use_local_api` is True
- `__init__.py`: coordinator instantiation reads Modbus options from `entry.options`
- `config_flow.py`: uncomment/activate the local API fields in both setup step and options step
- `const.py`: add `CONF_LOCAL_PORT` and `CONF_LOCAL_SLAVE_ID` constants

</code_context>

<specifics>
## Specific Ideas

- No specific reference UX mentioned — standard HA config flow patterns apply
- Modbus fields in setup are optional and clearly separated from required cloud fields (via `vol.Optional`)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 05-config-flow-and-coordinator-wiring*
*Context gathered: 2026-02-28*
