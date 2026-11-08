"""Sensor platform for RYSE SmartBridge (local).

Battery is only available via pyryse's detailed device fetch (added in
pyryse 0.2.0); a gear with no battery data is skipped rather than shown as
an always-unknown entity. The power-source sensor reports whether a shade is
running on its battery, an AC adapter or a USB charger (pyryse 0.3.0).
"""

from __future__ import annotations

from pyryse import Gear

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory
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
    """Set up battery and power-source sensors for gears that report them."""
    coordinator = entry.runtime_data.coordinator
    entities: list[SensorEntity] = []
    for gear_id, gear in coordinator.data.items():
        if gear.battery is not None:
            entities.append(RyseBatterySensor(coordinator, entry, gear_id))
        if gear.power_type is not None:
            entities.append(RysePowerSourceSensor(coordinator, entry, gear_id))
    async_add_entities(entities)


class RyseBatterySensor(CoordinatorEntity[RyseCoordinator], SensorEntity):
    """Battery level for one RYSE shade."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_entity_registry_enabled_default = True

    def __init__(
        self,
        coordinator: RyseCoordinator,
        entry: RyseConfigEntry,
        gear_id: str,
    ) -> None:
        super().__init__(coordinator)
        self._gear_id = gear_id
        self._attr_unique_id = f"{entry.unique_id}_{gear_id}_battery"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, gear_id)},
        )

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
            and gear.battery is not None
        )

    @property
    def native_value(self) -> int | None:
        gear = self._gear
        return gear.battery if gear else None

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()


POWER_SOURCES = ["battery", "ac_adapter", "usb_charger", "unknown"]


class RysePowerSourceSensor(CoordinatorEntity[RyseCoordinator], SensorEntity):
    """How one RYSE shade is currently powered."""

    _attr_has_entity_name = True
    _attr_translation_key = "power_source"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = POWER_SOURCES
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: RyseCoordinator,
        entry: RyseConfigEntry,
        gear_id: str,
    ) -> None:
        super().__init__(coordinator)
        self._gear_id = gear_id
        self._attr_unique_id = f"{entry.unique_id}_{gear_id}_power_source"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, gear_id)})

    @property
    def _gear(self) -> Gear | None:
        return self.coordinator.data.get(self._gear_id)

    @property
    def available(self) -> bool:
        gear = self._gear
        return super().available and gear is not None and gear.online

    @property
    def native_value(self) -> str | None:
        gear = self._gear
        source = gear.power_source if gear else None
        return source.name.lower() if source is not None else None

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()
