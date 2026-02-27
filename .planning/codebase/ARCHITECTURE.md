# Architecture

**Analysis Date:** 2026-02-27

## Pattern Overview

**Overall:** Home Assistant Integration Hub Pattern

This is a Home Assistant custom integration implementing a hub-based architecture that bridges the FranklinWH energy management system with Home Assistant. The integration follows Home Assistant's platform-based entity system with a centralized data coordinator.

**Key Characteristics:**
- Integration entry point based on `ConfigEntry` (Home Assistant's configuration management)
- Data aggregation and update coordination via `DataUpdateCoordinator`
- Platform-based entity system (Sensors and Switches)
- Async-first architecture with Home Assistant reactor integration
- Cloud API polling with configurable scan intervals
- Multi-service support (operation mode and battery reserve control)

## Layers

**Entry Layer:**
- Purpose: Initialize integration, register services, and manage lifecycle
- Location: `__init__.py`
- Contains: Main setup function, platform registration, service registration
- Depends on: Coordinator, const, Home Assistant config entries API
- Used by: Home Assistant when loading custom integrations

**Data Layer (Coordinator):**
- Purpose: Fetch and manage data from FranklinWH cloud API, cache state
- Location: `coordinator.py`
- Contains: `FranklinWHCoordinator` (DataUpdateCoordinator subclass), `FranklinWHData` (data model)
- Depends on: `franklinwh` library (TokenFetcher, Client, Mode, Stats), Home Assistant helpers
- Used by: All platform entities, services

**Platform Layer - Sensors:**
- Purpose: Expose FranklinWH device metrics as read-only Home Assistant sensors
- Location: `sensor.py`
- Contains: Entity descriptions, `FranklinWHSensorEntity` class, 24+ sensor definitions
- Depends on: Coordinator, Home Assistant sensor components
- Used by: Home Assistant entity registry and automations

**Platform Layer - Switches:**
- Purpose: Expose FranklinWH smart switches and grid connection as controllable switches
- Location: `switch.py`
- Contains: `FranklinWHSmartSwitch`, `GridSwitch` classes
- Depends on: Coordinator, Home Assistant switch components
- Used by: Home Assistant entity registry and automations

**Configuration Layer:**
- Purpose: Handle user setup, validation, and authentication flows
- Location: `config_flow.py`
- Contains: `FranklinWHConfigFlow`, `FranklinWHOptionsFlow`, validation helpers, custom exceptions
- Depends on: `franklinwh` library, Home Assistant config entries API
- Used by: Home Assistant during user onboarding and credential updates

**Support Layers:**
- Constants: `const.py` - Domain, configuration keys, defaults, service names
- Diagnostics: `diagnostics.py` - Debug information and troubleshooting data

## Data Flow

**Integration Initialization:**

1. User configures integration via Home Assistant UI
2. `FranklinWHConfigFlow.async_step_user()` validates credentials via `validate_input()`
3. `FranklinWHCoordinator` is instantiated with credentials and gateway ID
4. `async_config_entry_first_refresh()` triggers initial data fetch
5. Coordinator data cached; platforms registered with `async_forward_entry_setups()`
6. Services registered: `set_operation_mode`, `set_battery_reserve`

**Continuous Data Updates:**

1. `DataUpdateCoordinator` runs `_async_update_data()` on schedule (default: 60s)
2. Client lazily initialized on first update (in executor to avoid blocking)
3. `client.get_stats()` fetches system metrics (async method in franklinwh 1.0.0+)
4. `client.get_smart_switch_state()` fetches switch states (optional, failure handled gracefully)
5. `FranklinWHData` object created with stats and switch state
6. Failure counter increments on error; after 3 failures marks unavailable
7. Entities notified of data change; platforms update their state
8. Temporary failures return last known data to keep entities available

**Service Call Flow:**

1. User calls `set_operation_mode` service with mode parameter
2. Entry handler routes to coordinator method
3. `async_set_operation_mode()` maps string mode to `Mode` factory object
4. `client.set_mode()` applies via API (async)
5. `async_request_refresh()` immediately refetches data
6. Entities update from coordinator

**Entity State Updates:**

1. Coordinator updates trigger `async_update_data()`
2. Entities inherit from `CoordinatorEntity` - automatically notified
3. Sensor `native_value` property calls value function with coordinator data
4. Switch `is_on` property reads switch state or grid status from coordinator data
5. Home Assistant updates entity state in registry

**State Management:**

- Coordinator holds current data in `self.data` (FranklinWHData instance)
- Token refreshed automatically by `franklinwh.TokenFetcher` (background process)
- Client connection reused across all requests (single client per coordinator)
- Failure counter tracks consecutive API errors; resets on success
- Entity availability tied to coordinator data availability and validity

## Key Abstractions

**FranklinWHData:**
- Purpose: Type-safe container for all device state
- Examples: `coordinator.py` lines 20-28
- Pattern: Simple dataclass holding `stats` (Stats object) and `switch_state` (tuple[bool, bool, bool])

**FranklinWHSensorEntityDescription:**
- Purpose: Declarative definition of sensor metadata and value extraction logic
- Examples: `sensor.py` lines 32-36, SENSOR_TYPES tuple lines 39-213
- Pattern: Extends Home Assistant's `SensorEntityDescription` with `value_fn` callable that extracts data from `FranklinWHData`

**FranklinWHCoordinator:**
- Purpose: Centralized async data fetcher with Home Assistant integration
- Examples: `coordinator.py` lines 31-240
- Pattern: Extends `DataUpdateCoordinator[FranklinWHData]`; manages client lifecycle, failure resilience, service methods

**Entity Platform Pattern:**
- Purpose: Declarative entity factory system
- Examples: `sensor.py` async_setup_entry (lines 216-229), `switch.py` async_setup_entry (lines 24-48)
- Pattern: `async_setup_entry` callback that extracts coordinator from hass.data and creates entity instances; Home Assistant discovers and registers entities

## Entry Points

**Integration Setup (`__init__.py`)**
- Location: `/Users/matt/Development/homeassistant-franklinwh/__init__.py`
- Triggers: Home Assistant loads integration; user configures via config flow
- Responsibilities:
  - Create and store coordinator in `hass.data[DOMAIN]`
  - Forward setup to platform modules (sensor, switch)
  - Register two services with schema validation
  - Handle setup failures and authentication errors
  - Implement unload and reload callbacks

**Platform Setup (sensor.py, switch.py)**
- Location: `sensor.py` async_setup_entry (lines 216-229); `switch.py` async_setup_entry (lines 24-48)
- Triggers: Integration calls `async_forward_entry_setups()`
- Responsibilities:
  - Fetch coordinator from `hass.data[DOMAIN][entry.entry_id]`
  - Create entity instances with coordinator reference
  - Register entities via `async_add_entities()` callback

**Config Flow Entry Point (`config_flow.py`)**
- Location: `config_flow.py` lines 80-179
- Triggers: User adds integration from UI
- Responsibilities:
  - Guide user through credential input and gateway ID
  - Validate credentials and connectivity before creating entry
  - Support credential updates via reauth flow

## Error Handling

**Strategy:** Multi-layered with graceful degradation

**Patterns:**

**Authentication Errors:**
- Detected in `_async_update_data()` via string matching ("auth", "token") or specific exception type
- Raised as `ConfigEntryAuthFailed` to trigger Home Assistant reauth flow
- User prompted to update credentials without losing configuration

**Temporary Connection Errors:**
- Tracked via `_consecutive_failures` counter (incremented up to `_max_failures` = 3)
- First 2 failures return last known data to keep entities available
- After 3 consecutive failures, raises `UpdateFailed` to mark entities unavailable
- Counter resets on successful update
- See `coordinator.py` lines 113-142

**Configuration Validation Errors:**
- `config_flow.py` validate_input() catches all exceptions
- Maps to semantic errors (CannotConnect, InvalidAuth, InvalidGateway)
- Presents user-friendly error messages via form errors dict
- See `config_flow.py` lines 57-77

**Entity Value Extraction Errors:**
- Sensor `native_value` property catches AttributeError, TypeError, KeyError
- Returns None (unknown state) instead of failing
- Logged as debug message to avoid spam
- See `sensor.py` lines 268-274

**Service Call Errors:**
- Service handlers wrap coordinator method calls in try/except
- Log errors but allow exceptions to propagate to Home Assistant
- Keeps entity available if error occurs
- See `__init__.py` lines 72-83

## Cross-Cutting Concerns

**Logging:**
- Logger per module: `_LOGGER = logging.getLogger(__name__)`
- Used for: Errors, warnings, debug info
- Channels: Home Assistant logger namespace configured in manifest (`"loggers": ["franklinwh"]`)

**Validation:**
- Input validation in `config_flow.validate_input()` before creating entry
- Service parameter validation via `voluptuous` schemas in `__init__.py` lines 91-108
- API response validation (null checks, attribute access safety)

**Authentication:**
- Credentials stored in config entry data: username, password, gateway_id
- Handled by `franklinwh.TokenFetcher` (manages token refresh in background)
- Reauth flow in config_flow.py allows credential update without full reconfiguration

**Concurrency:**
- All operations async (async/await throughout)
- Client initialization wrapped in executor to prevent blocking reactor: `hass.async_add_executor_job(create_client)` (lines 87 in coordinator.py)
- Service calls use `async_request_refresh()` to trigger immediate update without blocking

---

*Architecture analysis: 2026-02-27*
