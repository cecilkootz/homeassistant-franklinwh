# Phase 4: Modbus Client Layer - Context

**Gathered:** 2026-02-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Build a standalone `SunSpecModbusClient` class that connects to a Modbus TCP host and reads SunSpec Models 502 (solar inverter), 701 (AC meter/grid), 713 (battery SOC), and 714 (battery DC power). Returns a typed data object with `battery_soc`, `battery_dc_power`, `solar_power`, `grid_ac_power`, and computed `home_load`. All Modbus I/O runs in an executor — never on the HA event loop. Config flow wiring and coordinator integration are Phase 5.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion

User deferred all implementation decisions to Claude. The following are standard approaches the planner should apply:

- **Connection lifecycle** — Use connect/disconnect per read (simpler, more resilient for infrequent polling). Persistent connections are an optimization for Phase 5+ if needed.
- **Failure contract** — Raise exceptions on Modbus failure. Let the coordinator (Phase 5) handle retry/fallback logic, consistent with the existing consecutive-failure pattern in `coordinator.py`.
- **Unit & sign normalization** — Return values in watts (W) as floats, using SunSpec sign conventions (discharge/export positive). Document the sign convention clearly in code. The home_load formula is fixed: `solar_power + battery_dc_power - grid_ac_power`.
- **sunspec2 usage mode** — Target models directly by address rather than auto-discovery scans. Faster, more predictable for a known device.
- **File placement** — New file `custom_components/franklin_wh/sunspec_client.py` containing `SunSpecModbusClient` class and a `SunSpecData` dataclass for the return type.

</decisions>

<specifics>
## Specific Ideas

- `sunspec2` must be added to `manifest.json` requirements array
- Return type should be a `@dataclass` named `SunSpecData` (consistent with existing `FranklinWHData` dataclass pattern)
- Class name: `SunSpecModbusClient` (specified in roadmap success criteria)
- Fields required: `battery_soc`, `battery_dc_power`, `solar_power`, `grid_ac_power`, `home_load`

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `FranklinWHData` dataclass in `coordinator.py`: Existing pattern for typed return objects — `SunSpecData` should follow same `@dataclass` structure
- `hass.async_add_executor_job()`: Already used in `config_flow.py` for blocking calls — same pattern applies here

### Established Patterns
- Dataclasses for data holders: `@dataclass class FranklinWHData` — use same for `SunSpecData`
- Exception-based error signaling: coordinator catches `UpdateFailed`; Modbus client should raise standard exceptions that Phase 5 coordinator can catch
- Module-level logger: `_LOGGER = logging.getLogger(__name__)` in every file
- Type hints throughout: all parameters and return types annotated

### Integration Points
- `manifest.json` — add `sunspec2` to `requirements` list
- `coordinator.py` (Phase 5) — will import and call `SunSpecModbusClient` from `sunspec_client.py`
- No existing Modbus or SunSpec code in codebase — this is net-new

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 04-modbus-client-layer*
*Context gathered: 2026-02-27*
