"""The FranklinWH integration.

Complete rewrite by Joshua Seidel (@JoshuaSeidel) with Anthropic Claude Sonnet 4.5.
Originally inspired by @richo's homeassistant-franklinwh integration.
Uses the franklinwh-python library by @richo.
"""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
import voluptuous as vol

from .const import (
    CONF_GATEWAY_ID,
    CONF_LOCAL_HOST,
    CONF_LOCAL_PORT,
    CONF_LOCAL_SLAVE_ID,
    CONF_USE_LOCAL_API,
    DEFAULT_LOCAL_PORT,
    DEFAULT_LOCAL_SLAVE_ID,
    DOMAIN,
    SERVICE_SET_BATTERY_RESERVE,
    SERVICE_SET_OPERATION_MODE,
)
from .coordinator import FranklinWHCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up FranklinWH from a config entry."""
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    gateway_id = entry.data[CONF_GATEWAY_ID]

    # Read Modbus settings from entry.options first (options flow users),
    # falling back to entry.data (first-setup users; entry.options is empty on first setup)
    use_local_api = entry.options.get(CONF_USE_LOCAL_API, entry.data.get(CONF_USE_LOCAL_API, False))
    local_host = entry.options.get(CONF_LOCAL_HOST, entry.data.get(CONF_LOCAL_HOST))
    local_port = entry.options.get(CONF_LOCAL_PORT, entry.data.get(CONF_LOCAL_PORT, DEFAULT_LOCAL_PORT))
    local_slave_id = entry.options.get(CONF_LOCAL_SLAVE_ID, entry.data.get(CONF_LOCAL_SLAVE_ID, DEFAULT_LOCAL_SLAVE_ID))

    # Create coordinator with all Modbus parameters
    coordinator = FranklinWHCoordinator(
        hass=hass,
        username=username,
        password=password,
        gateway_id=gateway_id,
        use_local_api=use_local_api,
        local_host=local_host,
        local_port=local_port,
        local_slave_id=local_slave_id,
        config_entry=entry,
    )

    # Fetch initial data
    try:
        await coordinator.async_config_entry_first_refresh()
        _LOGGER.debug("FranklinWH initial data fetch complete")
    except ConfigEntryAuthFailed as err:
        _LOGGER.error("Authentication failed: %s", err)
        raise
    except Exception as err:
        # Check if this is a Modbus-related error at startup
        err_str = str(err).lower()
        is_modbus_error = (
            "sunspec" in err_str
            or "modbus" in err_str
            or "connection" in err_str
            or "timeout" in err_str
        )

        if use_local_api and is_modbus_error:
            # Modbus failed at startup - log warning and continue with cloud-only
            _LOGGER.warning(
                "Modbus failed at startup (%s), continuing with cloud-only mode. "
                "The integration loaded successfully but local Modbus will be "
                "disabled until the next reload or restart.",
                err
            )
            # Update options to disable local API for next reload
            from homeassistant.config_entries import ConfigEntry

            # Store that we fell back to cloud-only due to Modbus failure
            hass.data.setdefault(DOMAIN, {})
            hass.data[DOMAIN][f"{entry.entry_id}_modbus_failed"] = True
        else:
            _LOGGER.error("Error setting up FranklinWH: %s", err)
            raise ConfigEntryNotReady from err

    # Store coordinator
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Reload the entry when options change (e.g., toggling local Modbus mode)
    entry.add_update_listener(async_reload_entry)

    # Register services
    async def handle_set_operation_mode(call: ServiceCall) -> None:
        """Handle the set_operation_mode service call."""
        mode = call.data.get("mode")
        try:
            await coordinator.async_set_operation_mode(mode)
        except Exception as err:
            _LOGGER.error("Failed to set operation mode: %s", err)

    async def handle_set_battery_reserve(call: ServiceCall) -> None:
        """Handle the set_battery_reserve service call."""
        reserve_percent = call.data.get("reserve_percent")
        try:
            await coordinator.async_set_battery_reserve(reserve_percent)
        except Exception as err:
            _LOGGER.error("Failed to set battery reserve: %s", err)

    # Register services only once
    if not hass.services.has_service(DOMAIN, SERVICE_SET_OPERATION_MODE):
        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_OPERATION_MODE,
            handle_set_operation_mode,
            schema=vol.Schema(
                {
                    vol.Required("mode"): vol.In(
                        ["self_use", "backup", "time_of_use", "clean_backup"]
                    )
                }
            ),
        )

    if not hass.services.has_service(DOMAIN, SERVICE_SET_BATTERY_RESERVE):
        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_BATTERY_RESERVE,
            handle_set_battery_reserve,
            schema=vol.Schema(
                {vol.Required("reserve_percent"): vol.All(vol.Coerce(int), vol.Range(min=0, max=100))}
            ),
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
