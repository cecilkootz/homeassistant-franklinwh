"""Client for interacting with FranklinWH gateway API.

This module provides classes and functions to authenticate, send commands,
and retrieve statistics from FranklinWH energy gateway devices.
"""

from __future__ import annotations
from collections.abc import Callable

import asyncio
from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import logging
import time
import zlib

import httpx

from .api import DEFAULT_URL_BASE


class AccessoryType(Enum):
    """Represents the type of accessory connected to the FranklinWH gateway.

    Attributes:
        SMART_CIRCUIT_MODULE (int): A Smart Circuit module, see https://www.franklinwh.com/document/download/smart-circuits-module-installation-guide-sku-accy-scv2-us
        GENERATOR_MODULE (int): A Generator module, see https://www.franklinwh.com/document/download/generator-module-installation-guide-sku-accy-genv2-us
    """

    GENERATOR_MODULE = 3
    SMART_CIRCUIT_MODULE = 4


def to_hex(inp):
    """Convert an integer to an 8-character uppercase hexadecimal string.

    Parameters
    ----------
    inp : int
        The integer to convert.

    Returns:
    -------
    str
        The hexadecimal string representation of the input.
    """
    return f"{inp:08X}"


def empty_stats():
    """Return a Stats object with all values set to zero.

    Returns:
    -------
    Stats
        A Stats object with zeroed Current and Totals values.
    """
    return Stats(
        Current(
            0.0,
            0.0,
            False,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            GridStatus.NORMAL,
            None,
            {},
        ),
        Totals(
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
        ),
    )


class GridStatus(Enum):
    """Represents the status of the grid connection for the FranklinWH gateway.

    Attributes:
        NORMAL (int): Grid connection is normal / up.
        DOWN (int): Grid connection is abnormal / down.
        OFF (int): Grid connection is turned off at the gateway.

    OFF is set by software, specifically Settings / Go Off-Grid in the app.
    DOWN is external to the gateway.
    NORMAL indicates normal operation.
    """

    NORMAL = 0
    DOWN = 1
    OFF = 2

    @staticmethod
    def from_offgridreason(value: int | None) -> GridStatus:
        """Convert an offgridreason value to a GridStatus.

        Parameters
        ----------
        value : int | None
            The offgridreason value to convert.

        Returns:
        -------
        GridStatus
            The corresponding GridStatus.
        """
        match value:
            case None | -1:
                return GridStatus.NORMAL
            case 0:
                return GridStatus.DOWN
            case 1:
                return GridStatus.OFF
            case _:
                raise ValueError(f"Unknown offgridreason value: {value}")


@dataclass
class Current:
    """Current statistics for FranklinWH gateway."""

    solar_production: float
    generator_production: float
    generator_enabled: bool
    battery_use: float
    grid_use: float
    home_load: float
    battery_soc: float
    switch_1_load: float
    switch_2_load: float
    v2l_use: float
    grid_status: GridStatus
    mode_name: str | None
    apower_power_by_sn: dict[str, float]


@dataclass
class Totals:
    """Total energy statistics for FranklinWH gateway."""

    battery_charge: float
    battery_discharge: float
    grid_import: float
    grid_export: float
    solar: float
    generator: float
    home_use: float
    switch_1_use: float
    switch_2_use: float
    v2l_export: float
    v2l_import: float
    solar_to_home: float
    grid_to_home: float
    battery_to_home: float
    generator_to_home: float
    grid_to_battery: float
    solar_to_battery: float
    solar_to_grid: float
    battery_to_grid: float
    ambient_temperature: float


@dataclass
class Stats:
    """Statistics for FranklinWH gateway."""

    current: Current
    totals: Totals


@dataclass
class ModeStatus:
    """Current selected mode and reserve settings as shown in the app."""

    mode_key: str | None
    mode_name: str | None
    current_mode_id: int | None
    time_of_use_reserve: int | None
    self_consumption_reserve: int | None
    emergency_backup_reserve: int | None

    @property
    def current_reserve(self) -> int | None:
        """Return reserve for the currently selected mode."""
        if self.mode_key == MODE_TIME_OF_USE:
            return self.time_of_use_reserve
        if self.mode_key == MODE_SELF_CONSUMPTION:
            return self.self_consumption_reserve
        if self.mode_key == MODE_EMERGENCY_BACKUP:
            return self.emergency_backup_reserve
        return None


