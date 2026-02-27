# External Integrations

**Analysis Date:** 2026-02-27

## APIs & External Services

**FranklinWH Cloud API:**
- FranklinWH Energy Storage System API - Primary data source for monitoring and control
  - SDK/Client: `franklinwh` Python library (>=1.0.0)
  - Auth: Email/password credentials (username + password)
  - Endpoints used:
    - `Client.get_stats()` - Retrieve current and total energy statistics
    - `Client.get_smart_switch_state()` - Get smart circuit switch states
    - `Client.set_smart_switch_state()` - Control smart circuits
    - `Client.get_mode()` - Retrieve current operation mode
    - `Client.set_mode()` - Set operation mode with battery reserve
    - `Client.get_accessories()` - List connected accessories/modules
  - Location: `coordinator.py` lines 84-110, 172-241

**Token Management:**
- FranklinWH TokenFetcher - Handles authentication tokens
  - SDK: `franklinwh.TokenFetcher` class
  - Auth method: Credentials-based token exchange
  - Location: `coordinator.py` lines 41-48, 83-88

## Data Storage

**Databases:**
- Not used - Stateless integration

**File Storage:**
- Not used - Local file storage not required

**Caching:**
- In-memory via DataUpdateCoordinator
  - Coordinator caches latest stats and switch state
  - Update interval: 60 seconds (cloud) or 10 seconds (local API, experimental)
  - Location: `coordinator.py` class `FranklinWHCoordinator`
  - Failure resilience: Maintains last-known data through 3 consecutive failures (3 minutes)

**State Persistence:**
- Home Assistant stores entity states and config entries
- Credentials encrypted by Home Assistant config entry system

## Authentication & Identity

**Auth Provider:**
- Custom credential-based authentication
- Implementation approach:
  - Email and password validated against FranklinWH API
  - TokenFetcher handles token acquisition in `franklinwh` library
  - Credentials stored in encrypted config entry
  - Location: `config_flow.py` lines 29-77, `coordinator.py` lines 83-91
  - Reauth support for credential refresh via `async_step_reauth_confirm`

**Credential Validation:**
- Validation occurs during config flow setup
- Tests credentials and gateway ID accessibility
- Specific error handling for:
  - Authentication failures (401 errors, token issues)
  - Gateway not found or invalid ID
  - Connection timeouts or unreachability
- Location: `config_flow.py` lines 29-77

## Monitoring & Observability

**Error Tracking:**
- None detected - Uses Home Assistant logging only

**Logs:**
- Python standard logging via Home Assistant logger
- Logger name: "franklin_wh" (defined in manifest.json)
- Debug, info, warning, and error levels throughout codebase
- Key loggers:
  - `coordinator.py` - API calls, failures, recovery
  - `config_flow.py` - Setup and validation
  - `switch.py` - Switch operations
  - Location: Root logger configured in `__init__.py`, `coordinator.py`, `config_flow.py`

**Diagnostics:**
- Built-in Home Assistant diagnostics support
- Location: `diagnostics.py`
- Provides: Stats data, switch states, update timing, redacted credentials
- Redacted fields: username, password, gateway_id, token, access_token

## CI/CD & Deployment

**Hosting:**
- Home Assistant custom component via HACS
- Repository: https://github.com/JoshuaSeidel/homeassistant-franklinwh

**CI Pipeline:**
- Not detected in codebase
- GitHub issue tracker: https://github.com/JoshuaSeidel/homeassistant-franklinwh/issues

**Installation Methods:**
- HACS (Home Assistant Community Store) - primary recommended method
- Manual ZIP extraction to `custom_components/franklin_wh/`
- YAML configuration (deprecated)

## Environment Configuration

**Required env vars:**
- None - Credentials stored in Home Assistant config entries

**Secrets location:**
- Home Assistant `secrets.yaml` for YAML-based config (deprecated)
- Encrypted config entry storage for UI config flow (recommended)
- Password field in config flow UI

**Forbidden env vars:**
- Credentials MUST NOT be in .env files
- Password stored exclusively in Home Assistant encrypted storage

## Webhooks & Callbacks

**Incoming:**
- None - Integration is polling-based only

**Outgoing:**
- None - All communication is request/response (pull-based)

## Service Integration

**Custom Services:**
- `set_operation_mode` - Controls system operation mode
  - Modes: self_use, backup, time_of_use, clean_backup
  - Implementation: `coordinator.async_set_operation_mode()`
  - Location: `__init__.py` lines 69-98, `coordinator.py` lines 180-208

- `set_battery_reserve` - Sets minimum battery reserve percentage
  - Range: 0-100%
  - Implementation: `coordinator.async_set_battery_reserve()`
  - Location: `__init__.py` lines 100-108, `coordinator.py` lines 210-240

## Entity Integration

**Sensor Entities:**
- 20+ sensor types providing real-time and cumulative energy data
- Classes: SensorEntity with state classes (MEASUREMENT, TOTAL_INCREASING)
- Location: `sensor.py` lines 39-150+

**Switch Entities:**
- Grid Connection switch (monitoring and control)
- Smart Circuit switches 1-3 (based on AccessoryType.SMART_CIRCUIT_MODULE)
- Location: `switch.py` lines 24-150+

## Device Management

**Device Registry:**
- All entities grouped under single FranklinWH device
- Device info:
  - Identifier: Gateway ID
  - Name: "FranklinWH {gateway_id[-6:]}"
  - Manufacturer: "FranklinWH"
  - Model: "aPower/aGate Energy Storage System"
  - Software Version: Optional from config
- Location: `sensor.py`, `switch.py` - DeviceInfo assignments

## Configuration Flow

**Setup Process:**
1. User enters email, password, gateway_id via UI
2. Config flow validates credentials via `franklinwh.Client`
3. Initial data fetch confirms API connectivity
4. Config entry created with encrypted credentials
5. DataUpdateCoordinator initialized with polling schedule
6. Sensor and switch platforms set up
7. Custom services registered

**Reauth Process:**
- Triggered on authentication failure
- User updates credentials only
- Config entry automatically reloaded
- Location: `config_flow.py` lines 127-171

---

*Integration audit: 2026-02-27*
