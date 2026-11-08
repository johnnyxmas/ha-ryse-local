"""Cover platform for RYSE SmartBridge (local)."""

from __future__ import annotations

from typing import Any

from pyryse import Gear

from homeassistant.components.cover import (
    ATTR_POSITION,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import RyseConfigEntry, RyseCoordinator
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RyseConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up shades from a config entry."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        RyseShade(coordinator, entry, gear_id) for gear_id in coordinator.data
    )


class RyseShade(CoordinatorEntity[RyseCoordinator], CoverEntity):
    """A single RYSE shade.

    Position conventions are INVERTED between the two systems:
      * pyryse/bridge: 0 = fully open, 100 = fully closed.
      * Home Assistant cover: 100 = fully open, 0 = closed.
    So HA position = 100 - bridge position, and vice versa.
    """

    _attr_has_entity_name = True
    _attr_name = None
    _attr_device_class = CoverDeviceClass.SHADE
    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.SET_POSITION
    )

    def __init__(
        self,
        coordinator: RyseCoordinator,
        entry: RyseConfigEntry,
        gear_id: str,
    ) -> None:
        super().__init__(coordinator)
        self._gear_id = gear_id
        self._attr_unique_id = f"{entry.unique_id}_{gear_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, gear_id)},
            name=self._gear.name if self._gear else gear_id,
            manufacturer="RYSE",
            model="SmartShade",
            via_device=(DOMAIN, entry.unique_id or "bridge"),
        )

    @property
    def _gear(self) -> Gear | None:
        return self.coordinator.data.get(self._gear_id)

    @property
    def available(self) -> bool:
        gear = self._gear
        return super().available and gear is not None and gear.online

    @property
    def current_cover_position(self) -> int | None:
        gear = self._gear
        return 100 - gear.position if gear else None

    @property
    def is_closed(self) -> bool | None:
        gear = self._gear
        if gear is None:
            return None
        return gear.position == 100

    async def async_open_cover(self, **kwargs: Any) -> None:
        await self._set_ha(100)

    async def async_close_cover(self, **kwargs: Any) -> None:
        await self._set_ha(0)

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        await self._set_ha(int(kwargs[ATTR_POSITION]))

    async def _set_ha(self, ha_position: int) -> None:
        """Set from a Home Assistant position (100=open); bridge wants the inverse."""
        bridge_position = 100 - max(0, min(100, ha_position))
        await self.coordinator.bridge.async_set_position(
            self._gear_id, bridge_position
        )
        await self.coordinator.async_request_refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()
