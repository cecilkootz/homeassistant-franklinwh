# Phase 5: Config Flow and Coordinator Wiring - Research

**Researched:** 2026-02-28
**Domain:** Home Assistant integration configuration flows and Modbus/Coordinator integration
**Confidence:** HIGH

## Summary

Phase 5 enables users to configure Modbus TCP settings (host, port, slave ID) during integration setup and toggle local mode via options flow. The coordinator must be wired to use `SunSpecModbusClient` for polling at 10-second intervals when local mode is enabled, while maintaining cloud API as the fallback for writes and energy totals.

This phase builds on Phase 4's `SunSpecModbusClient` which handles synchronous PySunSpec2 I/O via HA's executor. The key technical challenge is integrating the synchronous Modbus client into the async coordinator update loop with proper fallback behavior.

**Primary recommendation:** Add `CONF_LOCAL_PORT` and `CONF_LOCAL_SLAVE_ID` constants; uncomment and enhance config flow Modbus fields in both `async_step_user()` and `async_step_init()`; update coordinator to use `SunSpecModbusClient` when `use_local_api=True`; store all Modbus settings in `entry.options`.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| voluptuous | latest | Config flow schema validation | HA standard for config flows |
| pysunspec2 | 1.3.3 | Modbus SunSpec client | Manifest dependency, Phase 4 established |
| homeassistant.helpers.config_validation | built-in | Input validation helpers | HA standard |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| sunspec2.modbus.client | 1.3.3 | Modbus TCP device connectivity | Used via pysunspec2, connect-per-read pattern |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `pysunspec2` | Custom Modbus implementation | High complexity, sunspec2 has model parsing built-in |
| Dataclass for config | TypedDict | Dataclass provides better type safety at runtime |

**Installation:**
```bash
# pysunspec2 already in manifest.json requirements
# No additional dependencies required
```

## Architecture Patterns

### Recommended Project Structure
```
custom_components/franklin_wh/
├── __init__.py           # Coordinator instantiation from entry.options
├── const.py              # CONF_LOCAL_PORT, CONF_LOCAL_SLAVE_ID
├── config_flow.py        # Modbus fields in setup/options
├── coordinator.py        # SunSpecModbusClient integration
├── sunspec_client.py     # Phase 4 - existing, unchanged
└── sensor.py             # Unchanged (reads coordinator.data)
```

### Pattern 1: HA Config Flow Options Pattern
**What:** Store tunable settings in `entry.options` vs credentials in `entry.data`; use `async_reload_entry` for runtime changes.

**When to use:** When options need to change without reinstalling the integration.

**Example:**
```python
# From Phase 5 CONTEXT.md (user decision)
# All Modbus settings stored in entry.options, not entry.data
# Options save triggers coordinator reload via async_reload_entry

class FranklinWHOptionsFlow(config_entries.OptionsFlow):
    def async_step_init(self, user_input=None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Get current values from entry.options
        scan_interval = self.config_entry.options.get(
            "scan_interval", DEFAULT_SCAN_INTERVAL
        )
        return self.async_show_form(step_id="init", data_schema=data_schema)
```

**Source:** Phase 5 CONTEXT.md user decisions, HA config flow best practices.

### Pattern 2: Executor Wrapping for Blocking I/O
**What:** Wrap synchronous blocking I/O (PySunSpec2 Modbus) in `hass.async_add_executor_job()`.

**When to use:** When using synchronous libraries in async Home Assistant context.

**Example:**
```python
# From sunspec_client.py (Phase 4)
class SunSpecModbusClient:
    async def read(self, hass: HomeAssistant) -> SunSpecData:
        """Dispatches blocking I/O to executor."""
        return await hass.async_add_executor_job(self._read_blocking)
```

**Source:** sunspec_client.py Phase 4 implementation.

### Pattern 3: Coordinator Hybrid Update Path
**What:** Select Modbus vs cloud data source based on `use_local_api` flag in `_async_update_data()`.

**When to use:** Hybrid mode where Modbus is primary but cloud is fallback.

