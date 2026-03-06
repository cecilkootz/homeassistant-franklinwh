"""Sensor platform for FranklinWH integration."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import CONF_GATEWAY_ID, DOMAIN, MANUFACTURER, MODEL
from .coordinator import FranklinWHCoordinator, FranklinWHData
from .franklinwh.client import (
    ApowerInfo,
    MODE_EMERGENCY_BACKUP,
    MODE_SELF_CONSUMPTION,
    MODE_TIME_OF_USE,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class FranklinWHSensorEntityDescription(SensorEntityDescription):
    """Describes FranklinWH sensor entity."""

    value_fn: Callable[[FranklinWHData], Any] | None = None
    last_reset_fn: Callable[[FranklinWHData], datetime | None] | None = None


APOWER_STATUS_MAP = {
    0: "Normal",
}


def _format_backup_time(minutes: int | None) -> str | None:
    """Convert backup runtime minutes to app-like text."""
    if minutes is None:
        return None
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours} hours {mins} minutes"


def _mode_label_from_data(data: FranklinWHData) -> str | None:
    """Return operation mode label from mode status, then runtime fallback."""
    if data.mode_status:
        if data.mode_status.mode_name:
            return data.mode_status.mode_name
        if data.mode_status.mode_key == MODE_TIME_OF_USE:
            return "Time of Use (TOU)"
        if data.mode_status.mode_key == MODE_SELF_CONSUMPTION:
            return "Self-Consumption"
        if data.mode_status.mode_key == MODE_EMERGENCY_BACKUP:
            return "Emergency Backup"
    if data.stats and data.stats.current and data.stats.current.mode_name:
        name = str(data.stats.current.mode_name)
        lowered = name.lower()
        if "time" in lowered and "use" in lowered:
            return "Time of Use (TOU)"
        if "self" in lowered:
            return "Self-Consumption"
        if "backup" in lowered:
            return "Emergency Backup"
        return name
    return None


def _local_day_start(_: FranklinWHData) -> datetime:
    """Return local midnight for daily-reset energy counters."""
    return dt_util.start_of_local_day()


SENSOR_TYPES: tuple[FranklinWHSensorEntityDescription, ...] = (
    FranklinWHSensorEntityDescription(
        key="operation_mode",
        name="Operation Mode",
        device_class=SensorDeviceClass.ENUM,
        options=["Time of Use (TOU)", "Self-Consumption", "Emergency Backup"],
        value_fn=lambda data: _mode_label_from_data(data),
    ),
    FranklinWHSensorEntityDescription(
        key="backup_reserve",
        name="Backup Reserve",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.mode_status.current_reserve if data.mode_status else None,
    ),
    FranklinWHSensorEntityDescription(
        key="time_of_use_backup_reserve",
        name="Time of Use Backup Reserve",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: (
            data.mode_status.time_of_use_reserve if data.mode_status else None
        ),
    ),
    FranklinWHSensorEntityDescription(
        key="self_consumption_backup_reserve",
        name="Self-Consumption Backup Reserve",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: (
            data.mode_status.self_consumption_reserve if data.mode_status else None
        ),
    ),
    FranklinWHSensorEntityDescription(
        key="emergency_backup_reserve",
        name="Emergency Backup Reserve",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: (
            data.mode_status.emergency_backup_reserve if data.mode_status else None
        ),
    ),
    FranklinWHSensorEntityDescription(
        key="total_storage_capacity",
        name="Total Storage Capacity",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY_STORAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: (
            data.system_overview.total_storage_capacity if data.system_overview else None
        ),
    ),
    FranklinWHSensorEntityDescription(
        key="apower_count",
        name="aPower Count",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.system_overview.apower_count if data.system_overview else None,
    ),
    FranklinWHSensorEntityDescription(
        key="battery_soc",
        name="State of Charge",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.stats.current.battery_soc if data.stats else None,
    ),
    FranklinWHSensorEntityDescription(
        key="battery_use",
        name="Battery Power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.stats.current.battery_use if data.stats else None,
    ),
    FranklinWHSensorEntityDescription(
        key="apower_cluster_power",
        name="aPower Cluster Power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.stats.current.battery_use if data.stats else None,
    ),
    FranklinWHSensorEntityDescription(
        key="battery_charge",
        name="Battery Charge",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        last_reset_fn=_local_day_start,
        value_fn=lambda data: data.stats.totals.battery_charge if data.stats else None,
    ),
    FranklinWHSensorEntityDescription(
        key="battery_discharge",
        name="Battery Discharge",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        last_reset_fn=_local_day_start,
        value_fn=lambda data: data.stats.totals.battery_discharge if data.stats else None,
    ),
    FranklinWHSensorEntityDescription(
        key="battery_charge_from_grid",
        name="Battery Charge from Grid",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: (
            # Battery charged from grid = Total battery charge - Solar energy
            # (assuming all solar goes to battery first, excess goes to home/grid)
            max(0, (data.stats.totals.battery_charge or 0) - (data.stats.totals.solar or 0))
            if data.stats else None
        ),
    ),
    FranklinWHSensorEntityDescription(
        key="home_load",
        name="Home Load",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.stats.current.home_load if data.stats else None,
    ),
    FranklinWHSensorEntityDescription(
        key="grid_use",
        name="Grid Use",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.stats.current.grid_use if data.stats else None,
    ),
    FranklinWHSensorEntityDescription(
        key="grid_import_power",
        name="Grid Import Power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: (
            max(data.stats.current.grid_use, 0) if data.stats else None
        ),
    ),
    FranklinWHSensorEntityDescription(
        key="grid_export_power",
        name="Grid Export Power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: (
            abs(min(data.stats.current.grid_use, 0)) if data.stats else None
        ),
    ),
    FranklinWHSensorEntityDescription(
        key="grid_import",
        name="Grid Import",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        last_reset_fn=_local_day_start,
        value_fn=lambda data: data.stats.totals.grid_import if data.stats else None,
    ),
    FranklinWHSensorEntityDescription(
        key="grid_export",
        name="Grid Export",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        last_reset_fn=_local_day_start,
        value_fn=lambda data: data.stats.totals.grid_export if data.stats else None,
    ),
    FranklinWHSensorEntityDescription(
        key="solar_production",
        name="Solar Production",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.stats.current.solar_production if data.stats else None,
    ),
    FranklinWHSensorEntityDescription(
        key="solar_energy",
        name="Solar Energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        last_reset_fn=_local_day_start,
        value_fn=lambda data: data.stats.totals.solar if data.stats else None,
    ),
    FranklinWHSensorEntityDescription(
        key="generator_use",
        name="Generator Use",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.stats.current.generator_production if data.stats else None,
    ),
    FranklinWHSensorEntityDescription(
        key="generator_energy",
        name="Generator Energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.stats.totals.generator if data.stats else None,
    ),
    FranklinWHSensorEntityDescription(
        key="switch_1_load",
        name="Switch 1 Load",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.stats.current.switch_1_load if data.stats else None,
    ),
    FranklinWHSensorEntityDescription(
        key="switch_1_lifetime_use",
        name="Switch 1 Lifetime Use",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: (data.stats.totals.switch_1_use / 1000) if data.stats else None,
    ),
    FranklinWHSensorEntityDescription(
        key="switch_2_load",
        name="Switch 2 Load",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.stats.current.switch_2_load if data.stats else None,
    ),
    FranklinWHSensorEntityDescription(
        key="switch_2_lifetime_use",
        name="Switch 2 Lifetime Use",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: (data.stats.totals.switch_2_use / 1000) if data.stats else None,
    ),
    FranklinWHSensorEntityDescription(
        key="v2l_use",
        name="V2L Use",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.stats.current.v2l_use if data.stats else None,
    ),
    FranklinWHSensorEntityDescription(
        key="v2l_export",
        name="V2L Export",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: (data.stats.totals.v2l_export / 1000) if data.stats else None,
    ),
    FranklinWHSensorEntityDescription(
        key="v2l_import",
        name="V2L Import",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: (data.stats.totals.v2l_import / 1000) if data.stats else None,
    ),
    FranklinWHSensorEntityDescription(
        key="home_energy_total",
        name="Home Energy Total",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.stats.totals.home_use if data.stats else None,
    ),
    FranklinWHSensorEntityDescription(
        key="used_today",
        name="Used Today",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.stats.totals.home_use if data.stats else None,
    ),
    FranklinWHSensorEntityDescription(
        key="produced_today",
        name="Produced Today",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.stats.totals.solar if data.stats else None,
    ),
    FranklinWHSensorEntityDescription(
        key="savings_today",
        name="Savings Today",
        value_fn=lambda data: data.benefit_info.savings_today if data.benefit_info else None,
    ),
    FranklinWHSensorEntityDescription(
        key="estimated_backup_time",
        name="Estimated Backup Time",
        value_fn=lambda data: (
            _format_backup_time(data.charge_power_details.estimated_backup_minutes)
            if data.charge_power_details
            else None
        ),
    ),
    FranklinWHSensorEntityDescription(
        key="solar_to_home",
        name="Solar to Home",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.stats.totals.solar_to_home if data.stats else None,
    ),
    FranklinWHSensorEntityDescription(
        key="grid_to_home",
        name="Grid to Home",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.stats.totals.grid_to_home if data.stats else None,
    ),
    FranklinWHSensorEntityDescription(
        key="battery_to_home",
        name="Battery to Home",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.stats.totals.battery_to_home if data.stats else None,
    ),
    FranklinWHSensorEntityDescription(
        key="generator_to_home",
        name="Generator to Home",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.stats.totals.generator_to_home if data.stats else None,
    ),
    FranklinWHSensorEntityDescription(
        key="grid_to_battery",
        name="Grid to Battery",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.stats.totals.grid_to_battery if data.stats else None,
    ),
    FranklinWHSensorEntityDescription(
        key="solar_to_battery",
        name="Solar to Battery",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.stats.totals.solar_to_battery if data.stats else None,
    ),
    FranklinWHSensorEntityDescription(
        key="solar_to_grid",
        name="Solar to Grid",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.stats.totals.solar_to_grid if data.stats else None,
    ),
    FranklinWHSensorEntityDescription(
        key="battery_to_grid",
        name="Battery to Grid",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.stats.totals.battery_to_grid if data.stats else None,
    ),
    FranklinWHSensorEntityDescription(
        key="ambient_temperature",
        name="Ambient Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.stats.totals.ambient_temperature if data.stats else None,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up FranklinWH sensor based on a config entry."""
    coordinator: FranklinWHCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities([
        FranklinWHSensorEntity(coordinator, description, entry)
        for description in SENSOR_TYPES
    ])

    # Dynamically add aPower device sensors as units are discovered
    known_apowers: set[str] = set()

    def _add_new_apowers() -> None:
        if not coordinator.data or not coordinator.data.apowers_info:
            return
        new_entities = []
        for apower in coordinator.data.apowers_info:
            sn = apower.apower_sn
            if sn not in known_apowers:
                known_apowers.add(sn)
                new_entities.extend([
                    FranklinWHApowerSocSensor(coordinator, sn, entry),
                    FranklinWHApowerRemainingEnergySensor(coordinator, sn, entry),
                    FranklinWHApowerCurrentPowerSensor(coordinator, sn, entry),
                    FranklinWHApowerStatusSensor(coordinator, sn, entry),
                    FranklinWHApowerRatedCapacitySensor(coordinator, sn, entry),
                    FranklinWHApowerRatedPowerSensor(coordinator, sn, entry),
                ])
        if new_entities:
            async_add_entities(new_entities)

    entry.async_on_unload(coordinator.async_add_listener(_add_new_apowers))
    _add_new_apowers()


