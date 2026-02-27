# Coding Conventions

**Analysis Date:** 2026-02-27

## Naming Patterns

**Files:**
- Lowercase with underscores: `config_flow.py`, `coordinator.py`, `sensor.py`
- Domain integration pattern: Root level files (e.g., `__init__.py`, `const.py`, `coordinator.py`)
- Platform files: `{platform}.py` (e.g., `sensor.py`, `switch.py`)

**Functions:**
- Async functions prefixed with `async_`: `async_setup_entry()`, `async_config_entry_first_refresh()`
- Handler functions use pattern `handle_{action}`: `handle_set_operation_mode()`, `handle_set_battery_reserve()`
- Private/internal functions prefixed with underscore: `_async_update_data()`, `_async_get_coordinator_diagnostics()`
- Use snake_case: `get_stats()`, `create_client()`, `set_grid_status()`

**Variables:**
- Lowercase with underscores: `username`, `gateway_id`, `use_local_api`, `local_host`
- Constants in UPPERCASE with underscores: Defined in `const.py`
- Private attributes prefixed with underscore: `_LOGGER`, `_client_lock`, `_consecutive_failures`
- Entity attributes use Home Assistant pattern: `_attr_unique_id`, `_attr_name`, `_attr_device_info`

**Types:**
- Use type hints with full imports from `typing`: `dict[str, Any]`, `list[Platform]`, `tuple[bool, bool, bool]`
- Use `Final` from typing for constants: `DOMAIN: Final = "franklin_wh"`
- Entity descriptions use dataclass: `@dataclass class FranklinWHSensorEntityDescription`

## Code Style

**Formatting:**
- PEP 8 compliant
- Line length: Appears to follow standard Python conventions (typically 88-100 characters)
- Docstrings: Triple-quoted format with summary and description sections

**Linting:**
- Pylint directives used: `# pylint: disable=broad-except` for specific exceptions
- Noqa comments for rule suppressions: `# noqa: PGH003`, `# noqa: RUF006`
- Type ignore comments for unannotated types: `# type: ignore` for lazy-initialized attributes

**Example from `config_flow.py`:**
```python
"""Config flow for FranklinWH integration."""
from __future__ import annotations

import logging
from typing import Any

import franklinwh
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
```

## Import Organization

**Order:**
1. Standard library imports (`logging`, `asyncio`, `dataclasses`)
2. Third-party imports (`franklinwh`, `voluptuous`, `homeassistant`)
3. Local imports from package (`.const`, `.coordinator`)

**Path Aliases:**
- Relative imports used for local package code: `from .const import DOMAIN`
- Absolute imports for external packages and Home Assistant
- No @ path aliases observed in codebase

**Pattern from `coordinator.py`:**
```python
from __future__ import annotations

from datetime import timedelta
import logging

from franklinwh import Client, TokenFetcher, Mode
from franklinwh.client import Stats

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_LOCAL_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN
```

## Error Handling

**Patterns:**

- Specific exception types caught first, broad exceptions caught last
- Home Assistant specific exceptions used: `ConfigEntryAuthFailed`, `ConfigEntryNotReady`, `UpdateFailed`
- Custom exceptions defined in `config_flow.py` for configuration validation:
  - `CannotConnect`: When API connection fails
  - `InvalidAuth`: When authentication credentials are invalid
  - `InvalidGateway`: When gateway ID is invalid

**Example from `config_flow.py`:**
```python
try:
    info = await validate_input(self.hass, user_input)
except CannotConnect:
    errors["base"] = "cannot_connect"
except InvalidAuth:
    errors["base"] = "invalid_auth"
except InvalidGateway:
    errors["base"] = "invalid_gateway"
except Exception:  # pylint: disable=broad-except
    _LOGGER.exception("Unexpected exception")
    errors["base"] = "unknown"
```

**Error detection from `coordinator.py`:**
- String matching for error classification: `"timeout" in error_str`, `"auth" in error_str.lower()`
- Incremental failure counter: `self._consecutive_failures` tracks consecutive API failures (max 3)
- Fallback to last known data on temporary failures instead of immediately marking unavailable

**Example from `coordinator.py`:**
```python
except Exception as err:
    self._consecutive_failures += 1
    _LOGGER.warning(
        "API error (attempt %d/%d): %s",
        self._consecutive_failures,
        self._max_failures,
        err
    )

    if self._consecutive_failures >= self._max_failures:
        _LOGGER.error("Max consecutive failures reached, marking unavailable")
        raise UpdateFailed(f"Error communicating with API: {err}") from err

    if self.data:
        _LOGGER.debug("Returning last known data due to temporary failure")
        return self.data
    raise UpdateFailed(f"Error communicating with API: {err}") from err
```

