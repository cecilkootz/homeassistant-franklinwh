from __future__ import annotations

import logging
from dataclasses import dataclass

import sunspec2.modbus.client as modbus_client
from sunspec2.modbus.client import (
    SunSpecModbusClientError,
    SunSpecModbusClientException,
    SunSpecModbusClientTimeout,
)

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


@dataclass
class SunSpecData:
    """Typed result from a SunSpecModbusClient read cycle.

    All power values are in watts (W) using native SunSpec sign conventions.
    Sign conventions are documented per-field below.
    """

    battery_soc: float
    """Percent (0-100). Model 713 SoC point."""

    battery_dc_power: float
    """Watts; positive = discharge, negative = charge (SunSpec Model 714 convention)."""

    solar_power: float
    """Watts; positive = production (SunSpec Model 502 convention)."""

    grid_ac_power: float
    """Watts; positive = export to grid, negative = import from grid (SunSpec Model 701 convention)."""

    home_load: float
    """Watts; computed: solar_power + battery_dc_power - grid_ac_power."""


class SunSpecModbusClient:
    """Standalone SunSpec Modbus TCP client for FranklinWH aGate.

    Reads SunSpec Models 502/701/713/714 and returns a SunSpecData instance.
    All blocking I/O is wrapped in _read_blocking(); the async read() method
    dispatches it via hass.async_add_executor_job so it never runs on the
    HA event loop.

    NOTE: Model 502 (Solar Module) is not listed in FranklinWH's SunSpec
    Alliance Product Certification Registry (which lists models 1 and 701-715).
    If model 502 is absent after scan on real hardware, a RuntimeError is raised
    with instructions to inspect device.models.keys() to identify the correct
    solar production model.
    """

    def __init__(self, host: str, port: int, slave_id: int) -> None:
        """Initialize the client with connection parameters.

        Args:
            host: Modbus TCP hostname or IP address of the FranklinWH aGate.
            port: Modbus TCP port (typically 502).
            slave_id: Modbus slave/unit ID.
        """
        self._host = host
        self._port = port
        self._slave_id = slave_id

    def _read_blocking(self) -> SunSpecData:
        """Blocking Modbus read. MUST be called from executor, never from the HA event loop.

        Creates a fresh device connection each call (connect-per-read lifecycle).
        Disconnects in a finally block to ensure cleanup even on error.
        Exceptions from pySunSpec2 and RuntimeError for missing models propagate
        to the caller — the coordinator handles retry/fallback logic.

        Returns:
            SunSpecData with all five fields populated.

        Raises:
            RuntimeError: If model 502 is not found after scan.
            SunSpecModbusClientTimeout: If the TCP connection times out.
            SunSpecModbusClientException: If a Modbus protocol error occurs.
            SunSpecModbusClientError: Base class for other pySunSpec2 errors.
        """
        device = modbus_client.SunSpecModbusClientDeviceTCP(
            slave_id=self._slave_id,
            ipaddr=self._host,
            ipport=self._port,
        )
        try:
            device.connect()
            # full_model_read=False: discover model addresses without reading all data yet;
            # connect=False because we already called device.connect() above.
            device.scan(connect=False, full_model_read=False)

            # Model 502 (Solar Module) is not in FranklinWH's registered SunSpec model list
            # (registered: 1, 701-715). Check its presence and raise an informative error
            # if absent so the user can inspect the real device to find the correct model.
            if 502 not in device.models:
                raise RuntimeError(
                    "SunSpec model 502 not found on device after scan. "
                    "FranklinWH's registered models are 1 and 701-715; "
                    "model 502 (Solar Module) may not be implemented. "
                    "Inspect device.models.keys() on real hardware to identify "
                    "the correct solar production model."
                )

            # Read each required model individually (raises SunSpecModbusClientError on failure)
            device.models[713][0].read()
            device.models[714][0].read()
            device.models[701][0].read()
            device.models[502][0].read()

            # Extract values using .cvalue (scale-factor-applied float), never .value (raw int)
            battery_soc = float(device.models[713][0].SoC.cvalue)
            grid_ac_power = float(device.models[701][0].W.cvalue)
            solar_power = float(device.models[502][0].OutPw.cvalue)

            # Model 714 DCW: prefer model-level sum; fall back to summing per-port DCSrc group.
            # FranklinWH hardware may only populate per-port values (see research open questions).
            dcw_val = device.models[714][0].DCW.cvalue
            if dcw_val is None:
                _LOGGER.debug(
                    "Model 714 model-level DCW is None; summing DCSrc port group values"
                )
                dcw_val = sum(
                    float(port.DCW.cvalue)
                    for port in device.models[714][0].groups.get("DCSrc", [])
                    if port.DCW.cvalue is not None
                )
            battery_dc_power = float(dcw_val)

            # SunSpec sign conventions: Model 701 W positive=export, Model 714 DCW positive=discharge,
            # Model 502 OutPw positive=production. Do NOT negate any of these values.
            home_load = solar_power + battery_dc_power - grid_ac_power

            _LOGGER.debug(
                "SunSpec read complete: soc=%.1f%% battery_dc=%.1fW solar=%.1fW grid=%.1fW home_load=%.1fW",
                battery_soc,
                battery_dc_power,
                solar_power,
                grid_ac_power,
                home_load,
            )

            return SunSpecData(
                battery_soc=battery_soc,
                battery_dc_power=battery_dc_power,
                solar_power=solar_power,
                grid_ac_power=grid_ac_power,
                home_load=home_load,
            )
        finally:
            device.disconnect()

    async def read(self, hass: HomeAssistant) -> SunSpecData:
        """Read all required SunSpec models. Dispatches blocking I/O to executor.

        Args:
            hass: HomeAssistant instance used to schedule the blocking read.

        Returns:
            SunSpecData with all five fields populated.
        """
        return await hass.async_add_executor_job(self._read_blocking)
