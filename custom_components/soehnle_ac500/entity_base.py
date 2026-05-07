"""Gemeinsame Basisklasse für alle AC500-Entitäten.

Zuständig für:
  - Gerätegruppierung (DeviceInfo wird von allen Entitäten geteilt)
  - Verfügbarkeitslogik: erst nach dem ersten EF02-Frame verfügbar;
    letzter bekannter Zustand bleibt bei BLE-Unterbrechungen erhalten
  - Registrierung und Deregistrierung des Coordinator-Listeners
"""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN
from .coordinator import AC500Coordinator


class AC500EntityBase(Entity):
    """Basisklasse für alle Soehnle AC500-Entitäten."""

    _attr_has_entity_name = True
    _attr_should_poll     = False

    def __init__(self, coordinator: AC500Coordinator,
                 entry: ConfigEntry, suffix: str) -> None:
        self._coordinator = coordinator
        self._entry       = entry

        device_name = entry.data.get(CONF_NAME, "Soehnle AC500")
        address     = entry.data.get(CONF_ADDRESS, "")

        self._attr_unique_id = f"{entry.entry_id}_{suffix}"

        # ── Gerätegruppierung ────────────────────────────────────────────
        # Alle Entitäten teilen diese DeviceInfo → HA gruppiert sie unter einem Gerät
        self._attr_device_info = DeviceInfo(
            identifiers   = {(DOMAIN, entry.entry_id)},
            name          = device_name,
            manufacturer  = "Soehnle",
            model         = "Airfresh Clean Connect 500",
            sw_version    = "Jan 25 2018",
            connections   = {("bluetooth", address)},
        )

    async def async_added_to_hass(self) -> None:
        self._coordinator.async_add_listener(self._handle_update)

    async def async_will_remove_from_hass(self) -> None:
        self._coordinator.async_remove_listener(self._handle_update)

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """
        True sobald der erste gültige EF02-Frame empfangen wurde.
        Bleibt True während BLE-Unterbrechungen, damit der letzte Zustand sichtbar bleibt.
        Nur False bevor überhaupt Daten angekommen sind.
        """
        return self._coordinator.state.ever_seen
