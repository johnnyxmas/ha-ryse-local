"""Number platform for RYSE SmartBridge (local): per-shade motor speed.

The bridge stores speed as 40-100; the RYSE app shows 0-100%. This entity uses
the app's scale so the two agree. The bridge takes a few seconds to apply a
new value, so the entity holds the value just written until the bridge reports
it (or PENDING_TIMEOUT passes) instead of snapping back to the old reading.
"""

from __future__ import annotations

import time
from typing import Any

from pyryse import Gear, percent_to_speed, speed_to_percent

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import PERCENTAGE, EntityCategory
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
    """Set up speed controls for gears that report a speed."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        RyseSpeedNumber(coordinator, entry, gear_id)
        for gear_id, gear in coordinator.data.items()
        if gear.speed is not None
    )


class RyseSpeedNumber(CoordinatorEntity[RyseCoordinator], NumberEntity):
    """How fast one shade's motor moves, as the RYSE app's 0-100%."""

    _attr_has_entity_name = True
    _attr_translation_key = "speed"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:speedometer"
    _attr_mode = NumberMode.SLIDER
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(
        self,
        coordinator: RyseCoordinator,
        entry: RyseConfigEntry,
        gear_id: str,
    ) -> None:
        super().__init__(coordinator)
        self._gear_id = gear_id
        self._attr_unique_id = f"{entry.unique_id}_{gear_id}_speed"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, gear_id)})
        # (bridge speed just written, time it was written)
        self._pending: tuple[int, float] | None = None

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
            and gear.speed is not None
        )

    @property
    def native_value(self) -> int | None:
        gear = self._gear
        if gear is None or gear.speed is None:
            return None
        if self._pending is not None:
            speed, written_at = self._pending
            if gear.speed == speed or time.monotonic() - written_at > PENDING_TIMEOUT:
                self._pending = None
            else:
                return speed_to_percent(speed)
        return gear.speed_percent

    async def async_set_native_value(self, value: float) -> None:
        speed = percent_to_speed(int(value))
        await self.coordinator.bridge.async_set_speed(self._gear_id, speed)
        self._pending = (speed, time.monotonic())
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        gear = self._gear
        if gear is None or gear.speed is None:
            return None
        # The raw value the bridge stores, for anyone comparing with the API.
        return {"bridge_speed": gear.speed}