@dataclass
class SystemOverview:
    """System-wide summary values shown in app settings/system pages."""

    apower_count: int | None
    total_storage_capacity: float | None


@dataclass
class BenefitInfo:
    """Daily benefit and savings information."""

    savings_today: float | None
    currency: str | None


@dataclass
class ChargePowerDetails:
    """Estimated backup runtime details."""

    estimated_backup_minutes: int | None
    estimated_backup_text: str | None


@dataclass
class ApowerInfo:
    """Information about an individual aPower battery unit in the cluster."""

    apower_sn: str
    rated_power: float  # kW
    rated_capacity: float  # kWh
    status: int
    remaining_power: float  # kWh
    soc: float  # %
    current_power: float | None = None  # kW (negative = charging, positive = discharging)


MODE_TIME_OF_USE = "time_of_use"
MODE_SELF_CONSUMPTION = "self_consumption"
MODE_EMERGENCY_BACKUP = "emergency_backup"

MODE_MAP = {
    9322: MODE_TIME_OF_USE,
    9323: MODE_SELF_CONSUMPTION,
    9324: MODE_EMERGENCY_BACKUP,
}

WORK_MODE_MAP = {
    1: MODE_TIME_OF_USE,
    2: MODE_SELF_CONSUMPTION,
    3: MODE_EMERGENCY_BACKUP,
}

MODE_LABELS = {
    MODE_TIME_OF_USE: "Time of Use (TOU)",
    MODE_SELF_CONSUMPTION: "Self-Consumption",
    MODE_EMERGENCY_BACKUP: "Emergency Backup",
}


class Mode:
    """Represents an operating mode for the FranklinWH gateway.

    Provides static methods to create specific modes (time of use, emergency backup, self consumption)
    and generates payloads for API requests to set the gateway's operating mode.

    Attributes:
    ----------
    soc : int
        The state of charge value for the mode.
    currendId : int | None
        The current mode identifier.
    workMode : int | None
        The work mode value.

    Methods:
    -------
    time_of_use(soc=20)
        Create a time of use mode instance.
    emergency_backup(soc=100)
        Create an emergency backup mode instance.
    self_consumption(soc=20)
        Create a self consumption mode instance.
    payload(gateway)
        Generate the payload dictionary for API requests.
    """

    @staticmethod
    def time_of_use(soc=20):
        """Create a time of use mode instance.

        Parameters
        ----------
        soc : int, optional
            The state of charge value for the mode, defaults to 20.

        Returns:
        -------
        Mode
            An instance of Mode configured for time of use.
        """
        mode = Mode(soc)
        mode.currendId = 9322
        mode.workMode = 1
        return mode

    @staticmethod
    def emergency_backup(soc=100):
        """Create an emergency backup mode instance.

        Parameters
        ----------
        soc : int, optional
            The state of charge value for the mode, defaults to 100.

        Returns:
        -------
        Mode
            An instance of Mode configured for emergency backup.
        """
        mode = Mode(soc)
        mode.currendId = 9324
        mode.workMode = 3
        return mode

    @staticmethod
    def self_consumption(soc=20):
        """Create a self consumption mode instance.

        Parameters
        ----------
        soc : int, optional
            The state of charge value for the mode, defaults to 20.

        Returns:
        -------
        Mode
            An instance of Mode configured for self consumption.
        """
        mode = Mode(soc)
        mode.currendId = 9323
        mode.workMode = 2
        return mode

    def __init__(self, soc: int) -> None:
        """Initialize a Mode instance with the given state of charge.

        Parameters
        ----------
        soc : int
            The state of charge value for the mode.
        """
        self.soc = soc
        self.currendId = None
        self.workMode = None

    def payload(self, gateway) -> dict:
        """Generate the payload dictionary for API requests to set the gateway's operating mode.

        Parameters
        ----------
        gateway : str
            The gateway identifier.

        Returns:
        -------
        dict
            The payload dictionary for the API request.
        """
        return {
            "currendId": str(self.currendId),
            "gatewayId": gateway,
            "lang": "EN_US",
            "oldIndex": "1",  # Who knows if this matters
            "soc": str(self.soc),
            "stromEn": "1",
            "workMode": str(self.workMode),
        }


