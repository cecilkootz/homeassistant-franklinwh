# Testing Patterns

**Analysis Date:** 2026-02-27

## Test Framework

**Status:** No formal testing framework configured

The codebase currently has:
- No test files found (no `test_*.py`, `*_test.py`, or `conftest.py`)
- No test runner configuration (no `pytest.ini`, `setup.cfg`, `pyproject.toml`)
- No test dependencies specified

This is a Home Assistant custom integration that relies on Home Assistant's testing infrastructure when deployed.

**Home Assistant Integration Testing:**
- Integration is designed to work with Home Assistant's config entry system
- Testing would typically use Home Assistant's test fixtures and mocking patterns
- Coordinator pattern allows isolated testing of data fetching logic

## Testable Components

**High Priority (Currently Untested):**

**`coordinator.py` - Data Fetching and State Management:**
- `FranklinWHCoordinator._async_update_data()`: Main data fetch with error handling
  - Needs testing for: Client initialization, successful data fetch, timeout handling, auth failures
  - Tests should verify: Consecutive failure counter, fallback to last known data, max failures trigger
  - Mocking required: `franklinwh.Client`, `franklinwh.TokenFetcher`, `Stats` objects

- `FranklinWHCoordinator.async_set_operation_mode()`: Mode switching with mode mapping
  - Needs testing for: String to Mode object conversion, each mode type (self_use, backup, time_of_use, clean_backup)
  - Mocking required: Client mock with `set_mode()` method

- `FranklinWHCoordinator.async_set_battery_reserve()`: Battery SOC setting
  - Needs testing for: Setting reserve with default self_consumption mode
  - Edge cases: What happens when current mode cannot be retrieved

**`config_flow.py` - Configuration and Validation:**
- `validate_input()`: User input validation against FranklinWH API
  - Needs testing for: Valid credentials, invalid credentials, timeout, invalid gateway, missing data
  - Test should verify correct exception types raised: `CannotConnect`, `InvalidAuth`, `InvalidGateway`
  - Mocking required: `franklinwh.TokenFetcher`, `franklinwh.Client`

- `FranklinWHConfigFlow.async_step_user()`: Initial setup form
  - Needs testing for: Form submission, error handling, duplicate gateway detection

- `FranklinWHConfigFlow.async_step_reauth_confirm()`: Reauthentication flow
  - Needs testing for: Credential update, entry reload, failed reauth

**`sensor.py` - Sensor Entity Values:**
- `FranklinWHSensorEntity.native_value()`: Sensor value extraction and error handling
  - Needs testing for: Each sensor type's value function with various data states
  - Edge cases: None data, missing attributes, type conversion errors (AttributeError, TypeError, KeyError)

**`switch.py` - Switch Control:**
- `FranklinWHSmartSwitch.async_turn_on/off()`: Smart switch state changes
  - Needs testing for: Correct switch state array construction and API call
  - Mocking required: Coordinator's `async_set_switch_state()` method

- `GridSwitch.is_on()`: Grid connection status mapping
  - Needs testing for: GridStatus.NORMAL → True, GridStatus.OFF → False, unknown states → None

## Recommended Test Setup

**Suggested Framework:** pytest with Home Assistant pytest plugin

**Suggested Test Structure:**
```
tests/
├── conftest.py                 # Shared fixtures and configuration
├── test_config_flow.py        # Configuration and validation tests
├── test_coordinator.py         # Data fetching and coordinator tests
├── test_sensor.py             # Sensor entity tests
├── test_switch.py             # Switch entity tests
├── test_diagnostics.py        # Diagnostic data tests
└── fixtures/
    ├── stats_data.py          # Mock FranklinWH stats objects
    └── responses.py           # Mock API responses
```

