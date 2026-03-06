"""Number platform for FranklinWH integration."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_GATEWAY_ID, DOMAIN, MANUFACTURER, MODEL
from .coordinator import FranklinWHCoordinator, FranklinWHData

_LOGGER = logging.getLogger(__name__)


@dataclass
class FranklinWHReserveNumberDescription(NumberEntityDescription):
    """Description for per-mode reserve number entities."""

    service_mode: str = ""
    value_fn: Callable[[FranklinWHData], int | None] | None = None


RESERVE_NUMBERS: tuple[FranklinWHReserveNumberDescription, ...] = (
    FranklinWHReserveNumberDescription(
        key="time_of_use_backup_reserve",
        name="Time of Use Backup Reserve",
        service_mode="time_of_use",
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        mode=NumberMode.BOX,
        value_fn=lambda data: (
            data.mode_status.time_of_use_reserve if data.mode_status else None
        ),
    ),
    FranklinWHReserveNumberDescription(
        key="self_consumption_backup_reserve",
        name="Self-Consumption Backup Reserve",
        service_mode="self_use",
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        mode=NumberMode.BOX,
        value_fn=lambda data: (
            data.mode_status.self_consumption_reserve if data.mode_status else None
        ),
    ),
    FranklinWHReserveNumberDescription(
        key="emergency_backup_reserve",
        name="Emergency Backup Reserve",
        service_mode="backup",
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        mode=NumberMode.BOX,
        value_fn=lambda data: (
            data.mode_status.emergency_backup_reserve if data.mode_status else None
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up FranklinWH number entities."""
    coordinator: FranklinWHCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [FranklinWHReserveNumber(coordinator, entry, description) for description in RESERVE_NUMBERS]
    )


class FranklinWHReserveNumber(
    CoordinatorEntity[FranklinWHCoordinator],
    NumberEntity,
):
    """Number entity for per-mode reserve."""

    entity_description: FranklinWHReserveNumberDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FranklinWHCoordinator,
        entry: ConfigEntry,
        description: FranklinWHReserveNumberDescription,
    ) -> None:
        """Initialize number entity."""
        super().__init__(coordinator)
        self.entity_description = description
        gateway_id = entry.data[CONF_GATEWAY_ID]
        self._attr_unique_id = f"{gateway_id}_{description.key}_number"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, gateway_id)},
            name=f"FranklinWH {gateway_id[-6:]}",
            manufacturer=MANUFACTURER,
            model=MODEL,
            sw_version=entry.data.get("sw_version"),
        )

    @property
    def native_value(self) -> float | None:
        """Return reserve value."""
        if self.entity_description.value_fn is None:
            return None
        try:
            value = self.entity_description.value_fn(self.coordinator.data)
            return float(value) if value is not None else None
        except (AttributeError, TypeError, ValueError) as err:
            _LOGGER.debug("Error getting reserve value for %s: %s", self.entity_description.key, err)
            return None

    async def async_set_native_value(self, value: float) -> None:
        """Update reserve for this mode."""
        reserve = int(round(value))
        try:
            await self.coordinator.async_set_mode_reserve(
                self.entity_description.service_mode,
                reserve,
            )
        except Exception as err:
            _LOGGER.error(
                "Failed to set reserve for mode %s to %d%%: %s",
                self.entity_description.service_mode,
                reserve,
                err,
            )
            raise