class SwitchState(tuple[bool | None, bool | None, bool | None]):
    """Represents the state of the smart switches connected to the FranklinWH gateway.

    Each element in the tuple corresponds to a switch:
        - True: Switch is ON
        - False: Switch is OFF
        - None: Switch state is unchanged
    """

    __slots__ = ()

    def __new__(cls, lst: list[bool | None] | None = None):
        """Convert a list to a SwitchState tuple.

        Parameters
        ----------
        lst : optional list[bool | None]
            The list to convert, defaults to [None, None, None].

        Returns:
        -------
        SwitchState
            The converted SwitchState tuple.
        """
        if lst is None:
            lst = [None, None, None]

        if len(lst) != 3:
            raise ValueError(
                "List must have exactly 3 elements to convert to SwitchState."
            )
        return super().__new__(cls, lst)


class TokenExpiredException(Exception):
    """raised when the token has expired to signal upstream that you need to create a new client or inject a new token."""


class AccountLockedException(Exception):
    """raised when the account is locked."""


class InvalidCredentialsException(Exception):
    """raised when the credentials are invalid."""


class DeviceTimeoutException(Exception):
    """raised when the device times out."""


class GatewayOfflineException(Exception):
    """raised when the gateway is offline."""


class HttpClientFactory:
    """Factory to create AsyncClient."""

    @staticmethod
    def default_get_client() -> httpx.AsyncClient:
        """Create an HTTP/2 AsyncClient."""
        return httpx.AsyncClient(http2=True)

    factory: Callable[..., httpx.AsyncClient] = default_get_client

    @classmethod
    def set_client_factory(cls, factory: Callable[..., httpx.AsyncClient]) -> None:
        """Set AsyncClient factory method."""
        cls.factory = factory

    @classmethod
    def get_client(cls) -> httpx.AsyncClient:
        """Create an AsyncClient via factory method."""
        return cls.factory()


class TokenFetcher(HttpClientFactory):
    """Fetches and refreshes authentication tokens for FranklinWH API."""

    def __init__(self, username: str, password: str, session: httpx.AsyncClient | None = None) -> None:
        """Initialize the TokenFetcher with the provided username and password."""
        self.username = username
        self.password = password
        self.info: dict | None = None
        self._session = session

    async def get_token(self):
        """Fetch a new authentication token using the stored credentials.

        Store the intermediate account information in self.info.
        """
        self.info = await self.fetch_token()
        return self.info["token"]

    @staticmethod
    async def login(username: str, password: str):
        """Log in to the FranklinWH API and retrieve an authentication token."""
        await TokenFetcher(username, password).get_token()

    async def fetch_token(self) -> dict:
        """Log in to the FranklinWH API and retrieve account information."""
        url = (
            DEFAULT_URL_BASE + "hes-gateway/terminal/initialize/appUserOrInstallerLogin"
        )
        form = {
            "account": self.username,
            "password": hashlib.md5(bytes(self.password, "ascii")).hexdigest(),
            "lang": "en_US",
            "type": 1,
        }
        if self._session is not None:
            res = await self._session.post(url, data=form, timeout=10)
        else:
            async with self.get_client() as client:
                res = await client.post(url, data=form, timeout=10)
        res.raise_for_status()
        js = res.json()

        if js["code"] == 401:
            raise InvalidCredentialsException(js["message"])

        if js["code"] == 400:
            raise AccountLockedException(js["message"])

        return js["result"]


async def retry(func, filter, refresh_func):
    """Tries calling func, and if filter fails it calls refresh func then tries again."""
    res = await func()
    if filter(res):
        return res
    await refresh_func()
    return await func()


