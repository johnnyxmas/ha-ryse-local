"""Cover platform for RYSE SmartBridge (local)."""

from __future__ import annotations

from typing import Any

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

from . import RyseConfigEntry, RyseCoordinator, RyseGear
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RyseConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up shades from a config entry."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        RyseShade(coordinator, entry, gear_id)
        for gear_id in coordinator.data
    )


class RyseShade(CoordinatorEntity[RyseCoordinator], CoverEntity):
    """A single RYSE shade.

    Position convention matches Home Assistant: 100 = fully open, 0 = closed.
    The bridge reports and accepts the same 0-100 scale.
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
            name=self._gear.name,
            manufacturer="RYSE",
            model="SmartShade",
            via_device=(DOMAIN, entry.unique_id or "bridge"),
        )

    @property
    def _gear(self) -> RyseGear | None:
        return self.coordinator.data.get(self._gear_id)

    @property
    def available(self) -> bool:
        gear = self._gear
        return super().available and gear is not None and gear.online

    @property
    def current_cover_position(self) -> int | None:
        gear = self._gear
        return gear.position if gear else None

    @property
    def is_closed(self) -> bool | None:
        gear = self._gear
        if gear is None:
            return None
        return gear.position == 0

    async def async_open_cover(self, **kwargs: Any) -> None:
        await self._set(100)

    async def async_close_cover(self, **kwargs: Any) -> None:
        await self._set(0)

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        await self._set(int(kwargs[ATTR_POSITION]))

    async def _set(self, position: int) -> None:
        await self.coordinator.client.async_set_position(self._gear_id, position)
        # The motor takes several seconds; refresh so the UI tracks it.
        await self.coordinator.async_request_refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()
