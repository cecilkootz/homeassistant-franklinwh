# Technology Stack

**Analysis Date:** 2026-02-27

## Languages

**Primary:**
- Python 3.11+ - Complete integration codebase

**Secondary:**
- JSON - Configuration and strings files

## Runtime

**Environment:**
- Home Assistant (custom integration component)
- Python interpreter within Home Assistant environment

**Package Manager:**
- pip (Python package management)
- Lockfile: Not applicable (Home Assistant manages dependencies)

## Frameworks

**Core:**
- Home Assistant Core - Framework for integration lifecycle, entities, and config flows
  - Location: `/__init__.py`, `config_flow.py`, `sensor.py`, `switch.py`
  - Used for: Entry setup, platforms, services registration

**Data Management:**
- Home Assistant DataUpdateCoordinator - Efficient polling with minimal API calls
  - Location: `/coordinator.py`
  - Used for: Central data fetching and state management with update intervals

**Validation & Configuration:**
- voluptuous - Schema validation for config flows
  - Used in: `config_flow.py` for user input validation

## Key Dependencies

**Critical:**
- `franklinwh>=1.0.0` - Python library for FranklinWH energy storage systems
  - Provides: `Client`, `TokenFetcher`, `Mode`, `Stats`, `AccessoryType`, `GridStatus` classes
  - Location: Imported in `coordinator.py`, `config_flow.py`, `switch.py`
  - Why it matters: Primary integration between Home Assistant and FranklinWH cloud API

**Home Assistant Built-ins:**
- `homeassistant.core` - Core Home Assistant functionality
- `homeassistant.config_entries` - Configuration entry management
- `homeassistant.components.sensor` - Sensor platform with descriptions and state classes
- `homeassistant.components.switch` - Switch platform
- `homeassistant.helpers.update_coordinator` - DataUpdateCoordinator pattern
- `homeassistant.helpers.device_registry` - Device organization
- `homeassistant.exceptions` - Standard exception types
- `homeassistant.helpers.config_validation` - Config validation helpers

**Logging:**
- Python standard `logging` module
  - Used throughout for debug, info, warning, and error logging

## Configuration

**Environment:**
- Configuration via Home Assistant UI config flow (recommended)
- YAML configuration support (deprecated)
- Credentials stored in Home Assistant config entries

**Required Configuration:**
- `username` (CONF_USERNAME) - FranklinWH account email
- `password` (CONF_PASSWORD) - FranklinWH account password
- `gateway_id` (CONF_GATEWAY_ID) - Device serial number from FranklinWH app
- `use_local_api` (optional, CONF_USE_LOCAL_API) - Enable local API (experimental, not functional)
- `local_host` (optional, CONF_LOCAL_HOST) - Gateway IP address (experimental)

**Build/Runtime Configuration:**
- `manifest.json` - Integration metadata, dependencies, platforms
- `const.py` - Constants for domain, configuration keys, default intervals
- `strings.json` - Localization strings for config flow and errors
- `services.yaml` - Service definitions for operation mode and battery reserve

## Platform Requirements

**Development:**
- Home Assistant installation with custom component support
- Python 3.11+
- Network access to FranklinWH cloud services

**Production:**
- Home Assistant running environment
- Cloud connectivity to FranklinWH API endpoints
- Valid FranklinWH account credentials

## Key Configuration Values

**API Polling:**
- `DEFAULT_SCAN_INTERVAL` = 60 seconds (cloud API)
- `DEFAULT_LOCAL_SCAN_INTERVAL` = 10 seconds (local API, experimental)

**Local API:**
- `LOCAL_API_PORT` = 8080
- `LOCAL_API_TIMEOUT` = 10 seconds

**Device Information:**
- `MANUFACTURER` = "FranklinWH"
- `MODEL` = "aPower/aGate Energy Storage System"

---

*Stack analysis: 2026-02-27*
