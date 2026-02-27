# Codebase Structure

**Analysis Date:** 2026-02-27

## Directory Layout

```
homeassistant-franklinwh/
├── __init__.py              # Integration entry point, setup/unload, service registration
├── config_flow.py           # User configuration flow, validation, reauth
├── coordinator.py           # Data fetching, state management, service implementations
├── sensor.py                # 24+ sensor entities exposing FranklinWH metrics
├── switch.py                # Smart switch and grid connection switch entities
├── const.py                 # Domain, configuration keys, defaults, constants
├── diagnostics.py           # Debug/troubleshooting information
├── manifest.json            # Integration metadata, dependencies, version
├── services.yaml            # Service definitions for Home Assistant
├── strings.json             # Localization strings
├── translations/            # Translated UI strings
│   └── en.json              # English translations
├── .cursorrules             # Cursor IDE configuration
├── README.md                # User documentation
├── LICENSE                  # Apache 2.0 license
├── QUICK_START.md           # Quick setup guide
├── CONTRIBUTING.md          # Development guidelines
└── .planning/               # Documentation and planning
    └── codebase/            # Architecture and structure docs
```

## Directory Purposes

**Root Directory (/):**
- Purpose: Home Assistant custom integration (HACS-installable)
- Contains: Python modules, configuration files, documentation
- Key files: `__init__.py` (entry point), `manifest.json` (metadata), `config_flow.py` (onboarding)

**translations/:**
- Purpose: Localization resources for Home Assistant UI strings
- Contains: JSON locale files
- Key files: `en.json` (English strings for config flow errors, service descriptions)

**Commit History:**
- Root is Home Assistant integration directory (domain = "franklin_wh")
- No subdirectories for tests, data, or models (single-level flat structure)
- Translation files centralized in `translations/` subdirectory

## Key File Locations

**Entry Points:**

- `__init__.py`: Main integration entry point
  - Function: `async_setup_entry()` - Called when Home Assistant loads config entry
  - Function: `async_unload_entry()` - Called when removing integration
  - Responsibilities: Coordinator creation, platform setup, service registration

- `config_flow.py`: Configuration and authentication entry point
  - Class: `FranklinWHConfigFlow` - Guides user through initial setup
  - Method: `async_step_user()` - Initial credential input
  - Method: `async_step_reauth_confirm()` - Credential update flow

**Configuration:**

- `const.py`: All constants used throughout integration
  - Domain name: `"franklin_wh"`
  - Configuration keys: `CONF_GATEWAY_ID`, `CONF_USE_LOCAL_API`, `CONF_LOCAL_HOST`
  - Defaults: `DEFAULT_SCAN_INTERVAL=60`, `DEFAULT_LOCAL_SCAN_INTERVAL=10`
  - Service names: `SERVICE_SET_OPERATION_MODE`, `SERVICE_SET_BATTERY_RESERVE`

- `manifest.json`: Home Assistant integration metadata
  - Version tracking, dependencies (franklinwh>=1.0.0), documentation links
  - Domain name and integration type

- `services.yaml`: Service definitions
  - Describes `set_operation_mode` and `set_battery_reserve` services
  - Used by Home Assistant UI for service call UI

**Core Logic:**

- `coordinator.py`: Data aggregation and device communication
  - Class: `FranklinWHCoordinator` - Async data fetcher (extends DataUpdateCoordinator)
  - Class: `FranklinWHData` - Type-safe data container
  - Methods: `_async_update_data()`, `async_set_operation_mode()`, `async_set_battery_reserve()`, `async_set_switch_state()`

- `sensor.py`: Sensor platform (read-only metrics)
  - SENSOR_TYPES: 24 sensor definitions (battery, grid, solar, switches, V2L, generator)
  - Class: `FranklinWHSensorEntity` - Home Assistant sensor entity
  - Data source: `coordinator.data.stats` (Stats object from franklinwh library)

- `switch.py`: Switch platform (controllable switches)
  - Class: `FranklinWHSmartSwitch` - Smart circuit module switches (1-3)
  - Class: `GridSwitch` - Grid connection on/off
  - Data source: `coordinator.data.switch_state` (tuple of 3 bools) and `coordinator.data.stats.current.grid_status`

**Support Files:**

