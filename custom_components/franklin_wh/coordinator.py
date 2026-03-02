"""DataUpdateCoordinator for FranklinWH."""

from __future__ import annotations

from datetime import timedelta
import logging

from .franklinwh import Client, TokenFetcher, Mode
from .franklinwh.client import Stats
from .sunspec_client import SunSpecModbusClient, SunSpecData

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.httpx_client import get_async_client
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_LOCAL_PORT, DEFAULT_LOCAL_SCAN_INTERVAL, DEFAULT_LOCAL_SLAVE_ID, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class FranklinWHData:
    """Class to hold FranklinWH data."""

    def __init__(
        self, stats: Stats, switch_state: tuple[bool, bool, bool] | None = None
    ) -> None:
        """Initialize the data class."""
        self.stats = stats
        self.switch_state = switch_state or (False, False, False)


class FranklinWHCoordinator(DataUpdateCoordinator[FranklinWHData]):
    """Class to manage fetching FranklinWH data."""

    def __init__(
        self,
        hass: HomeAssistant,
        username: str,
        password: str,
        gateway_id: str,
        use_local_api: bool = False,
        local_host: str | None = None,
        local_port: int = DEFAULT_LOCAL_PORT,
        local_slave_id: int = DEFAULT_LOCAL_SLAVE_ID,
        config_entry: ConfigEntry | None = None,
    ) -> None:
        """Initialize the coordinator."""
        self.username = username
        self.password = password
        self.gateway_id = gateway_id
        self.use_local_api = use_local_api
        self.local_host = local_host
        self.local_port = local_port
        self.local_slave_id = local_slave_id

        # Store credentials for lazy client initialization
        # Client will be created in executor during first update to avoid blocking
        self.token_fetcher: TokenFetcher = None  # type: ignore  # noqa: PGH003
        self.client: Client = None  # type: ignore  # noqa: PGH003
        self._client_lock = False

        # Lazy-initialize SunSpecModbusClient
        self._sunspec_client: SunSpecModbusClient | None = None

        # Lock for cloud data fetch (thread safety for lazy client init)
        self._cloud_data_lock = False

        # Set update interval based on API type
        update_interval = (
            DEFAULT_LOCAL_SCAN_INTERVAL if use_local_api else DEFAULT_SCAN_INTERVAL
        )

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
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

            # MODBUS PATH: When local API is enabled
            if self.use_local_api and self.local_host:
                try:
                    # Create SunSpecModbusClient lazily if not already created
                    if self._sunspec_client is None:
                        self._sunspec_client = SunSpecModbusClient(
                            host=self.local_host,
                            port=self.local_port,
                            slave_id=self.local_slave_id,
                        )

                    # Read from Modbus via executor
                    sunspec_data = await self._sunspec_client.read(self.hass)

                    # Fetch cloud data for energy totals and switch state
                    cloud_stats = await self._fetch_cloud_stats_fallback()

                    # Map SunSpecData to FranklinWHData with hybrid approach:
                    # - Current values (power flow) from Modbus
                    # - Totals (kWh) and switch state from cloud
                    return FranklinWHData(
                        stats=Stats(
                            current=self._map_sunspec_to_stats_current(sunspec_data),
                            totals=cloud_stats.totals if cloud_stats else self._get_default_totals(),
                        ),
                        switch_state=cloud_stats.switch_state if cloud_stats else None,
                    )
                except Exception as err:
                    # Log warning and fall back to cloud on any Modbus error
                    _LOGGER.warning(
                        "Modbus read failed (%s), falling back to cloud API. "
                        "Entities will remain available with last known data.",
                        err
                    )
                    # Reset Modbus client to allow recovery
                    self._sunspec_client = None
                    # Fall through to cloud path

            # Fetch stats (async method in franklinwh 1.0.0+)
            stats = await self.client.get_stats()

            if stats is None:
                raise UpdateFailed("Failed to fetch stats from FranklinWH API")

            _LOGGER.debug(
                "Stats fetched - SOC: %s%%, Solar: %skW, Grid: %skW",
                getattr(stats.current, 'battery_soc', 'N/A') if stats.current else 'N/A',
                getattr(stats.current, 'solar_production', 'N/A') if stats.current else 'N/A',
                getattr(stats.current, 'grid_use', 'N/A') if stats.current else 'N/A',
            )

            # Fetch switch state (async method in franklinwh 1.0.0+)
            try:
                switch_state = await self.client.get_smart_switch_state()
            except Exception as err:
                _LOGGER.debug("Failed to fetch switch state: %s", err)
                switch_state = None

            # Reset failure counter on success
            self._consecutive_failures = 0

            return FranklinWHData(stats=stats, switch_state=switch_state)

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

    def _map_sunspec_to_stats_current(self, sunspec_data: SunSpecData) -> Stats:
        """Map SunSpecData to Stats current values.

        SunSpec values are in native units (Watts, Percent).
        HA expects kW for power values.
        """
        from .franklinwh.client import Current, GridStatus

        return Current(
            solar_production=sunspec_data.solar_power / 1000.0,
            generator_production=0.0,
            generator_enabled=False,
            battery_use=sunspec_data.battery_dc_power / 1000.0,
            grid_use=-sunspec_data.grid_ac_power / 1000.0,
            home_load=sunspec_data.home_load / 1000.0,
            battery_soc=sunspec_data.battery_soc,
            switch_1_load=0.0,
            switch_2_load=0.0,
            v2l_use=0.0,
            grid_status=GridStatus.NORMAL,
        )

    def _get_default_totals(self) -> Stats:
        """Get default totals for Modbus mode (not available via Modbus)."""
        from .franklinwh.client import Totals

        return Totals(
            battery_charge=0.0,
            battery_discharge=0.0,
            grid_import=0.0,
            grid_export=0.0,
            solar=0.0,
            generator=0.0,
            home_use=0.0,
            switch_1_use=0.0,
            switch_2_use=0.0,
            v2l_export=0.0,
            v2l_import=0.0,
        )

    async def _fetch_cloud_stats_fallback(self) -> FranklinWHData | None:
        """Fetch cloud stats for hybrid mode fallback. Never raises - returns None on failure.

        This method is called when Modbus is enabled but we need cloud data for:
        - Energy totals (kWh values not available via Modbus)
        - Switch state
        """
        try:
            # Initialize client lazily if not already created
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
                    _LOGGER.warning("Failed to initialize cloud client for fallback: %s", err)
                    return None

            try:
                stats = await self.client.get_stats()
                if stats is None:
                    _LOGGER.debug("Cloud stats fetch returned None")
                    return None

                switch_state = None
                try:
                    switch_state = await self.client.get_smart_switch_state()
                except Exception as err:
                    _LOGGER.debug("Failed to fetch switch state: %s", err)

                return FranklinWHData(stats=stats, switch_state=switch_state)
            except Exception as err:
                _LOGGER.warning("Cloud fallback fetch failed: %s", err)
                return None
        except Exception as err:
            _LOGGER.warning("Unexpected error in cloud fallback: %s", err)
            return None

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
            # Each mode gets a default reserve of 20% except emergency_backup (100%)
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
            
            # Create mode object with default SOC
            mode_obj = mode_map[mode]()
            
            # Set the mode via API (async method in franklinwh 1.0.0+)
            await self.client.set_mode(mode_obj)
            
            # Request immediate refresh
            await self.async_request_refresh()
            _LOGGER.info("Successfully set operation mode to %s", mode)
        except Exception as err:
            _LOGGER.error("Failed to set operation mode to %s: %s", mode, err)
            raise

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

            # Create new mode with updated SOC
            # Note: We need to detect the current mode type to preserve it
            # For now, we default to self_consumption if we can't determine the mode
            # TODO: Add mode type detection when the API provides mode information
            mode_obj = Mode.self_consumption(soc=reserve_percent)

            # Async method in franklinwh 1.0.0+
            await self.client.set_mode(mode_obj)
            
            # Request immediate refresh
            await self.async_request_refresh()
            _LOGGER.info("Successfully set battery reserve to %d%%", reserve_percent)
        except Exception as err:
            _LOGGER.error("Failed to set battery reserve to %d%%: %s", reserve_percent, err)
            raise