**Example:**
```python
# From coordinator.py
class FranklinWHCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, username, password, gateway_id,
                 use_local_api=False, local_host=None):
        self.use_local_api = use_local_api
        self.local_host = local_host
        # ... init SunSpecModbusClient when use_local_api=True

    async def _async_update_data(self) -> FranklinWHData:
        if self.use_local_api and self.local_host:
            # Use Modbus client
            sunspec_data = await self.sunspec_client.read(self.hass)
            return self._map_sunspec_to_franklinwh_data(sunspec_data)
        else:
            # Use cloud API
            stats = await self.client.get_stats()
            return FranklinWHData(stats=stats)
```

**Source:** Phase 5 CONTEXT.md code insights section.

### Anti-Patterns to Avoid
- **Modbus client creation per update:** Creates excessive connections; create once in `__init__` or lazy-initialize on first use.
- **Blocking I/O on event loop:** Never call `device.connect()` or `read()` directly in `_async_update_data()`; always use executor.
- **Storing Modbus settings in entry.data:** Prevents runtime changes; use `entry.options` per user decision.
- **No fallback on Modbus failure:** Entities become unavailable; implement retry/fallback to cloud.
- **Hardcoded port/slave_id:** Must be configurable per user decision.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Modbus SunSpec client | Custom PyModbus implementation | `pysunspec2==1.3.3` | SunSpec model parsing is complex; pysunspec2 handles scale factors, model scanning, per-model reading |
| Config flow validation | Manual schema validation | `voluptuous` + `cv.string`, `vol.All` | HA standard, built-in error messages, type coercion |
| Dataclass schema | Manual dict validation | `@dataclass` with type hints | Type safety, IDE autocomplete, runtime validation |
| Option change reload | Manual entity reload | `async_reload_entry` | HA standard pattern, handles platform reload |

**Key insight:** pysunspec2 is the ecosystem-standard library for SunSpec/Modbus in Home Assistant integrations. The Phase 4 research confirmed it's synchronous and must be wrapped in executor.

## Common Pitfalls

### Pitfall 1: PySunSpec2 is Synchronous Blocking I/O
**What goes wrong:** Calling `SunSpecModbusClientDeviceTCP.connect()` or `.read()` directly in async context blocks HA event loop, causing warnings and timeout errors.

**Why it happens:** PySunSpec2 uses modbus-tk under the hood which is synchronous; the async wrapper in sunspec_client.py is essential.

**How to avoid:** Always use `SunSpecModbusClient.read(hass)` which wraps `_read_blocking()` in `hass.async_add_executor_job()`. Never call `_read_blocking()` directly.

**Warning signs:** HA log shows "Executing executor job" warnings, or `async_timeout` exceptions in coordinator.

### Pitfall 2: Modbus Connection Failures Break Entities
**What goes wrong:** Modbus timeout/connection error makes all entities unavailable until HA restart.

**Why it happens:** No exception handling in Modbus read path; exceptions propagate and coordinator marks unavailable after max failures.

**How to avoid:** Let exceptions propagate from `SunSpecModbusClient` (per Phase 4 decision); coordinator already has retry/fallback logic that keeps entities available with last known data. Ensure `SunSpecModbusClient` raises proper exceptions (RuntimeError, SunSpecModbusClientTimeout, etc.) so coordinator can distinguish between temporary failures and fatal errors.

**Warning signs:** Entities show "unavailable" state after Modbus network glitch.

### Pitfall 3: Config Entry Data/Options Confusion
**What goes wrong:** Storing Modbus settings in `entry.data` requires uninstall/reinstall for changes; user expects options flow to work.

**Why it happens:** Old code pattern or misunderstanding of HA's config entry design.

**How to avoid:** Per Phase 5 CONTEXT.md user decision: `entry.data` holds only cloud credentials (username, password, gateway_id); `entry.options` holds all Modbus settings (use_local_api, host, port, slave_id). Coordinator reads from `entry.options`.

**Warning signs:** User changes Modbus settings in options flow but integration doesn't update until restart.

### Pitfall 4: Missing Scan Interval in Coordinator Reinit
**What goes wrong:** Coordinator scan interval doesn't change when user toggles local mode in options flow.

**Why it happens:** Coordinator `update_interval` set in `__init__` but not updated when options change; `async_reload_entry` recreates coordinator but must pass new options.

