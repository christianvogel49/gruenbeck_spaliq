"""Sensor platform for Grünbeck spaliQ."""
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, DINT_REGISTERS, INT16_REGISTERS
from .coordinator import GruenbeckCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: GruenbeckCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[GruenbeckSensor] = []

    for label, key, _start in DINT_REGISTERS:
        entities.append(
            GruenbeckSensor(
                coordinator=coordinator,
                entry=entry,
                key=key,
                name=label,
                unit=UnitOfTime.HOURS,
                device_class=SensorDeviceClass.DURATION,
                state_class=SensorStateClass.TOTAL_INCREASING,
            )
        )

    for label, key, _reg, _scale, _raw_offset, unit, dc_str in INT16_REGISTERS:
        device_class = SensorDeviceClass(dc_str) if dc_str else None
        entities.append(
            GruenbeckSensor(
                coordinator=coordinator,
                entry=entry,
                key=key,
                name=label,
                unit=unit,
                device_class=device_class,
                state_class=SensorStateClass.MEASUREMENT,
            )
        )

    async_add_entities(entities)


class GruenbeckSensor(CoordinatorEntity, SensorEntity):
    """A numeric sensor backed by one Modbus register (DInt or Int16)."""

    def __init__(
        self,
        coordinator: GruenbeckCoordinator,
        entry: ConfigEntry,
        key: str,
        name: str,
        unit: str,
        device_class: SensorDeviceClass | None,
        state_class: SensorStateClass,
    ) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_name = name
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Grünbeck spaliQ",
            manufacturer="Grünbeck",
            model="spaliQ Professional",
        )

    @property
    def native_value(self):
        return self.coordinator.data.get(self._key)
