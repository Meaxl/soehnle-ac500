"""Binary sensor – BLE connection status."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import AC500Coordinator
from .entity_base import AC500EntityBase


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                            async_add_entities: AddEntitiesCallback) -> None:
    coordinator: AC500Coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([AC500ConnectivitySensor(coordinator, entry)])


class AC500ConnectivitySensor(AC500EntityBase, BinarySensorEntity):
    """Shows live BLE connection status. Always available (shows 'off' when disconnected)."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator: AC500Coordinator,
                 entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "connectivity")
        device_name     = entry.data.get(CONF_NAME, "Soehnle AC500")
        self._attr_name = f"{device_name} Connection"

    @property
    def available(self) -> bool:
        # Always available so the disconnected state is visible in HA
        return True

    @property
    def is_on(self) -> bool:
        return self._coordinator.state.connected
