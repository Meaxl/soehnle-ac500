"""Binärsensor – BLE-Verbindungsstatus."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
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
    """Zeigt den aktuellen BLE-Verbindungsstatus. Immer verfügbar (zeigt 'off' bei Trennung)."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: AC500Coordinator,
                 entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "connectivity")
        self._attr_name = "Connection"

    @property
    def available(self) -> bool:
        # Immer verfügbar, damit der Getrennt-Zustand in HA sichtbar bleibt
        return True

    @property
    def is_on(self) -> bool:
        return self._coordinator.state.connected