class FranklinWHSensorEntity(CoordinatorEntity[FranklinWHCoordinator], SensorEntity):
    """Representation of a FranklinWH sensor."""

    entity_description: FranklinWHSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FranklinWHCoordinator,
        description: FranklinWHSensorEntityDescription,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        
        gateway_id = entry.data[CONF_GATEWAY_ID]
        
        # Set unique ID
        self._attr_unique_id = f"{gateway_id}_{description.key}"
        
        # Set device info
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, gateway_id)},
            name=f"FranklinWH {gateway_id[-6:]}",
            manufacturer=MANUFACTURER,
            model=MODEL,
            sw_version=entry.data.get("sw_version"),
        )

    @property
    def native_value(self) -> Any:
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

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            super().available
            and self.coordinator.data is not None
            and self.coordinator.data.stats is not None
        )

    @property
    def last_reset(self) -> datetime | None:
        """Return last reset for daily total sensors."""
        if self.entity_description.last_reset_fn is None:
            return None
        try:
            return self.entity_description.last_reset_fn(self.coordinator.data)
        except (AttributeError, TypeError, ValueError) as err:
            _LOGGER.debug(
                "Error getting last_reset for %s: %s",
                self.entity_description.key,
                err,
            )
            return None


class FranklinWHApowerBaseSensor(CoordinatorEntity[FranklinWHCoordinator], SensorEntity):
    """Base class for per-aPower battery unit sensors."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FranklinWHCoordinator,
        apower_sn: str,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._apower_sn = apower_sn
        gateway_id = entry.data[CONF_GATEWAY_ID]
        short_sn = apower_sn[-6:]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, apower_sn)},
            name=f"FranklinWH Battery {short_sn}",
            manufacturer=MANUFACTURER,
            model="aPower",
            via_device=(DOMAIN, gateway_id),
        )

    def _get_apower(self) -> ApowerInfo | None:
        if not self.coordinator.data or not self.coordinator.data.apowers_info:
            return None
        for apower in self.coordinator.data.apowers_info:
            if apower.apower_sn == self._apower_sn:
                return apower
        return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return super().available and self._get_apower() is not None


class FranklinWHApowerSocSensor(FranklinWHApowerBaseSensor):
    """State of charge sensor for an individual aPower battery unit."""

    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_name = "State of Charge"

    def __init__(self, coordinator: FranklinWHCoordinator, apower_sn: str, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, apower_sn, entry)
        self._attr_unique_id = f"{apower_sn}_soc"

    @property
    def native_value(self) -> float | None:
        """Return the state of charge."""
        apower = self._get_apower()
        return apower.soc if apower else None


class FranklinWHApowerRemainingEnergySensor(FranklinWHApowerBaseSensor):
    """Remaining energy sensor for an individual aPower battery unit."""

    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY_STORAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_name = "Remaining Energy"

    def __init__(self, coordinator: FranklinWHCoordinator, apower_sn: str, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, apower_sn, entry)
        self._attr_unique_id = f"{apower_sn}_remaining_energy"

    @property
    def native_value(self) -> float | None:
        """Return the remaining energy in kWh."""
        apower = self._get_apower()
        return apower.remaining_power if apower else None


class FranklinWHApowerCurrentPowerSensor(FranklinWHApowerBaseSensor):
    """Current power sensor for an individual aPower battery unit."""

    _attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_name = "Current Power"

    def __init__(self, coordinator: FranklinWHCoordinator, apower_sn: str, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, apower_sn, entry)
        self._attr_unique_id = f"{apower_sn}_current_power"

    @property
    def native_value(self) -> float | None:
        """Return current power in kW."""
        apower = self._get_apower()
        return apower.current_power if apower else None


class FranklinWHApowerStatusSensor(FranklinWHApowerBaseSensor):
    """Status sensor for an individual aPower battery unit."""

    _attr_name = "Status"

    def __init__(self, coordinator: FranklinWHCoordinator, apower_sn: str, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, apower_sn, entry)
        self._attr_unique_id = f"{apower_sn}_status"

    @property
    def native_value(self) -> str | None:
        """Return the status text."""
        apower = self._get_apower()
        if not apower:
            return None
        return APOWER_STATUS_MAP.get(apower.status, f"Code {apower.status}")


class FranklinWHApowerRatedCapacitySensor(FranklinWHApowerBaseSensor):
    """Rated capacity sensor for an individual aPower battery unit."""

    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY_STORAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_name = "Rated Capacity"

    def __init__(self, coordinator: FranklinWHCoordinator, apower_sn: str, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, apower_sn, entry)
        self._attr_unique_id = f"{apower_sn}_rated_capacity"

    @property
    def native_value(self) -> float | None:
        """Return the rated capacity in kWh."""
        apower = self._get_apower()
        return apower.rated_capacity if apower else None


class FranklinWHApowerRatedPowerSensor(FranklinWHApowerBaseSensor):
    """Rated power sensor for an individual aPower battery unit."""

    _attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_name = "Rated Power"

    def __init__(self, coordinator: FranklinWHCoordinator, apower_sn: str, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, apower_sn, entry)
        self._attr_unique_id = f"{apower_sn}_rated_power"

    @property
    def native_value(self) -> float | None:
        """Return the rated power in kW."""
        apower = self._get_apower()
        return apower.rated_power if apower else None