## Logging

**Framework:** Python standard `logging` module

**Patterns:**
- Logger initialized at module level: `_LOGGER = logging.getLogger(__name__)`
- Use level-appropriate methods:
  - `_LOGGER.debug()`: Detailed diagnostic info, data values
  - `_LOGGER.info()`: Successful operations (mode changes, settings updates)
  - `_LOGGER.warning()`: Transient failures or recoverable issues
  - `_LOGGER.error()`: Service call failures, persistent issues
  - `_LOGGER.exception()`: Unexpected exceptions with full traceback

**Examples from `coordinator.py`:**
```python
_LOGGER.debug(
    "Stats fetched - SOC: %s%%, Solar: %skW, Grid: %skW",
    getattr(stats.current, 'battery_soc', 'N/A') if stats.current else 'N/A',
    getattr(stats.current, 'solar_production', 'N/A') if stats.current else 'N/A',
    getattr(stats.current, 'grid_use', 'N/A') if stats.current else 'N/A',
)

_LOGGER.info("Successfully set operation mode to %s", mode)

_LOGGER.error("Failed to set battery reserve to %d%%: %s", reserve_percent, err)
```

## Comments

**When to Comment:**
- Algorithm explanation: Mode type mapping in `async_set_operation_mode()`
- Non-obvious behavior: Battery reserve SOC preservation logic
- Configuration notes: Local API fields that are shown but not functional
- Known limitations: TODO comments for future enhancements

**Documentation Strings:**
- All public functions have docstrings explaining purpose and parameters
- Service handlers have descriptive docstrings: `"""Handle the set_operation_mode service call."""`
- Data classes document their purpose: `"""Class to hold FranklinWH data."""`

**Example from `config_flow.py`:**
```python
async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
```

## Function Design

**Size:** Functions are typically 10-40 lines

**Parameters:**
- Use type hints for all parameters
- Use Home Assistant conventions for hass: `hass: HomeAssistant`
- Use specific types instead of `Any` when possible
- Optional parameters use Union or `|` syntax: `switch_state: tuple[bool, bool, bool] | None = None`

**Return Values:**
- All functions specify return types: `-> bool`, `-> None`, `-> FranklinWHData`
- Async functions always return specific types (not auto-wrapped in coroutine in type hint)
- Return early on error conditions

**Example from `sensor.py`:**
```python
@property
def native_value(self) -> float | int | None:
    """Return the state of the sensor."""
    if self.entity_description.value_fn is None:
        return None

    try:
        return self.entity_description.value_fn(self.coordinator.data)
    except (AttributeError, TypeError, KeyError) as err:
        _LOGGER.debug(
            "Error getting value for %s: %s", self.entity_description.key, err
        )
        return None
```

## Module Design

**Exports:**
- Platform modules (`sensor.py`, `switch.py`) define async setup function: `async def async_setup_entry()`
- Integration module (`__init__.py`) exports setup/unload/reload entry points
- Constants module (`const.py`) exports all configuration keys and default values

**Barrel Files:**
- Not used - direct imports from submodules only

**Class Organization:**
- Entity classes inherit from Home Assistant base classes: `CoordinatorEntity[FranklinWHCoordinator]`, `SensorEntity`, `SwitchEntity`
- Configuration classes inherit from Home Assistant config flows: `ConfigFlow`, `OptionsFlow`
- Data classes use `@dataclass` decorator for simple data holders

**Example from `sensor.py`:**
```python
@dataclass
class FranklinWHSensorEntityDescription(SensorEntityDescription):
    """Describes FranklinWH sensor entity."""

    value_fn: Callable[[FranklinWHData], float | int | None] | None = None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up FranklinWH sensor based on a config entry."""
    coordinator: FranklinWHCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        FranklinWHSensorEntity(coordinator, description, entry)
        for description in SENSOR_TYPES
    ]

    async_add_entities(entities)
```

## Async Patterns

**Pattern:** All Home Assistant integration points use async:
- Setup functions: `async_setup_entry()`, `async_setup()`
- Service handlers: `async def handle_service_name(call: ServiceCall) -> None:`
- Data fetching: `await coordinator.async_request_refresh()`
- Executor delegation for blocking operations: `await hass.async_add_executor_job(blocking_fn)`

**Example from `config_flow.py`:**
```python
def create_client():
    token_fetcher = franklinwh.TokenFetcher(username, password)
    return franklinwh.Client(token_fetcher, gateway_id)

client = await hass.async_add_executor_job(create_client)
```

---

*Convention analysis: 2026-02-27*