**How to avoid:** Coordinator reads `use_local_api` from `entry.options` on each reload. Per Phase 5 CONTEXT.md: "Options flow toggle takes effect immediately - no HA restart required; coordinator re-initializes with new options on reload."

**Warning signs:** After toggling local mode in options, coordinator still uses old scan interval.

## Code Examples

Verified patterns from existing code:

### Setting Up Modbus Constants
**Source:** const.py - existing stubs need completion

```python
from typing import Final

# Configuration - existing stubs:
CONF_USE_LOCAL_API: Final = "use_local_api"
CONF_LOCAL_HOST: Final = "local_host"

# ADD these (per Phase 5 CONTEXT.md):
CONF_LOCAL_PORT: Final = "local_port"
CONF_LOCAL_SLAVE_ID: Final = "slave_id"

# Default values:
DEFAULT_LOCAL_SCAN_INTERVAL: Final = 10  # seconds for local API
DEFAULT_LOCAL_PORT: Final = 502
DEFAULT_LOCAL_SLAVE_ID: Final = 1
```

### Config Flow Schema with Optional Modbus Fields
**Source:** config_flow.py - commented fields ready to activate

```python
import voluptuous as vol
from homeassistant.helpers import config_validation as cv

# In async_step_user():
data_schema = vol.Schema(
    {
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_GATEWAY_ID): cv.string,
        # Local API - OPTIONAL fields
        vol.Optional(CONF_USE_LOCAL_API, default=False): cv.boolean,
        vol.Optional(CONF_LOCAL_HOST): cv.string,
        vol.Optional(CONF_LOCAL_PORT, default=502): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=65535)
        ),
        vol.Optional(CONF_LOCAL_SLAVE_ID, default=1): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=255)
        ),
    }
)
```

### Coordinator Initialization with Modbus Client
**Source:** coordinator.py - needs SunSpecModbusClient wiring

```python
from .sunspec_client import SunSpecModbusClient

class FranklinWHCoordinator(DataUpdateCoordinator[FranklinWHData]):
    def __init__(
        self,
        hass: HomeAssistant,
        username: str,
        password: str,
        gateway_id: str,
        use_local_api: bool = False,
        local_host: str | None = None,
        local_port: int = 502,
        local_slave_id: int = 1,
    ) -> None:
        # ... existing init code ...

        # Store Modbus config
        self.use_local_api = use_local_api
        self.local_host = local_host
        self.local_port = local_port
        self.local_slave_id = local_slave_id

        # Lazy-initialize SunSpecModbusClient (created on first use)
        self._sunspec_client: SunSpecModbusClient | None = None

    async def _async_update_data(self) -> FranklinWHData:
        # When local API is enabled
        if self.use_local_api and self.local_host:
            if self._sunspec_client is None:
                self._sunspec_client = SunSpecModbusClient(
                    host=self.local_host,
                    port=self.local_port,
                    slave_id=self.local_slave_id,
                )

            # Read from Modbus
            sunspec_data = await self._sunspec_client.read(self.hass)

            # Map SunSpecData to FranklinWHData
            return FranklinWHData(
                stats=Stats(
                    current=Current(
                        solar_production=sunspec_data.solar_power / 1000,
                        battery_use=sunspec_data.battery_dc_power / 1000,
                        grid_use=-sunspec_data.grid_ac_power / 1000,
                        home_load=sunspec_data.home_load / 1000,
                        battery_soc=sunspec_data.battery_soc,
                        # Other fields as defaults
                        generator_production=0.0,
                        generator_enabled=False,
                        switch_1_load=0.0,
                        switch_2_load=0.0,
                        v2l_use=0.0,
                        grid_status=GridStatus.NORMAL,
                    ),
                    totals=Totals(
                        battery_charge=0.0,  # Not available via Modbus
                        battery_discharge=0.0,
                        grid_import=0.0,
                        grid_export=0.0,
                        solar=0.0,
                        generator=0.0,
                        home_use=0.0,
                        switch_1_use=0.0,
                        switch_2_use=0.0,
                        v2l_export=0.0,
                        v2l_import=0.0,
                    ),
                ),
                # Switch state from cloud fallback
                switch_state=None,
            )

        # Cloud API path (existing code)
        stats = await self.client.get_stats()
        return FranklinWHData(stats=stats)
```

