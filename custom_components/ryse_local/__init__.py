"""RYSE SmartBridge (local) integration.

Talks to the bridge's local HTTP API (no cloud):
  GET  /lua/device
  POST /lua/device/<dvc_id>/gear/<gear_id>/position   body {"position": 0-100}

Confirmed on firmware: bridge fw page dated 2023, shades fw 5.3.2 (2026-11-07).
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_HOST,
    CONF_SERIAL,
    REQUEST_TIMEOUT,
    SCAN_INTERVAL_SECONDS,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.COVER]


class RyseApiError(Exception):
    """Raised when the bridge API call fails."""


@dataclass
class RyseGear:
    """One shade as reported by the bridge."""

    gear_id: str
    name: str
    position: int
    position_state: int
    online: bool


class RyseClient:
    """Minimal async client for the bridge's local API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        serial: str | None = None,
    ) -> None:
        self._session = session
        self._host = host
        self._serial = serial
        self.dvc_id: str | None = None

    @property
    def _headers(self) -> dict[str, str]:
        # The bridge only requires Authorization when its local-security option
        # is enabled; when it is off the header is ignored. Send it if we have it.
        if self._serial:
            return {"Authorization": self._serial}
        return {}

    async def async_get_device(self) -> dict[str, Any]:
        """GET /lua/device and return the first device object."""
        url = f"http://{self._host}/lua/device"
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                resp = await self._session.get(url, headers=self._headers)
                resp.raise_for_status()
                data = await resp.json(content_type=None)
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise RyseApiError(f"GET {url} failed: {err}") from err
        if not isinstance(data, list) or not data:
            raise RyseApiError("Unexpected /lua/device response")
        device = data[0]
        self.dvc_id = device.get("dvc_id")
        return device

    async def async_list_gears(self) -> dict[str, RyseGear]:
        """Return gears keyed by gear id."""
        device = await self.async_get_device()
        gears: dict[str, RyseGear] = {}
        for g in device.get("gears", []):
            gid = g.get("id")
            if not gid:
                continue
            gears[gid] = RyseGear(
                gear_id=gid,
                name=str(g.get("name", gid)),
                position=int(g.get("position", 0)),
                position_state=int(g.get("position_state", 0)),
                online=bool(g.get("online", False)),
            )
        return gears

    async def async_set_position(self, gear_id: str, position: int) -> None:
        """POST a new position (0-100) to one gear."""
        if self.dvc_id is None:
            await self.async_get_device()
        position = max(0, min(100, int(position)))
        url = f"http://{self._host}/lua/device/{self.dvc_id}/gear/{gear_id}/position"
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                resp = await self._session.post(
                    url, json={"position": position}, headers=self._headers
                )
                resp.raise_for_status()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise RyseApiError(f"POST {url} failed: {err}") from err


class RyseCoordinator(DataUpdateCoordinator[dict[str, RyseGear]]):
    """Polls the bridge for all shade positions."""

    def __init__(self, hass: HomeAssistant, client: RyseClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="RYSE SmartBridge",
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, RyseGear]:
        try:
            return await self.client.async_list_gears()
        except RyseApiError as err:
            raise UpdateFailed(str(err)) from err


@dataclass
class RyseRuntimeData:
    """Stored on the config entry."""

    coordinator: RyseCoordinator
    client: RyseClient


type RyseConfigEntry = ConfigEntry[RyseRuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: RyseConfigEntry) -> bool:
    """Set up RYSE SmartBridge from a config entry."""
    session = async_get_clientsession(hass)
    client = RyseClient(
        session,
        host=entry.data[CONF_HOST],
        serial=entry.data.get(CONF_SERIAL),
    )
    coordinator = RyseCoordinator(hass, client)
    try:
        await coordinator.async_config_entry_first_refresh()
    except UpdateFailed as err:
        raise ConfigEntryNotReady(str(err)) from err

    entry.runtime_data = RyseRuntimeData(coordinator=coordinator, client=client)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: RyseConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
