#!/usr/bin/env python3
"""Lightweight checks for FranklinWH API-backed mode values."""

from __future__ import annotations

import asyncio
import importlib.util
import logging
from pathlib import Path
import sys
import types
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "franklin_wh"
CLIENT_PACKAGE = "franklinwh_check"
COORD_PACKAGE = "franklinwh_coord_check"


def _load_module(name: str, path: Path) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _stub_httpx() -> None:
    httpx = types.ModuleType("httpx")
    httpx.AsyncClient = object
    httpx.Request = object
    httpx.Response = object
    sys.modules["httpx"] = httpx


def _stub_homeassistant() -> None:
    homeassistant = types.ModuleType("homeassistant")
    config_entries = types.ModuleType("homeassistant.config_entries")
    core = types.ModuleType("homeassistant.core")
    exceptions = types.ModuleType("homeassistant.exceptions")
    helpers = types.ModuleType("homeassistant.helpers")
    httpx_client = types.ModuleType("homeassistant.helpers.httpx_client")
    update_coordinator = types.ModuleType(
        "homeassistant.helpers.update_coordinator"
    )

    class DataUpdateCoordinator:
        @classmethod
        def __class_getitem__(cls, _: Any) -> type:
            return cls

        def async_set_updated_data(self, data: Any) -> None:
            self.data = data

    class UpdateFailed(Exception):
        pass

    class ConfigEntryAuthFailed(Exception):
        pass

    config_entries.ConfigEntry = object
    core.HomeAssistant = object
    exceptions.ConfigEntryAuthFailed = ConfigEntryAuthFailed
    httpx_client.get_async_client = lambda _: None
    update_coordinator.DataUpdateCoordinator = DataUpdateCoordinator
    update_coordinator.UpdateFailed = UpdateFailed

    sys.modules["homeassistant"] = homeassistant
    sys.modules["homeassistant.config_entries"] = config_entries
    sys.modules["homeassistant.core"] = core
    sys.modules["homeassistant.exceptions"] = exceptions
    sys.modules["homeassistant.helpers"] = helpers
    sys.modules["homeassistant.helpers.httpx_client"] = httpx_client
    sys.modules["homeassistant.helpers.update_coordinator"] = update_coordinator


def load_client_module() -> types.ModuleType:
    _stub_httpx()
    package = types.ModuleType(CLIENT_PACKAGE)
    package.__path__ = []
    sys.modules[CLIENT_PACKAGE] = package
    _load_module(f"{CLIENT_PACKAGE}.api", COMPONENT / "franklinwh" / "api.py")
    return _load_module(
        f"{CLIENT_PACKAGE}.client", COMPONENT / "franklinwh" / "client.py"
    )


def load_coordinator_module(client: types.ModuleType) -> types.ModuleType:
    _stub_homeassistant()
    package = types.ModuleType(COORD_PACKAGE)
    package.__path__ = []
    sys.modules[COORD_PACKAGE] = package

    franklinwh = types.ModuleType(f"{COORD_PACKAGE}.franklinwh")
    franklinwh.Client = client.Client
    franklinwh.TokenFetcher = client.TokenFetcher
    franklinwh.Mode = client.Mode
    sys.modules[f"{COORD_PACKAGE}.franklinwh"] = franklinwh
    sys.modules[f"{COORD_PACKAGE}.franklinwh.client"] = client

    _load_module(f"{COORD_PACKAGE}.const", COMPONENT / "const.py")
    return _load_module(f"{COORD_PACKAGE}.coordinator", COMPONENT / "coordinator.py")


