"""Shared base class for all AC500 entities.

Handles:
  - Device grouping (DeviceInfo shared across all entities)
  - Availability logic: unavailable only before first EF02 frame received;
    last-known state is preserved during BLE reconnects
  - Coordinator listener registration / deregistration
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
    """Base for all Soehnle AC500 entities."""

    _attr_has_entity_name = True
    _attr_should_poll     = False

    def __init__(self, coordinator: AC500Coordinator,
                 entry: ConfigEntry, suffix: str) -> None:
        self._coordinator = coordinator
        self._entry       = entry

        device_name = entry.data.get(CONF_NAME, "Soehnle AC500")
        address     = entry.data.get(CONF_ADDRESS, "")

        self._attr_unique_id = f"{entry.entry_id}_{suffix}"

        # ── Device grouping ──────────────────────────────────────────────
        # All entities share this DeviceInfo → HA groups them under one device
        self._attr_device_info = DeviceInfo(
            identifiers   = {(DOMAIN, entry.entry_id)},
            name          = device_name,
            manufacturer  = "Soehnle",
            model         = "Airfresh Clean Connect 500",
            sw_version    = "0.0.3",
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
        True once the first valid EF02 frame has been received.
        Stays True during BLE reconnects so last-known state remains visible.
        Only False before any data has ever arrived.
        """
        return self._coordinator.state.ever_seen
