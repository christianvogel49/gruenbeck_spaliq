"""Binary sensor platform for Grünbeck spaliQ."""
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import BIT_REGISTERS, DOMAIN
from .coordinator import GruenbeckCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: GruenbeckCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        GruenbeckBinarySensor(
            coordinator=coordinator,
            entry=entry,
            key=key,
            name=friendly_name,
            device_class=BinarySensorDeviceClass.PROBLEM if dc_str == "problem" else None,
        )
        for _reg, _bit, key, friendly_name, dc_str in BIT_REGISTERS
    ]
    async_add_entities(entities)


class GruenbeckBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """A binary sensor backed by one bit in a Modbus status/alarm/fault word."""

    def __init__(
        self,
        coordinator: GruenbeckCoordinator,
        entry: ConfigEntry,
        key: str,
        name: str,
        device_class: BinarySensorDeviceClass | None,
    ) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_name = name
        self._attr_device_class = device_class
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Grünbeck spaliQ",
            manufacturer="Grünbeck",
            model="spaliQ Professional",
        )

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.get(self._key)
