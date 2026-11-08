"""RYSE SmartBridge (local) integration.

Device/protocol code lives in the `pyryse` library; this integration is the
Home Assistant glue (config entry, polling coordinator, cover platform).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta

from pyryse import Gear, RyseBridge, RyseError

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_HOST, CONF_SERIAL, REQUEST_TIMEOUT, SCAN_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.COVER, Platform.SENSOR]


class RyseCoordinator(DataUpdateCoordinator[dict[str, Gear]]):
    """Polls the bridge and exposes gears keyed by id."""

    def __init__(self, hass: HomeAssistant, bridge: RyseBridge) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="RYSE SmartBridge",
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
        )
        self.bridge = bridge

    async def _async_update_data(self) -> dict[str, Gear]:
        try:
            device = await self.bridge.async_get_device()
        except RyseError as err:
            raise UpdateFailed(str(err)) from err
        return {gear.id: gear for gear in device.gears}


@dataclass
class RyseRuntimeData:
    """Stored on the config entry."""

    coordinator: RyseCoordinator
    bridge: RyseBridge


type RyseConfigEntry = ConfigEntry[RyseRuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: RyseConfigEntry) -> bool:
    """Set up RYSE SmartBridge from a config entry."""
    bridge = RyseBridge(
        entry.data[CONF_HOST],
        async_get_clientsession(hass),
        serial=entry.data.get(CONF_SERIAL),
        timeout=REQUEST_TIMEOUT,
    )
    coordinator = RyseCoordinator(hass, bridge)
    try:
        await coordinator.async_config_entry_first_refresh()
    except UpdateFailed as err:
        raise ConfigEntryNotReady(str(err)) from err

    entry.runtime_data = RyseRuntimeData(coordinator=coordinator, bridge=bridge)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: RyseConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
