"""Select platform for FranklinWH integration."""
from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_GATEWAY_ID, DOMAIN, MANUFACTURER, MODEL
from .coordinator import FranklinWHCoordinator
from .franklinwh.client import (
    MODE_EMERGENCY_BACKUP,
    MODE_SELF_CONSUMPTION,
    MODE_TIME_OF_USE,
)

_LOGGER = logging.getLogger(__name__)

MODE_OPTION_TO_SERVICE_MODE = {
    "Time of Use (TOU)": "time_of_use",
    "Self-Consumption": "self_use",
    "Emergency Backup": "backup",
}

MODE_KEY_TO_OPTION = {
    MODE_TIME_OF_USE: "Time of Use (TOU)",
    MODE_SELF_CONSUMPTION: "Self-Consumption",
    MODE_EMERGENCY_BACKUP: "Emergency Backup",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up FranklinWH select entities."""
    coordinator: FranklinWHCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([FranklinWHModeSelect(coordinator, entry)])


class FranklinWHModeSelect(CoordinatorEntity[FranklinWHCoordinator], SelectEntity):
    """Select entity for operation mode."""

    _attr_has_entity_name = True
    _attr_name = "Mode"
    _attr_options = list(MODE_OPTION_TO_SERVICE_MODE.keys())

    def __init__(self, coordinator: FranklinWHCoordinator, entry: ConfigEntry) -> None:
        """Initialize the mode select."""
        super().__init__(coordinator)
        gateway_id = entry.data[CONF_GATEWAY_ID]
        self._attr_unique_id = f"{gateway_id}_operation_mode_select"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, gateway_id)},
            name=f"FranklinWH {gateway_id[-6:]}",
            manufacturer=MANUFACTURER,
            model=MODEL,
            sw_version=entry.data.get("sw_version"),
        )

    @property
    def current_option(self) -> str | None:
        """Return current selected mode."""
        if not self.coordinator.data or not self.coordinator.data.mode_status:
            return None

        mode_status = self.coordinator.data.mode_status
        if mode_status.mode_name in MODE_OPTION_TO_SERVICE_MODE:
            return mode_status.mode_name
        if mode_status.mode_key:
            return MODE_KEY_TO_OPTION.get(mode_status.mode_key)
        return None

    async def async_select_option(self, option: str) -> None:
        """Change operation mode."""
        if option not in MODE_OPTION_TO_SERVICE_MODE:
            raise ValueError(f"Invalid mode option: {option}")

        service_mode = MODE_OPTION_TO_SERVICE_MODE[option]
        try:
            await self.coordinator.async_set_operation_mode(service_mode)
        except Exception as err:
            _LOGGER.error("Failed to set mode to %s: %s", option, err)
            raise

