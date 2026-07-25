"""DataUpdateCoordinator for FranklinWH."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
import time

import httpx

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.httpx_client import get_async_client
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .franklinwh import Client, TokenFetcher, Mode
from .franklinwh.client import (
    AccountLockedException,
    ApiUnavailableException,
    ApowerInfo,
    BenefitInfo,
    ChargePowerDetails,
    DeviceTimeoutException,
    GatewayOfflineException,
    InvalidCredentialsException,
    ModeStatus,
    Stats,
    SystemOverview,
    TokenExpiredException,
    MODE_EMERGENCY_BACKUP,
    MODE_LABELS,
    MODE_SELF_CONSUMPTION,
    MODE_TIME_OF_USE,
)

# Errors that represent a temporarily slow/unreachable gateway or cloud rather
# than a real fault. These are common and self-recover, so they are retried
# inline and logged quietly instead of as warnings.
# ApiUnavailableException covers AuthServiceUnavailableException, i.e. the login
# endpoint being down, which says nothing about the credentials.
TRANSIENT_ERRORS = (
    DeviceTimeoutException,
    GatewayOfflineException,
    TokenExpiredException,
    ApiUnavailableException,
    httpx.TransportError,
)

# A rejected login only becomes a reauth prompt once it has persisted for both
# this many updates and this long. The cloud hands out spurious 401s during its
# own outages, and reauth stops polling entirely until a human notices.
AUTH_FAILURE_THRESHOLD = 3
AUTH_FAILURE_GRACE = 15 * 60

# Auth-failure bookkeeping lives here rather than on the coordinator: a failed
# setup builds a new coordinator on every retry, which would otherwise reset the
# grace period and make it unreachable.
AUTH_STATE_KEY = f"{DOMAIN}_auth_state"

MODE_STRING_TO_KEY = {
    "self_use": MODE_SELF_CONSUMPTION,
    "self_consumption": MODE_SELF_CONSUMPTION,
    "backup": MODE_EMERGENCY_BACKUP,
    "emergency_backup": MODE_EMERGENCY_BACKUP,
    "clean_backup": MODE_EMERGENCY_BACKUP,
    "time_of_use": MODE_TIME_OF_USE,
}

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

        # Inline retries for the primary stats fetch when the gateway reports a
        # transient timeout. Kept short so the whole update stays well within
        # the scan interval.
        self._stats_retries = 2
        self._stats_retry_delay = 3.0

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
            stats = await self._get_stats_with_retry()

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
            elif mode_status and self.data and self.data.mode_status:
                prev_mode = self.data.mode_status
                mode_status.mode_key = mode_status.mode_key or prev_mode.mode_key
                mode_status.mode_name = mode_status.mode_name or prev_mode.mode_name
                mode_status.current_mode_id = (
                    mode_status.current_mode_id
                    if mode_status.current_mode_id is not None
                    else prev_mode.current_mode_id
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

            # Reset failure counters on success
            self._consecutive_failures = 0
            self._auth_state().clear()

            return FranklinWHData(
                stats=stats,
                switch_state=switch_state,
                apowers_info=apowers_info,
                mode_status=mode_status,
                system_overview=system_overview,
                benefit_info=benefit_info,
                charge_power_details=charge_power_details,
            )

        except InvalidCredentialsException as err:
            return self._handle_auth_failure(err)

        except AccountLockedException as err:
            # A lockout is usually the cloud rate-limiting us, and re-entering
            # the same credentials cannot clear one, so back off rather than
            # prompt. It still counts toward the grace period: if the lock
            # followed genuinely bad credentials, the first rejection after it
            # expires escalates straight away.
            _LOGGER.warning(
                "FranklinWH account is temporarily locked, backing off: %s", err
            )
            return self._handle_auth_failure(err, escalate=False)

        except Exception as err:
            return self._handle_update_failure(err)

    async def _get_stats_with_retry(self) -> Stats | None:
        """Fetch stats, retrying transient gateway timeouts inline.

        A single slow response from the gateway is common and usually succeeds
        on a quick retry, so it is handled here instead of counting against the
        consecutive-failure budget.
        """
        last_err: Exception | None = None
        for attempt in range(self._stats_retries + 1):
            try:
                return await self.client.get_stats()
            except TRANSIENT_ERRORS as err:
                last_err = err
                if attempt < self._stats_retries:
                    _LOGGER.debug(
                        "Transient gateway error fetching stats (try %d/%d): %s; "
                        "retrying in %.1fs",
                        attempt + 1,
                        self._stats_retries + 1,
                        err,
                        self._stats_retry_delay,
                    )
                    await asyncio.sleep(self._stats_retry_delay)
        # Exhausted inline retries; let the caller's failure handling take over.
        assert last_err is not None
        raise last_err

    def _auth_state(self) -> dict:
        """Return the shared auth-failure bookkeeping for this config entry."""
        store = self.hass.data.setdefault(AUTH_STATE_KEY, {})
        key = self.config_entry.entry_id if self.config_entry else self.gateway_id
        return store.setdefault(key, {})

    def _handle_auth_failure(
        self, err: Exception, escalate: bool = True
    ) -> FranklinWHData:
        """Account for the cloud rejecting our credentials.

        Reauth stops polling until someone re-enters credentials by hand, so a
        rejection is only escalated once it has outlived a transient upstream
        problem. Until then it is treated as an ordinary failure and polling
        continues, which is how a spurious 401 recovers on its own.
        """
        state = self._auth_state()
        now = time.monotonic()
        failures = state.get("failures", 0) + 1
        first_at = state.setdefault("first_at", now)
        state["failures"] = failures
        elapsed = now - first_at

        if not escalate:
            return self._handle_update_failure(err, already_logged=True)

        if failures >= AUTH_FAILURE_THRESHOLD and elapsed >= AUTH_FAILURE_GRACE:
            raise ConfigEntryAuthFailed(
                f"Credentials rejected {failures} times over "
                f"{elapsed / 60:.0f} minutes: {err}"
            )

        _LOGGER.warning(
            "Credentials rejected (%d/%d over %.0f of %.0f minutes), retrying before "
            "asking for reauthentication: %s",
            failures,
            AUTH_FAILURE_THRESHOLD,
            elapsed / 60,
            AUTH_FAILURE_GRACE / 60,
            err,
        )
        return self._handle_update_failure(err, already_logged=True)

    def _handle_update_failure(
        self, err: Exception, already_logged: bool = False
    ) -> FranklinWHData:
        """Account for a failed update.

        While under the failure threshold (and we have prior data), the last
        known data is returned to keep entities available. Transient gateway
        hiccups are logged at debug level to avoid noise; only a sustained
        outage that actually marks the device unavailable is logged louder.
        """
        self._consecutive_failures += 1
        transient = isinstance(err, TRANSIENT_ERRORS)

        if self._consecutive_failures < self._max_failures and self.data is not None:
            if not already_logged:
                log = _LOGGER.debug if transient else _LOGGER.warning
                log(
                    "API error (attempt %d/%d), keeping last known data: %s",
                    self._consecutive_failures,
                    self._max_failures,
                    err,
                )
            return self.data

        _LOGGER.error(
            "Error communicating with API after %d/%d attempts, marking unavailable: %s",
            self._consecutive_failures,
            self._max_failures,
            err,
        )
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

            try:
                mode_status = await self.client.get_mode_status()
            except Exception as err:
                raise RuntimeError(
                    "Unable to fetch API reserve values before switching modes"
                ) from err

            reserve = None
            if mode == "self_use":
                reserve = mode_status.self_consumption_reserve
            elif mode == "time_of_use":
                reserve = mode_status.time_of_use_reserve
            elif mode in ("backup", "clean_backup"):
                reserve = mode_status.emergency_backup_reserve

            if reserve is None:
                raise RuntimeError(
                    f"Unable to determine API reserve value for mode {mode}"
                )

            mode_obj = mode_map[mode](soc=reserve)

            # Set the mode via API (async method in franklinwh 1.0.0+)
            await self.client.set_mode(mode_obj)

            # Optimistically update local data so UI reflects change immediately
            if self.data and self.data.mode_status:
                new_mode_key = MODE_STRING_TO_KEY.get(mode)
                if new_mode_key:
                    existing = self.data.mode_status
                    updated_status = ModeStatus(
                        mode_key=new_mode_key,
                        mode_name=MODE_LABELS.get(new_mode_key),
                        current_mode_id=existing.current_mode_id,
                        time_of_use_reserve=existing.time_of_use_reserve,
                        self_consumption_reserve=existing.self_consumption_reserve,
                        emergency_backup_reserve=existing.emergency_backup_reserve,
                    )
                    self.async_set_updated_data(
                        FranklinWHData(
                            stats=self.data.stats,
                            switch_state=self.data.switch_state,
                            apowers_info=self.data.apowers_info,
                            mode_status=updated_status,
                            system_overview=self.data.system_overview,
                            benefit_info=self.data.benefit_info,
                            charge_power_details=self.data.charge_power_details,
                        )
                    )

            # Request immediate refresh
            await self.async_request_refresh()
            _LOGGER.info("Successfully set operation mode to %s", mode)
        except Exception as err:
            _LOGGER.error("Failed to set operation mode to %s: %s", mode, err)
            raise

    def _set_updated_mode_status(self, mode_status: ModeStatus) -> None:
        """Update coordinator data with a new mode status."""
        if not self.data:
            return

        self.async_set_updated_data(
            FranklinWHData(
                stats=self.data.stats,
                switch_state=self.data.switch_state,
                apowers_info=self.data.apowers_info,
                mode_status=mode_status,
                system_overview=self.data.system_overview,
                benefit_info=self.data.benefit_info,
                charge_power_details=self.data.charge_power_details,
            )
        )

    def _set_updated_mode_reserve(self, mode: str, reserve_percent: int) -> None:
        """Update the cached reserve value for a mode."""
        if not self.data:
            return

        mode_key = MODE_STRING_TO_KEY.get(mode)
        if mode_key is None:
            return

        existing = self.data.mode_status
        time_of_use_reserve = (
            existing.time_of_use_reserve if existing is not None else None
        )
        self_consumption_reserve = (
            existing.self_consumption_reserve if existing is not None else None
        )
        emergency_backup_reserve = (
            existing.emergency_backup_reserve if existing is not None else None
        )

        if mode_key == MODE_TIME_OF_USE:
            time_of_use_reserve = reserve_percent
        elif mode_key == MODE_SELF_CONSUMPTION:
            self_consumption_reserve = reserve_percent
        elif mode_key == MODE_EMERGENCY_BACKUP:
            emergency_backup_reserve = reserve_percent

        self._set_updated_mode_status(
            ModeStatus(
                mode_key=existing.mode_key if existing is not None else None,
                mode_name=existing.mode_name if existing is not None else None,
                current_mode_id=(
                    existing.current_mode_id if existing is not None else None
                ),
                time_of_use_reserve=time_of_use_reserve,
                self_consumption_reserve=self_consumption_reserve,
                emergency_backup_reserve=emergency_backup_reserve,
            )
        )

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
        self._set_updated_mode_reserve(mode, reserve_percent)
        await self.async_request_refresh()
        _LOGGER.info(
            "Successfully set reserve for mode %s to %d%%",
            mode,
            reserve_percent,
        )

    async def async_set_battery_reserve(self, reserve_percent: int) -> None:
        """Set the battery reserve percentage.

        This attempts to preserve the current operation mode while updating
        the battery reserve (SOC) percentage.
        """
        try:
            try:
                current_mode = await self.client.get_mode()
                _LOGGER.debug("Current mode retrieved: %s", current_mode)
            except Exception as err:
                raise RuntimeError(
                    "Unable to fetch API mode and reserve before setting reserve"
                ) from err

            current_mode_key = current_mode[0]
            mode_factory = {
                MODE_TIME_OF_USE: Mode.time_of_use,
                MODE_SELF_CONSUMPTION: Mode.self_consumption,
                MODE_EMERGENCY_BACKUP: Mode.emergency_backup,
            }.get(current_mode_key)
            if mode_factory is None:
                raise RuntimeError(
                    f"Unable to determine API mode for reserve update: {current_mode_key}"
                )

            mode_obj = mode_factory(soc=reserve_percent)

            # Async method in franklinwh 1.0.0+
            await self.client.set_mode(mode_obj)

            # Request immediate refresh
            await self.async_request_refresh()
            _LOGGER.info("Successfully set battery reserve to %d%%", reserve_percent)
        except Exception as err:
            _LOGGER.error("Failed to set battery reserve to %d%%: %s", reserve_percent, err)
            raise