### __init__.py - Reading Modbus Options
**Source:** __init__.py - needs coordinator instantiation update

```python
from .const import (
    CONF_GATEWAY_ID,
    CONF_LOCAL_HOST,
    CONF_LOCAL_PORT,
    CONF_LOCAL_SLAVE_ID,
    CONF_USE_LOCAL_API,
    DOMAIN,
)
from .coordinator import FranklinWHCoordinator

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    gateway_id = entry.data[CONF_GATEWAY_ID]

    # Read Modbus settings from entry.options (not entry.data)
    use_local_api = entry.options.get(CONF_USE_LOCAL_API, False)
    local_host = entry.options.get(CONF_LOCAL_HOST)
    local_port = entry.options.get(CONF_LOCAL_PORT, 502)
    local_slave_id = entry.options.get(CONF_LOCAL_SLAVE_ID, 1)

    coordinator = FranklinWHCoordinator(
        hass=hass,
        username=username,
        password=password,
        gateway_id=gateway_id,
        use_local_api=use_local_api,
        local_host=local_host,
        local_port=local_port,
        local_slave_id=local_slave_id,
    )

    hass.data[DOMAIN][entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hardcoded local API port | Configurable port via options | Phase 5 | User can specify non-standard Modbus ports |
| No local API option | Optional local API with Modbus fallback | Phase 5 | Users can choose cloud-only or hybrid mode |
| Separate config reinstall for options | Runtime options via `async_reload_entry` | Phase 5 | No HA restart needed for config changes |

**Deprecated/outdated:**
- `CONF_USE_LOCAL_API` / `CONF_LOCAL_HOST` only in code but not functional: Stubs were placeholders; Phase 5 makes them functional with full Modbus config (port, slave_id).
- Storing Modbus settings in `entry.data`: Prevents runtime changes; `entry.options` is the HA-standard pattern for tunable settings.

## Open Questions

1. **Model 502 absence on real hardware**
   - What we know: sunspec_client.py raises RuntimeError if model 502 is not found after scan; the error message instructs user to inspect `device.models.keys()`.
   - What's unclear: Whether real FranklinWH aGate devices actually have model 502 or use a different model for solar production.
   - Recommendation: The Phase 4 design is correct for discovery - let exceptions propagate to coordinator for graceful fallback. No action needed for Phase 5.

2. **Scan interval per Modbus vs cloud**
   - What we know: Phase 5 requires 10-second interval when local mode is enabled, 60s for cloud.
   - What's unclear: Should scan interval be configurable separately for each mode, or is the fixed 10s/60s split sufficient?
   - Recommendation: Follow user decision: "Polling at 10s when local mode enabled" implies fixed intervals. Add `scan_interval` to options flow only if user requests finer control.

3. **Coordinator reload timing**
   - What we know: User decision says "toggle takes effect immediately via async_reload_entry".
   - What's unclear: Are there any cleanup tasks needed before reload (e.g., closing Modbus connections)?
   - Recommendation: `SunSpecModbusClient._read_blocking()` already disconnects in `finally` block, so no explicit cleanup needed. `async_reload_entry` is sufficient.

## Validation Architecture

> Skip this section entirely if workflow.nyquist_validation is false in .planning/config.json

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | tests/conftest.py (needs Wave 0 creation) |
| Quick run command | `pytest tests/test_config_flow.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MCONF-01 | User can configure Modbus host, port (502), slave ID (1) during setup | unit | `pytest tests/test_config_flow.py::test_async_step_user_with_modbus -x` | ❌ Wave 0 |
| MCONF-02 | User can enable/disable local mode via options flow | unit | `pytest tests/test_config_flow.py::test_async_step_init_toggle_local_mode -x` | ❌ Wave 0 |
| MDATA-06 | Integration polls Modbus at 10s interval when local mode enabled | unit | `pytest tests/test_coordinator.py::test_update_interval_local_mode -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_config_flow.py tests/test_coordinator.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_config_flow.py` — tests for config flow Modbus fields
- [ ] `tests/test_coordinator.py` — tests for coordinator Modbus client integration
- [ ] `tests/conftest.py` — shared fixtures (mock coordinator, entry, etc.)
- [ ] Framework install: `pytest` already in requirements-dev.txt if exists

