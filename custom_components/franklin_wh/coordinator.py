"""DataUpdateCoordinator for FranklinWH."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging

from .franklinwh import Client, TokenFetcher, Mode
from .franklinwh.client import (
    ApowerInfo,
    BenefitInfo,
    ChargePowerDetails,
    ModeStatus,
    Stats,
    SystemOverview,
    MODE_EMERGENCY_BACKUP,
    MODE_SELF_CONSUMPTION,
    MODE_TIME_OF_USE,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.httpx_client import get_async_client
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class FranklinWHData:
    """Class to hold FranklinWH data."""

    def __init__(
        self,
        stats: Stats,
        switch_state: tuple[bool, bool, bool] | None = None,
        apowers_info: list[ApowerInfo] | None = None,
        mode_status: ModeStatus | None = None,
        system_overview: SystemOverview | None = None,
        benefit_info: BenefitInfo | None = None,
        charge_power_details: ChargePowerDetails | None = None,
    ) -> None:
        """Initialize the data class."""
        self.stats = stats
        self.switch_state = switch_state or (False, False, False)
        self.apowers_info = apowers_info or []
        self.mode_status = mode_status
        self.system_overview = system_overview
        self.benefit_info = benefit_info
        self.charge_power_details = charge_power_details


class FranklinWHCoordinator(DataUpdateCoordinator[FranklinWHData]):
    """Class to manage fetching FranklinWH data."""

    def __init__(
        self,
        hass: HomeAssistant,
        username: str,
        password: str,
        gateway_id: str,
        config_entry: ConfigEntry | None = None,
    ) -> None:
        """Initialize the coordinator."""
        self.username = username
        self.password = password
        self.gateway_id = gateway_id

        # Store credentials for lazy client initialization
        # Client will be created in executor during first update to avoid blocking
        self.token_fetcher: TokenFetcher = None  # type: ignore  # noqa: PGH003
        self.client: Client = None  # type: ignore  # noqa: PGH003
        self._client_lock = False

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
            # Keep entities available during temporary failures
            # Only mark unavailable after 3 consecutive failures (3 minutes)
            always_update=False,
            config_entry=config_entry,
        )

        self._http_session = get_async_client(hass)

        # Track consecutive failures
        self._consecutive_failures = 0
        self._max_failures = 3

    async def _async_update_data(self) -> FranklinWHData:
        """Fetch data from FranklinWH API."""
        try:
            # Initialize client on first run (non-blocking with injected HA httpx session)
            if self.client is None and not self._client_lock:
                self._client_lock = True
                try:
                    self.token_fetcher = TokenFetcher(
                        self.username, self.password, session=self._http_session
                    )
                    self.client = Client(
                        self.token_fetcher, self.gateway_id, session=self._http_session
                    )
                except Exception as err:
                    self._client_lock = False
                    raise UpdateFailed(f"Failed to initialize client: {err}") from err

            # Fetch stats (async method in franklinwh 1.0.0+)
            stats = await self.client.get_stats()

            if stats is None:
                raise UpdateFailed("Failed to fetch stats from FranklinWH API")

            _LOGGER.debug(
                "[cloud] metrics collected: battery_soc=%.1f%% solar=%.3fkW grid=%.3fkW "
                "battery=%.3fkW home_load=%.3fkW switch1=%.3fkW switch2=%.3fkW | "
                "totals: solar=%.2fkWh grid_import=%.2fkWh grid_export=%.2fkWh "
                "batt_charge=%.2fkWh batt_discharge=%.2fkWh home_use=%.2fkWh",
                stats.current.battery_soc if stats.current else float("nan"),
                stats.current.solar_production if stats.current else float("nan"),
                stats.current.grid_use if stats.current else float("nan"),
                stats.current.battery_use if stats.current else float("nan"),
                stats.current.home_load if stats.current else float("nan"),
                stats.current.switch_1_load if stats.current else float("nan"),
                stats.current.switch_2_load if stats.current else float("nan"),
                stats.totals.solar if stats.totals else float("nan"),
                stats.totals.grid_import if stats.totals else float("nan"),
                stats.totals.grid_export if stats.totals else float("nan"),
                stats.totals.battery_charge if stats.totals else float("nan"),
                stats.totals.battery_discharge if stats.totals else float("nan"),
                stats.totals.home_use if stats.totals else float("nan"),
            )

            (
                switch_state_res,
                apowers_info_res,
                mode_status_res,
                system_overview_res,
                benefit_info_res,
                charge_power_details_res,
            ) = await asyncio.gather(
                self.client.get_smart_switch_state(),
                self.client.get_apowers_info(),
                self.client.get_mode_status(),
                self.client.get_device_overall_info(),
                self.client.get_benefit_info(),
                self.client.get_charge_power_details(),
                return_exceptions=True,
            )

            switch_state = (
                None if isinstance(switch_state_res, Exception) else switch_state_res
            )
            if isinstance(switch_state_res, Exception):
                _LOGGER.debug("Failed to fetch switch state: %s", switch_state_res)

            apowers_info = (
                None if isinstance(apowers_info_res, Exception) else apowers_info_res
            )
            if isinstance(apowers_info_res, Exception):
                _LOGGER.debug("Failed to fetch apowers info: %s", apowers_info_res)

            mode_status = (
                None if isinstance(mode_status_res, Exception) else mode_status_res
            )
            if isinstance(mode_status_res, Exception):
                _LOGGER.debug("Failed to fetch mode status: %s", mode_status_res)
                mode_status = self.data.mode_status if self.data else None
            elif mode_status and self.data and self.data.mode_status:
                prev_mode = self.data.mode_status
                mode_status.mode_key = mode_status.mode_key or prev_mode.mode_key
                mode_status.mode_name = mode_status.mode_name or prev_mode.mode_name
                mode_status.current_mode_id = (
                    mode_status.current_mode_id
                    if mode_status.current_mode_id is not None
                    else prev_mode.current_mode_id
                )
                mode_status.time_of_use_reserve = (
                    mode_status.time_of_use_reserve
                    if mode_status.time_of_use_reserve is not None
                    else prev_mode.time_of_use_reserve
                )
                mode_status.self_consumption_reserve = (
                    mode_status.self_consumption_reserve
                    if mode_status.self_consumption_reserve is not None
                    else prev_mode.self_consumption_reserve
                )
                mode_status.emergency_backup_reserve = (
                    mode_status.emergency_backup_reserve
                    if mode_status.emergency_backup_reserve is not None
                    else prev_mode.emergency_backup_reserve
                )

            system_overview = (
                None
                if isinstance(system_overview_res, Exception)
                else system_overview_res
            )
            if isinstance(system_overview_res, Exception):
                _LOGGER.debug(
                    "Failed to fetch system overview: %s", system_overview_res
                )

            benefit_info = (
                None if isinstance(benefit_info_res, Exception) else benefit_info_res
            )
            if isinstance(benefit_info_res, Exception):
                _LOGGER.debug("Failed to fetch benefit info: %s", benefit_info_res)
                benefit_info = self.data.benefit_info if self.data else None

            charge_power_details = (
                None
                if isinstance(charge_power_details_res, Exception)
                else charge_power_details_res
            )
            if isinstance(charge_power_details_res, Exception):
                _LOGGER.debug(
                    "Failed to fetch charge power details: %s",
                    charge_power_details_res,
                )
                charge_power_details = (
                    self.data.charge_power_details if self.data else None
                )

            # Enrich per-battery entries with real-time power from runtime status.
            if apowers_info and stats.current.apower_power_by_sn:
                for apower in apowers_info:
                    apower.current_power = stats.current.apower_power_by_sn.get(
                        apower.apower_sn
                    )

            # Reset failure counter on success
            self._consecutive_failures = 0

            return FranklinWHData(
                stats=stats,
                switch_state=switch_state,
                apowers_info=apowers_info,
                mode_status=mode_status,
                system_overview=system_overview,
                benefit_info=benefit_info,
                charge_power_details=charge_power_details,
            )

        except AttributeError as err:
            # Handle case where AuthenticationError doesn't exist in franklinwh
            if "AuthenticationError" in str(type(err)):
                raise ConfigEntryAuthFailed(f"Authentication failed: {err}") from err

            # Increment failure counter
            self._consecutive_failures += 1
            _LOGGER.warning(
                "API error (attempt %d/%d): %s",
                self._consecutive_failures,
                self._max_failures,
                err
            )

            # Only raise UpdateFailed after max failures
            # This keeps entities available with last known data
            if self._consecutive_failures >= self._max_failures:
                _LOGGER.error("Max consecutive failures reached, marking unavailable")
                raise UpdateFailed(f"Error communicating with API: {err}") from err

            # Return last known data to keep entities available
            if self.data:
                _LOGGER.debug("Returning last known data due to temporary failure")
                return self.data
            raise UpdateFailed(f"Error communicating with API: {err}") from err

        except Exception as err:
            # Check if it's an authentication-related error
            if "auth" in str(err).lower() or "token" in str(err).lower():
                raise ConfigEntryAuthFailed(f"Authentication failed: {err}") from err

            # Increment failure counter
            self._consecutive_failures += 1
            _LOGGER.warning(
                "API error (attempt %d/%d): %s",
                self._consecutive_failures,
                self._max_failures,
                err
            )

            # Only raise UpdateFailed after max failures
            if self._consecutive_failures >= self._max_failures:
                _LOGGER.error("Max consecutive failures reached, marking unavailable")
                raise UpdateFailed(f"Error communicating with API: {err}") from err

            # Return last known data to keep entities available
            if self.data:
                _LOGGER.debug("Returning last known data due to temporary failure")
                return self.data
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    async def async_set_switch_state(self, switches: tuple[bool, bool, bool]) -> None:
        """Set the state of smart switches."""
        try:
            # Async method in franklinwh 1.0.0+
            await self.client.set_smart_switch_state(switches)
            # Request immediate refresh
            await self.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Failed to set switch state: %s", err)
            raise

    async def async_set_operation_mode(self, mode: str) -> None:
        """Set the operation mode of the system."""
        try:
            # Map string mode to Mode factory methods
            # Preserve currently configured reserve for each mode when switching.
            mode_map = {
                "self_use": Mode.self_consumption,
                "backup": Mode.emergency_backup,
                "time_of_use": Mode.time_of_use,
                # Note: clean_backup mode from Home Assistant services.yaml
                # Maps to emergency_backup as the library doesn't have a separate clean_backup mode
                "clean_backup": Mode.emergency_backup,
            }

            if mode not in mode_map:
                raise ValueError(f"Invalid mode: {mode}")

            reserve = 20
            if mode in ("backup", "clean_backup"):
                reserve = 100

            try:
                mode_status = await self.client.get_mode_status()
                if mode == "self_use" and mode_status.self_consumption_reserve is not None:
                    reserve = mode_status.self_consumption_reserve
                elif mode == "time_of_use" and mode_status.time_of_use_reserve is not None:
                    reserve = mode_status.time_of_use_reserve
                elif mode in ("backup", "clean_backup") and mode_status.emergency_backup_reserve is not None:
                    reserve = mode_status.emergency_backup_reserve
            except Exception as err:
                _LOGGER.debug("Could not fetch mode reserves before switching: %s", err)

            mode_obj = mode_map[mode](soc=reserve)

            # Set the mode via API (async method in franklinwh 1.0.0+)
            await self.client.set_mode(mode_obj)

            # Request immediate refresh
            await self.async_request_refresh()
            _LOGGER.info("Successfully set operation mode to %s", mode)
        except Exception as err:
            _LOGGER.error("Failed to set operation mode to %s: %s", mode, err)
            raise

    async def async_set_mode_reserve(self, mode: str, reserve_percent: int) -> None:
        """Set reserve percentage for a specific mode."""
        mode_map = {
            "self_use": Mode.self_consumption,
            "self_consumption": Mode.self_consumption,
            "backup": Mode.emergency_backup,
            "emergency_backup": Mode.emergency_backup,
            "time_of_use": Mode.time_of_use,
            "clean_backup": Mode.emergency_backup,
        }

        if mode not in mode_map:
            raise ValueError(f"Invalid mode: {mode}")

        mode_obj = mode_map[mode](soc=reserve_percent)
        await self.client.set_mode(mode_obj)
        await self.async_request_refresh()
        _LOGGER.info(
            "Successfully set reserve for mode %s to %d%%",
            mode,
            reserve_percent,
        )

    async def async_set_battery_reserve(self, reserve_percent: int) -> None:
        """Set the battery reserve percentage.

        This attempts to preserve the current operation mode while updating
        the battery reserve (SOC) percentage. If the current mode cannot be
        determined, it defaults to self_consumption mode.
        """
        try:
            # Try to get the current mode to preserve it (async method in franklinwh 1.0.0+)
            try:
                current_mode = await self.client.get_mode()
                _LOGGER.debug("Current mode retrieved: %s", current_mode)
            except Exception as err:
                _LOGGER.warning("Could not retrieve current mode, defaulting to self_consumption: %s", err)
                current_mode = None

            current_mode_key = current_mode[0] if current_mode else MODE_SELF_CONSUMPTION
            mode_factory = {
                MODE_TIME_OF_USE: Mode.time_of_use,
                MODE_SELF_CONSUMPTION: Mode.self_consumption,
                MODE_EMERGENCY_BACKUP: Mode.emergency_backup,
            }.get(current_mode_key, Mode.self_consumption)

            mode_obj = mode_factory(soc=reserve_percent)

            # Async method in franklinwh 1.0.0+
            await self.client.set_mode(mode_obj)

            # Request immediate refresh
            await self.async_request_refresh()
            _LOGGER.info("Successfully set battery reserve to %d%%", reserve_percent)
        except Exception as err:
            _LOGGER.error("Failed to set battery reserve to %d%%: %s", reserve_percent, err)
            raise
