"""RYSE SmartBridge (local) integration.

Device/protocol code lives in the `pyryse` library; this integration is the
Home Assistant glue (config entry, polling coordinator, cover platform).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta

from pyryse import Device, Gear, RyseBridge, RyseError

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_HOST,
    CONF_SERIAL,
    DOMAIN,
    REQUEST_TIMEOUT,
    SCAN_INTERVAL_SECONDS,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.COVER,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
]


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
        #: The bridge as last reported (identity, firmware, gears).
        self.device: Device | None = None

    async def _async_update_data(self) -> dict[str, Gear]:
        try:
            device = await self.bridge.async_get_device()
        except RyseError as err:
            raise UpdateFailed(str(err)) from err
        self.device = device
        return {gear.id: gear for gear in device.gears}


@dataclass
class RyseRuntimeData:
    """Stored on the config entry."""

    coordinator: RyseCoordinator
    bridge: RyseBridge
    #: Device-registry id of the bridge; shades hang off it.
    bridge_device_id: str


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

    device = coordinator.device
    assert device is not None  # set by the successful first refresh  # noqa: S101
    connections = (
        {(dr.CONNECTION_NETWORK_MAC, dr.format_mac(device.mac))}
        if device.mac
        else set()
    )
    bridge_device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.unique_id or device.id)},
        connections=connections,
        manufacturer="RYSE",
        model="SmartBridge",
        name=device.name,
        sw_version=device.fw_version,
        hw_version=device.hw_version,
        configuration_url=f"http://{entry.data[CONF_HOST]}",
    )

    entry.runtime_data = RyseRuntimeData(
        coordinator=coordinator,
        bridge=bridge,
        bridge_device_id=bridge_device.id,
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: RyseConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