async def main() -> None:
    logging.disable(logging.CRITICAL)
    client = load_client_module()

    class FakeClient(client.Client):
        def __init__(self) -> None:
            self.gateway = "gateway-1"
            self.url_base = client.DEFAULT_URL_BASE
            self.logger = logging.getLogger("franklinwh-check")
            self.tou_data: dict[str, Any] = {}
            self.switch_status: dict[str, Any] | Exception = RuntimeError("unused")
            self.composite: dict[str, Any] | Exception = RuntimeError("unused")
            self.posts: list[tuple[str, dict[str, Any]]] = []

        async def get_gateway_tou_list(self) -> dict[str, Any]:
            return self.tou_data

        async def _switch_status(self) -> dict[str, Any]:
            if isinstance(self.switch_status, Exception):
                raise self.switch_status
            return self.switch_status

        async def get_composite_info(self) -> dict[str, Any]:
            if isinstance(self.composite, Exception):
                raise self.composite
            return self.composite

        async def _post_form(self, url: str, payload: dict[str, Any]) -> None:
            self.posts.append((url, payload))

    class GatewayListClient(client.Client):
        def __init__(self) -> None:
            self.url_base = client.DEFAULT_URL_BASE
            self.posts: list[tuple[str, Any, dict[str, Any] | None]] = []

        async def _post(
            self, url: str, payload: Any, params: dict[str, Any] | None = None
        ) -> dict[str, Any]:
            self.posts.append((url, payload, params))
            return {"result": {"list": []}}

    gateway_list = GatewayListClient()
    await gateway_list.get_gateway_tou_list()
    assert gateway_list.posts[-1][1] is None
    assert gateway_list.posts[-1][2] == {"showType": 1}

    fake = FakeClient()
    fake.tou_data = {
        "currendId": "2202",
        "list": [
            {"id": "1101", "workMode": "1", "soc": "11"},
            {"id": "2202", "workMode": "2", "soc": "35.4"},
            {"id": "3303", "workMode": "3", "soc": 98},
        ],
    }
    status = await fake.get_mode_status()
    assert status.mode_key == client.MODE_SELF_CONSUMPTION
    assert status.current_mode_id == 2202
    assert status.time_of_use_reserve == 11
    assert status.self_consumption_reserve == 35
    assert status.emergency_backup_reserve == 98

    fake.tou_data = {
        "currendId": "2202",
        "list": [
            {"id": "1101", "workMode": "1", "details": {"reserveSoc": "30"}},
            {"id": "2202", "workMode": "2", "minSoc": "30"},
            {"id": "3303", "workMode": "3", "maxSoc": "100"},
        ],
    }
    status = await fake.get_mode_status()
    assert status.time_of_use_reserve == 30
    assert status.self_consumption_reserve == 30
    assert status.emergency_backup_reserve == 100

    fake.tou_data = {
        "currendId": None,
        "list": [{"id": "1101", "workMode": "1", "soc": "12"}],
    }
    fake.switch_status = {
        "touMinSoc": "13",
        "selfMinSoc": "27.5",
        "backupMaxSoc": "97",
        "runingMode": "3",
    }
    fake.composite = {}
    status = await fake.get_mode_status()
    assert status.mode_key == client.MODE_EMERGENCY_BACKUP
    assert status.time_of_use_reserve == 12
    assert status.self_consumption_reserve is None
    assert status.emergency_backup_reserve is None

    fake.tou_data = {"list": [{"id": "4567", "workMode": "1", "oldIndex": 8}]}
    await fake.set_mode(client.Mode.time_of_use(soc=44))
    payload = fake.posts[-1][1]
    assert payload["currendId"] == "4567"
    assert payload["oldIndex"] == "8"
    assert payload["soc"] == "44"

    coordinator = load_coordinator_module(client)
    coord = object.__new__(coordinator.FranklinWHCoordinator)
    coord.data = coordinator.FranklinWHData(
        stats=object(),
        mode_status=client.ModeStatus(
            mode_key=client.MODE_SELF_CONSUMPTION,
            mode_name="Self-Consumption",
            current_mode_id=2202,
            time_of_use_reserve=12,
            self_consumption_reserve=28,
            emergency_backup_reserve=97,
        ),
    )
    coord._set_updated_mode_reserve("time_of_use", 46)
    assert coord.data.mode_status.time_of_use_reserve == 46
    assert coord.data.mode_status.self_consumption_reserve == 28
    assert coord.data.mode_status.emergency_backup_reserve == 97

    class ReserveClient:
        def __init__(self) -> None:
            self.set_modes: list[Any] = []

        async def get_mode_status(self) -> Any:
            return client.ModeStatus(
                mode_key=client.MODE_SELF_CONSUMPTION,
                mode_name="Self-Consumption",
                current_mode_id=2202,
                time_of_use_reserve=None,
                self_consumption_reserve=None,
                emergency_backup_reserve=None,
            )

        async def set_mode(self, mode: Any) -> None:
            self.set_modes.append(mode)

    reserve_client = ReserveClient()
    coord.client = reserve_client

    async def refresh() -> None:
        raise AssertionError("refresh should not run without API reserve values")

    coord.async_request_refresh = refresh
    try:
        await coord.async_set_operation_mode("self_use")
    except RuntimeError:
        pass
    else:
        raise AssertionError("mode change should fail without API reserve values")
    assert reserve_client.set_modes == []


if __name__ == "__main__":
    asyncio.run(main())