- `diagnostics.py`: Diagnostic information for troubleshooting
  - Function: `async_get_config_entry_diagnostics()` - Returns sanitized stats for Home Assistant diagnostics

- `strings.json`: UI string localization (English)
  - Config flow labels, descriptions, error messages

## Naming Conventions

**Files:**

- Lowercase with underscores: `config_flow.py`, `coordinator.py`, `sensor.py`, `switch.py`, `diagnostics.py`
- Pattern: `{feature}.py` for platform files; core files named by function
- Exception: `__init__.py` for package entry point

**Directories:**

- Lowercase with underscores: `translations/`, `.planning/`, `.github/`
- Pattern: English descriptive names

**Python Classes:**

- PascalCase: `FranklinWHCoordinator`, `FranklinWHSensorEntity`, `FranklinWHSmartSwitch`
- Pattern: Feature prefix + descriptive suffix (e.g., {Integration}Coordinator)
- Exceptions: `CannotConnect`, `InvalidAuth`, `InvalidGateway` (all PascalCase)

**Functions:**

- snake_case: `async_setup_entry()`, `async_step_user()`, `validate_input()`, `_async_update_data()`
- Pattern: Async functions prefixed with `async_`; private functions prefixed with `_`

**Constants:**

- UPPER_SNAKE_CASE: `DOMAIN`, `CONF_GATEWAY_ID`, `DEFAULT_SCAN_INTERVAL`
- Pattern: Configuration keys prefixed with `CONF_`, defaults with `DEFAULT_`, services with `SERVICE_`

**Module-level Variables:**

- `_LOGGER = logging.getLogger(__name__)` - Per-module logger

## Where to Add New Code

**New Sensor/Metric:**
- Add `FranklinWHSensorEntityDescription` entry to `SENSOR_TYPES` tuple in `sensor.py`
- Define `key`, `name`, `native_unit_of_measurement`, `device_class`, `state_class`
- Provide `value_fn` lambda that extracts value from `FranklinWHData`
- Example pattern (lines 40-46 in `sensor.py`):
  ```python
  FranklinWHSensorEntityDescription(
      key="battery_soc",
      name="State of Charge",
      native_unit_of_measurement=PERCENTAGE,
      device_class=SensorDeviceClass.BATTERY,
      state_class=SensorStateClass.MEASUREMENT,
      value_fn=lambda data: data.stats.current.battery_soc if data.stats else None,
  ),
  ```

**New Switch Type:**
- Create new class extending `CoordinatorEntity[FranklinWHCoordinator], SwitchEntity`
- Implement `__init__()` with unique ID and device info
- Implement `is_on` property to read state from coordinator data
- Implement `async_turn_on()` and `async_turn_off()` calling coordinator methods
- Register in `async_setup_entry()` by appending to entities list
- Example pattern in `switch.py` (lines 51-132 for FranklinWHSmartSwitch)

**New Service:**
- Add service name constant to `const.py`: `SERVICE_X = "x"`
- Add handler function in `__init__.async_setup_entry()` (lines 69-83 pattern)
- Register with `hass.services.async_register()` including voluptuous schema
- Implement coordinator method to execute service action
- Define service in `services.yaml` with description and parameters

**New Configuration Option:**
- Add constant to `const.py`: `CONF_X = "x"`
- Add field to config schema in `config_flow.async_step_user()` (lines 112-121 pattern)
- Store in entry.data automatically via `async_create_entry()`
- Use in coordinator or entity initialization

**Coordinator Method (Data Fetch or Action):**
- Add async method to `FranklinWHCoordinator` class in `coordinator.py`
- Follow existing pattern: wrap client call, handle exceptions, call `async_request_refresh()` if mutating
- Add error logging with context
- Examples: `async_set_operation_mode()` (lines 180-208), `async_set_battery_reserve()` (lines 210-240)

## Special Directories

**translations/:**
- Purpose: Localization strings (currently English only)
- Generated: No (manually maintained)
- Committed: Yes - required for Home Assistant UI

**.github/:**
- Purpose: GitHub Actions workflows, issue templates
- Generated: No (manually maintained)
- Committed: Yes

**.planning/codebase/:**
- Purpose: Architecture and structure documentation for development
- Generated: Yes (by mapping agent)
- Committed: Yes - reference documentation

---

*Structure analysis: 2026-02-27*
