"""Switch platform for RYSE SmartBridge (local): obstacle detection.

Obstacle detection makes a shade stop when it meets resistance. Turning it off
removes that protection. The bridge takes a few seconds to apply a change, so
the entity holds the value just written until the bridge reports it (or
PENDING_TIMEOUT passes) instead of snapping back to the old reading.
"""

from __future__ import annotations

import time
from typing import Any

from pyryse import Gear

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import RyseConfigEntry, RyseCoordinator
from .const import DOMAIN, PENDING_TIMEOUT


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RyseConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up obstacle-detection switches for gears that report the setting."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        RyseObstacleSwitch(coordinator, entry, gear_id)
        for gear_id, gear in coordinator.data.items()
        if gear.obstacle_detection is not None
    )


class RyseObstacleSwitch(CoordinatorEntity[RyseCoordinator], SwitchEntity):
    """Obstacle detection for one shade."""

    _attr_has_entity_name = True
    _attr_translation_key = "obstacle_detection"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:shield-alert-outline"

    def __init__(
        self,
        coordinator: RyseCoordinator,
        entry: RyseConfigEntry,
        gear_id: str,
    ) -> None:
        super().__init__(coordinator)
        self._gear_id = gear_id
        self._attr_unique_id = f"{entry.unique_id}_{gear_id}_obstacle_detection"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, gear_id)})
        # (value just written, time it was written)
        self._pending: tuple[bool, float] | None = None

    @property
    def _gear(self) -> Gear | None:
        return self.coordinator.data.get(self._gear_id)

    @property
    def available(self) -> bool:
        gear = self._gear
        return (
            super().available
            and gear is not None
            and gear.online
            and gear.obstacle_detection is not None
        )

    @property
    def is_on(self) -> bool | None:
        gear = self._gear
        if gear is None or gear.obstacle_detection is None:
            return None
        actual = bool(gear.obstacle_detection)
        if self._pending is not None:
            wanted, written_at = self._pending
            if actual == wanted or time.monotonic() - written_at > PENDING_TIMEOUT:
                self._pending = None
            else:
                return wanted
        return actual

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._set(False)

    async def _set(self, enabled: bool) -> None:
        await self.coordinator.bridge.async_set_obstacle_detection(
            self._gear_id, enabled
        )
        self._pending = (enabled, time.monotonic())
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()
