"""Schalter-Entitäten – UV-C, Nachtmodus."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import AC500Coordinator
from .entity_base import AC500EntityBase

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                            async_add_entities: AddEntitiesCallback) -> None:
    coordinator: AC500Coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        AC500Switch(coordinator, entry,
                    "UV-C",       "uvc",   "uvc_on",   "uvc_off"),
        AC500NightModeSwitch(coordinator, entry),
    ])


class AC500Switch(AC500EntityBase, SwitchEntity):
    def __init__(self, coordinator: AC500Coordinator, entry: ConfigEntry,
                 feature: str, state_attr: str,
                 cmd_on: str, cmd_off: str) -> None:
        super().__init__(coordinator, entry, state_attr)
        self._state_attr = state_attr
        self._cmd_on     = cmd_on
        self._cmd_off    = cmd_off
        self._attr_name  = feature

    @property
    def is_on(self) -> bool:
        return bool(getattr(self._coordinator.state, self._state_attr, False))

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._coordinator.client.send_command(self._cmd_on)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._coordinator.client.send_command(self._cmd_off)


class AC500NightModeSwitch(AC500EntityBase, SwitchEntity):
    """
    Nachtmodus-Schalter mit BLE-Disconnect-Logik:
    Beim Einschalten wird die BLE-Verbindung nach dem Befehl getrennt,
    damit das Gerät nicht sofort wieder aus dem Nachtmodus geweckt wird.
    Beim Ausschalten wird der Reconnect wieder freigegeben – der Verbindungsaufbau
    selbst weckt das Gerät aus dem Nachtmodus (Geräteverhalten).
    """

    def __init__(self, coordinator: AC500Coordinator,
                 entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "night")
        self._attr_name = "Night Mode"

    @property
    def is_on(self) -> bool:
        return bool(self._coordinator.state.night)

    async def async_turn_on(self, **kwargs: Any) -> None:
        success = await self._coordinator.client.send_command("night_on")
        if success:
            await asyncio.sleep(1.0)
            await self._coordinator.pause_for_night_mode()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        # Wenn bereits verbunden, Nachtmodus aktiv beenden.
        # (z. B. nach physischer Aktivierung oder HA-Neustart)
        if self._coordinator.client.is_connected:
            await self._coordinator.client.send_command("night_off")

        # Reconnect freigeben – der Verbindungsaufbau weckt Gerät automatisch,
        # falls aktuell keine BLE-Verbindung besteht.
        self._coordinator.resume_from_night_mode()
        self.async_write_ha_state()