**Example Test Structure (pytest):**
```python
import pytest
from unittest.mock import AsyncMock, MagicMock

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ConfigEntryAuthFailed

from custom_components.franklin_wh.coordinator import FranklinWHCoordinator
from custom_components.franklin_wh.config_flow import validate_input, CannotConnect, InvalidAuth


@pytest.fixture
def mock_franklinwh_client():
    """Create mock FranklinWH client."""
    client = AsyncMock()
    client.get_stats = AsyncMock()
    client.get_smart_switch_state = AsyncMock()
    return client


@pytest.fixture
async def coordinator(hass: HomeAssistant, mock_franklinwh_client):
    """Create coordinator with mocked client."""
    coordinator = FranklinWHCoordinator(
        hass=hass,
        username="test_user",
        password="test_pass",
        gateway_id="test_gateway",
    )
    coordinator.client = mock_franklinwh_client
    return coordinator


@pytest.mark.asyncio
async def test_validate_input_success(hass: HomeAssistant, mock_franklinwh_client):
    """Test successful input validation."""
    with patch("custom_components.franklin_wh.config_flow.franklinwh.TokenFetcher") as mock_fetcher:
        mock_fetcher.return_value = MagicMock()
        with patch("custom_components.franklin_wh.config_flow.franklinwh.Client") as mock_client:
            mock_client.return_value = AsyncMock(get_stats=AsyncMock(return_value={"data": "value"}))

            result = await validate_input(hass, {
                "username": "test",
                "password": "pass",
                "gateway_id": "GW123"
            })

            assert result["title"] == "FranklinWH 123"
            assert result["gateway_id"] == "GW123"


@pytest.mark.asyncio
async def test_validate_input_auth_failure(hass: HomeAssistant):
    """Test validation with authentication failure."""
    with patch("custom_components.franklin_wh.config_flow.franklinwh.TokenFetcher") as mock_fetcher:
        mock_fetcher.side_effect = Exception("Invalid credentials - 401")

        with pytest.raises(InvalidAuth):
            await validate_input(hass, {
                "username": "bad_user",
                "password": "bad_pass",
                "gateway_id": "GW123"
            })


@pytest.mark.asyncio
async def test_coordinator_update_with_failures(coordinator, mock_franklinwh_client):
    """Test coordinator failure counter and fallback behavior."""
    stats = MagicMock()
    coordinator.data = MagicMock(stats=stats)

    # Simulate temporary failures
    mock_franklinwh_client.get_stats.side_effect = [
        Exception("Temporary failure"),
        Exception("Temporary failure"),
        Exception("Max failures reached")
    ]

    # First two calls should return cached data
    result1 = await coordinator._async_update_data()
    assert result1.stats is not None

    result2 = await coordinator._async_update_data()
    assert result2.stats is not None

    # Third call should raise UpdateFailed
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()

    assert coordinator._consecutive_failures == 3


@pytest.mark.asyncio
async def test_set_operation_mode_mapping(coordinator, mock_franklinwh_client):
    """Test operation mode string-to-Mode mapping."""
    modes_to_test = [
        ("self_use", "Mode.self_consumption"),
        ("backup", "Mode.emergency_backup"),
        ("time_of_use", "Mode.time_of_use"),
        ("clean_backup", "Mode.emergency_backup")
    ]

    for mode_str, expected_mode in modes_to_test:
        coordinator._consecutive_failures = 0  # Reset counter
        await coordinator.async_set_operation_mode(mode_str)
        mock_franklinwh_client.set_mode.assert_called()
```

## Testing Challenges and Notes

**Mock Complexity:**
- `franklinwh` library has external API calls that need mocking
- `Stats` objects have nested structures (`.current`, `.totals`) with many attributes
- Requires mocking both sync and async methods depending on franklinwh version

**Current Version Compatibility:**
- Recent fix (commit 7f78572): Updated to async API methods from franklinwh 1.0.0+
- All coordinator data fetching now uses async: `await client.get_stats()`
- Tests need to mock async methods properly with `AsyncMock`

**Coverage Gaps:**
- No tests for error edge cases in `sensor.py` value extraction
- No tests for switch state tuple construction and boundary conditions
- No tests for diagnostics data collection
- No tests for Home Assistant platform setup hooks
- No integration tests with actual Home Assistant instance

**Async Testing Considerations:**
- All coordinator methods are async and need `@pytest.mark.asyncio`
- Service handlers are async and need proper event loop handling
- Must use `AsyncMock` from unittest.mock for async methods
- Executor job delegation needs special handling in tests

## Error Conditions to Test

**API Communication:**
- Timeout errors (detect string "timeout" in error message)
- Authentication failures (detect "auth" or "token" in error message)
- Invalid gateway (detect "gateway" or "device" in error message)
- Network connectivity issues
- Malformed API responses

**State Management:**
- Consecutive failure counting and reset on success
- Fallback to last known data behavior
- Transitioning from unavailable to available
- Data initialization on first run

**Configuration:**
- Duplicate gateway detection in config flow
- Invalid credential combinations
- Missing required fields
- Optional field handling (local API fields currently disabled)

---

*Testing analysis: 2026-02-27*