class Client(HttpClientFactory):
    """Client for interacting with FranklinWH gateway API."""

    def __init__(
        self, fetcher: TokenFetcher, gateway: str, url_base: str = DEFAULT_URL_BASE, session: httpx.AsyncClient | None = None
    ) -> None:
        """Initialize the Client with the provided TokenFetcher, gateway ID, and optional URL base."""
        self.fetcher = fetcher
        self.gateway = gateway
        self.url_base = url_base
        self.token = ""
        self.snno = 0
        self.session = session if session is not None else self.get_client()

        # to enable detailed logging add this to configuration.yaml:
        # logger:
        #   logs:
        #     franklinwh: debug

        self.logger = logging.getLogger("franklinwh")
        self.logger.debug("Session class: %s", type(self.session))
        if self.logger.isEnabledFor(logging.DEBUG):

            async def debug_request(request: httpx.Request):
                body = request.content
                if body and request.headers.get("Content-Type", "").startswith(
                    "application/json"
                ):
                    body = json.dumps(json.loads(body), ensure_ascii=False)
                self.logger.debug(
                    "Request: %s %s %s %s",
                    request.method,
                    request.url,
                    request.headers,
                    body,
                )
                return request

            async def debug_response(response: httpx.Response):
                await response.aread()
                self.logger.debug(
                    "Response: %s %s %s %s",
                    response.status_code,
                    response.url,
                    response.headers,
                    response.json(),
                )
                return response

            self.session.event_hooks["request"].append(debug_request)
            self.session.event_hooks["response"].append(debug_response)

    # TODO(richo) Setup timeouts and deal with them gracefully.
    async def _post(self, url, payload, params: dict | None = None):
        self.logger.debug("[cloud] POST %s", url)
        if params is not None:
            params = params.copy()
            params.update({"gatewayId": self.gateway, "lang": "en_US"})

        async def __post():
            return (
                await self.session.post(
                    url,
                    params=params,
                    headers={
                        "loginToken": self.token,
                        "Content-Type": "application/json",
                    },
                    data=payload,
                )
            ).json()

        return await retry(__post, lambda j: j["code"] != 401, self.refresh_token)

    async def _post_form(self, url, payload):
        self.logger.debug("[cloud] POST (form) %s", url)
        async def __post():
            return (
                await self.session.post(
                    url,
                    headers={
                        "loginToken": self.token,
                        "Content-Type": "application/x-www-form-urlencoded",
                        "optsource": "3",
                    },
                    data=payload,
                )
            ).json()

        return await retry(__post, lambda j: j["code"] != 401, self.refresh_token)

    async def _get(self, url, params: dict | None = None):
        self.logger.debug("[cloud] GET %s", url)
        if params is None:
            params = {}
        else:
            params = params.copy()
        params.update({"gatewayId": self.gateway, "lang": "en_US"})

        async def __get():
            return (
                await self.session.get(
                    url, params=params, headers={"loginToken": self.token}
                )
            ).json()

        return await retry(__get, lambda j: j["code"] != 401, self.refresh_token)

    async def refresh_token(self):
        """Refresh the authentication token using the TokenFetcher."""
        self.token = await self.fetcher.get_token()

    async def get_accessories(self):
        """Get the list of accessories connected to the gateway."""
        url = self.url_base + "hes-gateway/common/getAccessoryList"
        # with no accessories this returns:
        # {"code":200,"message":"Query success!","result":[],"success":true,"total":0}
        return (await self._get(url))["result"]

    async def get_smart_switch_state(self) -> SwitchState:
        """Get the current state of the smart switches."""
        # TODO(richo) This API is super in flux, both because of how vague the
        # underlying API is and also trying to figure out what to do with
        # inconsistency.
        # Whether this should use the _switch_status() API is super unclear.
        # Maybe I will reach out to FranklinWH once I have published.
        status = await self._status()
        switches = [x == 1 for x in status["pro_load"]]
        return SwitchState(switches)

    async def set_smart_switch_state(self, state: SwitchState):
        """Set the state of the smart circuits.

        Setting a value in the state tuple to True will turn on that circuit,
        setting to False will turn it off. Setting to None will make it
        unchanged.
        """

        payload = await self._switch_status()
        payload["opt"] = 1
        payload.pop("modeChoose")
        payload.pop("result")

        if payload["SwMerge"] == 1:
            if state[0] != state[1]:
                raise RuntimeError(
                    "Smart switches 1 and 2 are merged! Setting them to different values could do bad things to your house. Aborting."
                )

        def set_value(keys, value):
            for k in keys:
                payload[k] = value

        for i in range(3):
            sw = i + 1
            if state[i] is not None:
                mode = f"Sw{sw}Mode"
                msg_type = f"Sw{sw}MsgType"
                pro_load = f"Sw{sw}ProLoad"

                payload[msg_type] = 1
                payload[mode] = int(bool(state[i]))
                payload[pro_load] = payload[mode] ^ 1

        wire_payload = self._build_payload(311, payload)
        data = (await self._mqtt_send(wire_payload))["result"]["dataArea"]
        return json.loads(data)

    # Sends a 203 which is a high level status
    async def _status(self):
        payload = self._build_payload(203, {"opt": 1, "refreshData": 1})
        data = (await self._mqtt_send(payload))["result"]["dataArea"]
        return json.loads(data)

    # Sends a 311 which appears to be a more specific switch command
    async def _switch_status(self):
        payload = self._build_payload(311, {"opt": 0, "order": self.gateway})
        data = (await self._mqtt_send(payload))["result"]["dataArea"]
        return json.loads(data)

    # Sends a 353 which grabs real-time smart-circuit load information
    # https://github.com/richo/homeassistant-franklinwh/issues/27#issuecomment-2714422732
    async def _switch_usage(self):
        payload = self._build_payload(353, {"opt": 0, "order": self.gateway})
        data = (await self._mqtt_send(payload))["result"]["dataArea"]
        return json.loads(data)

    async def set_mode(self, mode):
        """Set the operating mode of the FranklinWH gateway."""
        # Time of use:
        # currendId=9322&gatewayId=___&lang=EN_US&oldIndex=3&soc=15&stromEn=1&workMode=1

        # Emergency Backup:
        # currendId=9324&gatewayId=___&lang=EN_US&oldIndex=1&soc=100&stromEn=1&workMode=3

        # Self consumption
        # currendId=9323&gatewayId=___&lang=EN_US&oldIndex=2&soc=20&stromEn=1&workMode=2
        url = DEFAULT_URL_BASE + "hes-gateway/terminal/tou/updateTouMode"
        payload = mode.payload(self.gateway)
        # The cloud API now uses per-site mode IDs. Resolve current IDs from TOU list.
        try:
            tou_data = await self.get_gateway_tou_list()
            for item in tou_data.get("list", []):
                if item.get("workMode") == mode.workMode:
                    payload["currendId"] = str(item["id"])
                    if "oldIndex" in item:
                        payload["oldIndex"] = str(item["oldIndex"])
                    break
        except Exception:
            # Fall back to the static IDs used by older firmware.
            pass
        await self._post_form(url, payload)

    async def get_mode(self):
        """Get the current operating mode of the FranklinWH gateway."""
        mode_status = await self.get_mode_status()
        if mode_status.mode_key is None:
            raise RuntimeError("Unable to determine active mode")
        reserve = mode_status.current_reserve
        if reserve is None:
            raise RuntimeError(f"Unable to determine reserve for mode {mode_status.mode_key}")
        return (mode_status.mode_key, reserve)

    async def get_stats(self) -> Stats:
        """Get current statistics for the FHP.

        This includes instantaneous measurements for current power, as well as totals for today (in local time)
        """
        status_data, sw_data = await asyncio.gather(self._status(), self._switch_usage())
        data = status_data
        grid_status: GridStatus = GridStatus.NORMAL
        if "offgridreason" in data:
            grid_status = GridStatus.from_offgridreason(data["offgridreason"])
        elif data.get("elecnet_state") == 1:
            grid_status = GridStatus.DOWN

        apower_power_by_sn: dict[str, float] = {}
        fhp_sns = data.get("fhpSn", [])
        fhp_powers = data.get("fhpPower", [])
        for idx, sn in enumerate(fhp_sns):
            if idx < len(fhp_powers):
                apower_power_by_sn[str(sn)] = float(fhp_powers[idx])

        return Stats(
            Current(
                float(data.get("p_sun", 0.0)),
                float(data.get("p_gen", 0.0)),
                int(data.get("genStat", 0)) > 1,
                float(data.get("p_fhp", 0.0)),
                float(data.get("p_uti", 0.0)),
                float(data.get("p_load", 0.0)),
                float(data.get("soc", 0.0)),
                float(sw_data.get("SW1ExpPower", 0.0)),
                float(sw_data.get("SW2ExpPower", 0.0)),
                float(sw_data.get("CarSWPower", 0.0)),
                grid_status,
                data.get("name"),
                apower_power_by_sn,
            ),
            Totals(
                float(data.get("kwh_fhp_chg", 0.0)),
                float(data.get("kwh_fhp_di", 0.0)),
                float(data.get("kwh_uti_in", 0.0)),
                float(data.get("kwh_uti_out", 0.0)),
                float(data.get("kwh_sun", 0.0)),
                float(data.get("kwh_gen", 0.0)),
                float(data.get("kwh_load", 0.0)),
                float(sw_data.get("SW1ExpEnergy", 0.0)),
                float(sw_data.get("SW2ExpEnergy", 0.0)),
                float(sw_data.get("CarSWExpEnergy", 0.0)),
                float(sw_data.get("CarSWImpEnergy", 0.0)),
                float(data.get("kwhSolarLoad", 0.0)) / 1000,
                float(data.get("kwhGridLoad", 0.0)) / 1000,
                float(data.get("kwhFhpLoad", 0.0)) / 1000,
                float(data.get("kwhGenLoad", 0.0)) / 1000,
                float(data.get("gridChBat", 0.0)) / 1000,
                float(data.get("soChBat", 0.0)) / 1000,
                float(data.get("soOutGrid", 0.0)) / 1000,
                float(data.get("batOutGrid", 0.0)) / 1000,
                float(data.get("t_amb", 0.0)),
            ),
        )

    @staticmethod
    def _round_int(value: float | int | None) -> int | None:
        """Round a numeric value to int, preserving None."""
        if value is None:
            return None
        return int(round(float(value)))

    @staticmethod
    def _parse_duration_to_minutes(value: str | None) -> int | None:
        """Parse duration text like '17 hour 57 minute' or '4 day 3 hour 0 minute'."""
        if not value:
            return None

        total_minutes = 0
        parts = value.replace(",", " ").split()
        idx = 0
        while idx < len(parts) - 1:
            token = parts[idx]
            unit = parts[idx + 1].lower()
            if not token.isdigit():
                idx += 1
                continue
            number = int(token)
            if unit.startswith("day"):
                total_minutes += number * 24 * 60
            elif unit.startswith("hour"):
                total_minutes += number * 60
            elif unit.startswith("min"):
                total_minutes += number
            idx += 2

        return total_minutes or None

    def next_snno(self):
        """Get the next sequence number for API requests."""
        self.snno += 1
        return self.snno

    def _build_payload(self, ty, data):
        raw = json.dumps(data, separators=(",", ":"))
        blob = raw.encode("utf-8")
        crc = to_hex(zlib.crc32(blob))
        ts = int(time.time())

        temp = json.dumps(
            {
                "lang": "EN_US",
                "cmdType": ty,
                "equipNo": self.gateway,
                "type": 0,
                "timeStamp": ts,
                "snno": self.next_snno(),
                "len": len(blob),
                "crc": crc,
                "dataArea": "DATA",
            }
        )
        # We do it this way because without a canonical way to generate JSON we can't risk reordering breaking the CRC.
        return temp.replace('"DATA"', raw)

    async def _mqtt_send(self, payload):
        url = DEFAULT_URL_BASE + "hes-gateway/terminal/sendMqtt"

        res = await self._post(url, payload)
        if res["code"] == 102:
            raise DeviceTimeoutException(res["message"])
        if res["code"] == 136:
            raise GatewayOfflineException(res["message"])
        assert res["code"] == 200, f"{res['code']}: {res['message']}"
        return res

    async def set_grid_status(self, status: GridStatus, soc: int = 5):
        """Set the grid status of the FranklinWH gateway.

        Parameters
        ----------
        status : GridStatus
            The desired grid status to set.
        """
        url = self.url_base + "hes-gateway/terminal/updateOffgrid"
        payload = {
            "gatewayId": self.gateway,
            "offgridSet": int(status != GridStatus.NORMAL),
            "offgridSoc": soc,
        }
        await self._post(url, json.dumps(payload))

    async def get_composite_info(self):
        """Get composite information about the FranklinWH gateway."""
        url = self.url_base + "hes-gateway/terminal/getDeviceCompositeInfo"
        params = {"refreshFlag": 1}
        return (await self._get(url, params))["result"]

    async def get_gateway_tou_list(self) -> dict:
        """Get mode configuration list, including active mode and reserve SOC values."""
        url = self.url_base + "hes-gateway/terminal/tou/getGatewayTouListV2"
        return (await self._get(url))["result"]

    async def get_mode_status(self) -> ModeStatus:
        """Get current mode and reserve settings."""
        current_mode_id: int | None = None
        mode_key: str | None = None
        mode_name: str | None = None
        time_of_use_reserve: int | None = None
        self_consumption_reserve: int | None = None
        emergency_backup_reserve: int | None = None

        try:
            result = await self.get_gateway_tou_list()
            current_mode_id_raw = result.get("currendId")
            current_mode_id = (
                int(current_mode_id_raw)
                if current_mode_id_raw is not None
                else None
            )

            for item in result.get("list", []):
                work_mode = item.get("workMode")
                this_mode_key = WORK_MODE_MAP.get(work_mode)
                if this_mode_key is None:
                    continue

                soc = self._round_int(item.get("soc"))
                if this_mode_key == MODE_TIME_OF_USE:
                    time_of_use_reserve = soc
                elif this_mode_key == MODE_SELF_CONSUMPTION:
                    self_consumption_reserve = soc
                elif this_mode_key == MODE_EMERGENCY_BACKUP:
                    emergency_backup_reserve = soc

                if item.get("id") == current_mode_id:
                    mode_key = this_mode_key
                    mode_name = MODE_LABELS.get(this_mode_key, item.get("name"))
        except Exception as err:
            self.logger.debug("Falling back from TOU list mode parsing: %s", err)

        # Fallback path when TOU list data is unavailable or incomplete.
        if (
            mode_key is None
            or time_of_use_reserve is None
            or self_consumption_reserve is None
            or emergency_backup_reserve is None
        ):
            sw_status, composite = await asyncio.gather(
                self._switch_status(),
                self.get_composite_info(),
                return_exceptions=True,
            )

            sw_data: dict = {}
            if not isinstance(sw_status, Exception):
                sw_data = sw_status
                if time_of_use_reserve is None:
                    time_of_use_reserve = self._round_int(sw_data.get("touMinSoc"))
                if self_consumption_reserve is None:
                    self_consumption_reserve = self._round_int(sw_data.get("selfMinSoc"))
                if emergency_backup_reserve is None:
                    emergency_backup_reserve = self._round_int(sw_data.get("backupMaxSoc"))
                if current_mode_id is None and sw_data.get("runingMode") is not None:
                    try:
                        current_mode_id = int(sw_data["runingMode"])
                    except (TypeError, ValueError):
                        pass

            if mode_key is None and not isinstance(composite, Exception):
                runtime = composite.get("runtimeData", {})
                current_work_mode = composite.get("currentWorkMode")
                if current_work_mode is not None:
                    try:
                        mode_key = WORK_MODE_MAP.get(int(current_work_mode))
                    except (TypeError, ValueError):
                        pass
                if mode_key is None:
                    mode_key = self._mode_key_from_name(runtime.get("name"))

            if mode_key is None and sw_data.get("runingMode") is not None:
                try:
                    mode_key = MODE_MAP.get(int(sw_data["runingMode"]))
                except (TypeError, ValueError):
                    mode_key = None

            if mode_key is None and sw_data.get("name"):
                mode_key = self._mode_key_from_name(sw_data.get("name"))

        if mode_key is None and current_mode_id is not None:
            mode_key = MODE_MAP.get(current_mode_id)
        if mode_name is None and mode_key is not None:
            mode_name = MODE_LABELS.get(mode_key)

        return ModeStatus(
            mode_key=mode_key,
            mode_name=mode_name,
            current_mode_id=current_mode_id,
            time_of_use_reserve=time_of_use_reserve,
            self_consumption_reserve=self_consumption_reserve,
            emergency_backup_reserve=emergency_backup_reserve,
        )

    @staticmethod
    def _mode_key_from_name(name: str | None) -> str | None:
        """Best-effort map from runtime mode label to internal mode key."""
        if not name:
            return None
        lowered = name.lower()
        if "time" in lowered and "use" in lowered:
            return MODE_TIME_OF_USE
        if "self" in lowered:
            return MODE_SELF_CONSUMPTION
        if "backup" in lowered:
            return MODE_EMERGENCY_BACKUP
        return None

    async def get_device_overall_info(self) -> SystemOverview:
        """Get overall system values (battery count and total storage capacity)."""
        url = self.url_base + "hes-gateway/terminal/selectDeviceOverallInfo"
        result = (await self._get(url))["result"]
        return SystemOverview(
            apower_count=result.get("apowerCount"),
            total_storage_capacity=(
                float(result["totalPower"]) if result.get("totalPower") is not None else None
            ),
        )

    async def get_charge_power_details(self) -> ChargePowerDetails:
        """Get estimated backup runtime details."""
        url = self.url_base + "hes-gateway/terminal/chargePowerDetails"
        result = (await self._get(url))["result"]
        backup_text = result.get("currentTime")
        return ChargePowerDetails(
            estimated_backup_minutes=self._parse_duration_to_minutes(backup_text),
            estimated_backup_text=backup_text,
        )

    async def get_benefit_info(self) -> BenefitInfo:
        """Get daily savings information used by the app home card."""
        url = self.url_base + "hes-gateway/terminal/bill/electric/selectBenefitInfo"
        try:
            result = (await self._get(url))["result"]
        except Exception as err:
            self.logger.debug("Falling back to zero savings: %s", err)
            return BenefitInfo(savings_today=0.0, currency=None)

        savings_keys = (
            "batFeedEarnList",
            "batLoadEarnModList",
            "batLoadEarnList",
            "solarFeedEarnList",
            "solarLoadEarnList",
        )
        savings_today = 0.0
        has_value = False
        for key in savings_keys:
            values = result.get(key)
            if isinstance(values, list) and values:
                has_value = True
                savings_today += float(values[-1] or 0)

        return BenefitInfo(
            savings_today=savings_today if has_value else 0.0,
            currency=result.get("currency"),
        )

    async def set_generator(self, enabled: bool):
        """Enable or disable the generator on the FranklinWH gateway.

        Parameters
        ----------
        enabled : bool
            True to enable the generator, False to disable it.
        """
        url = self.url_base + "hes-gateway/terminal/updateIotGenerator"
        payload = {"manuSw": 1 + int(enabled), "gatewayId": self.gateway, "opt": 1}
        await self._post(url, json.dumps(payload))

    async def get_apowers_info(self) -> list[ApowerInfo]:
        """Get information about individual aPower battery units in the cluster."""
        url = self.url_base + "hes-gateway/terminal/obtainApowersInfo"
        result = (await self._get(url))["result"]
        return [
            ApowerInfo(
                apower_sn=item["apowerSn"],
                rated_power=item["ratedPower"],
                rated_capacity=item["ratedCapacity"],
                status=item["status"],
                remaining_power=item["remainingPower"],
                soc=item["soc"],
            )
            for item in result
        ]

    async def get_home_gateway_list(self):
        """Get the list of Home Gateways associated with the account.

        Returns:
        -------
        JSON payload containing the list of Home Gateway information
        - email account linked (binded), location, timezone, etc.
        - number of aGates, status (online/offline), model, firmware version, etc
        - connectivity type (4G/WiFi/Ethernet), etc
        """
        url = DEFAULT_URL_BASE + "hes-gateway/terminal/getHomeGatewayList"
        return (await self._get(url))["result"]


class UnknownMethodsClient(Client):
    """A client that also implements some methods that don't obviously work, for research purposes."""

    async def get_controllable_loads(self):
        """Get the list of controllable loads connected to the gateway."""
        url = (
            self.url_base
            + "hes-gateway/terminal/selectTerGatewayControlLoadByGatewayId"
        )
        params = {"id": self.gateway, "lang": "en_US"}
        headers = {"loginToken": self.token}
        res = await self.session.get(url, params=params, headers=headers)
        return res.json()

    async def get_accessory_list(self):
        """Get the list of accessories connected to the gateway."""
        url = self.url_base + "hes-gateway/terminal/getIotAccessoryList"
        params = {"gatewayId": self.gateway, "lang": "en_US"}
        headers = {"loginToken": self.token}
        res = await self.session.get(url, params=params, headers=headers)
        return res.json()

    async def get_equipment_list(self):
        """Get the list of equipment connected to the gateway."""
        url = self.url_base + "hes-gateway/manage/getEquipmentList"
        params = {"gatewayId": self.gateway, "lang": "en_US"}
        headers = {"loginToken": self.token}
        res = await self.session.get(url, params=params, headers=headers)
        return res.json()
