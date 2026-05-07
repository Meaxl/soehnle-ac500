"""Gemeinsame Basisklasse für alle AC500-Entitäten.

Zuständig für:
  - Gerätegruppierung (DeviceInfo wird von allen Entitäten geteilt)
  - Verfügbarkeitslogik: erst nach dem ersten EF02-Frame verfügbar;
    letzter bekannter Zustand bleibt bei BLE-Unterbrechungen erhalten
  - Listener-Registrierung via CoordinatorEntity
"""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, CONF_NAME
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AC500Coordinator


class AC500EntityBase(CoordinatorEntity[AC500Coordinator]):
    """Basisklasse für alle Soehnle AC500-Entitäten."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: AC500Coordinator,
                 entry: ConfigEntry, suffix: str) -> None:
        super().__init__(coordinator)
        # Alias für alle Subklassen die self._coordinator verwenden
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

    @property
    def available(self) -> bool:
        """
        True sobald der erste gültige EF02-Frame empfangen wurde und kein Stale-Timeout abgelaufen ist.
        Während Nachtmodus-Pause bleibt der letzte Wert erhalten (kein Stale).
        """
        return self._coordinator.state.ever_seen and not self._coordinator.is_stale