*(If no gaps: "None — existing test infrastructure covers all phase requirements")*

## Sources

### Primary (HIGH confidence)
- `/Users/matt/Development/homeassistant-franklinwh/custom_components/franklin_wh/sunspec_client.py` - SunSpecModbusClient implementation with executor wrapping
- `/Users/matt/Development/homeassistant-franklinwh/custom_components/franklin_wh/coordinator.py` - DataUpdateCoordinator with retry/fallback pattern
- `/Users/matt/Development/homeassistant-franklinwh/custom_components/franklin_wh/config_flow.py` - Current config flow with commented Modbus stubs
- `/Users/matt/Development/homeassistant-franklinwh/custom_components/franklin_wh/__init__.py` - Integration setup, entry data/options handling
- `/Users/matt/Development/homeassistant-franklinwh/custom_components/franklin_wh/const.py` - Configuration constants
- `/Users/matt/Development/homeassistant-franklinwh/.planning/phases/05-config-flow-and-coordinator-wiring/05-CONTEXT.md` - User decisions constraining research
- `/Users/matt/Development/homeassistant-franklinwh/.planning/REQUIREMENTS.md` - Phase requirement IDs MCONF-01, MCONF-02, MDATA-06

### Secondary (MEDIUM confidence)
- Home Assistant config flow documentation - voluptuous schema patterns, options flow with `async_reload_entry`
- PySunSpec2 library (pysunspec2 1.3.3) - synchronous Modbus client, must use executor

### Tertiary (LOW confidence)
- None identified - all claims verified against source files or documentation.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - pysunspec2 1.3.3 is explicitly in manifest.json; voluptuous is HA built-in
- Architecture: HIGH - All patterns verified in existing codebase; Phase 4 established sunspec_client pattern
- Pitfalls: HIGH - All pitfalls identified from Phase 4 learnings and current code structure

**Research date:** 2026-02-28
**Valid until:** 2026-03-28 (30 days for stable patterns)

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MCONF-01 | User can optionally configure Modbus TCP host, port (default 502), and slave ID (default 1) during initial integration setup | Config flow schema uses vol.Optional for Modbus fields with defaults; validation uses vol.All with Coerce(int) and Range |
| MCONF-02 | User can enable or disable local Modbus mode via the options flow without re-entering cloud credentials | Options flow reads/writes to entry.options; async_reload_entry triggers coordinator re-init with new settings |
| MDATA-06 | Integration polls Modbus at 10-second interval when local Modbus is enabled (vs 60s cloud) | Coordinator update_interval set based on use_local_api flag; DEFAULT_LOCAL_SCAN_INTERVAL = 10 in const.py |

## User Constraints (from CONTEXT.md)

### Locked Decisions

**Setup flow placement:**
- Modbus fields (host, port, slave ID) appear on the same screen as cloud credentials (username, password, gateway ID)
- All Modbus fields are optional — user can leave them blank to skip local mode during setup
- Default values: port=502, slave ID=1

**Options flow scope:**
- Options flow has a toggle to enable/disable local Modbus mode
- Options flow also exposes host, port, and slave ID fields — user can reconfigure without reinstalling
- This replaces the commented-out `CONF_USE_LOCAL_API` / `CONF_LOCAL_HOST` stubs already in the flow

**Config storage:**
- All Modbus settings (use_local_api, host, port, slave_id) stored in `entry.options`, not `entry.data`
- Allows runtime changes via options flow without reinstalling the integration
- `entry.data` holds only cloud credentials (username, password, gateway_id) — unchanged from today

**Toggle behavior:**
- Toggling local mode in options takes effect immediately — no HA restart required
- Options save triggers a coordinator reload (HA standard pattern: `async_reload_entry`)
- Coordinator re-initializes with new options on reload; poll interval switches live

### Claude's Discretion

None specified in CONTEXT.md.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
