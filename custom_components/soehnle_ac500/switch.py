"""Switch entities – UV-C, Night Mode."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import AC500Coordinator
from .entity_base import AC500EntityBase

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                            async_add_entities: AddEntitiesCallback) -> None:
    coordinator: AC500Coordinator = hass.data[DOMAIN][entry.entry_id]
    device_name = entry.data.get(CONF_NAME, "Soehnle AC500")
    async_add_entities([
        AC500Switch(coordinator, entry, device_name,
                    "UV-C",       "uvc",   "uvc_on",   "uvc_off"),
        AC500Switch(coordinator, entry, device_name,
                    "Night Mode", "night", "night_on", "night_off"),
    ])


class AC500Switch(AC500EntityBase, SwitchEntity):
    def __init__(self, coordinator: AC500Coordinator, entry: ConfigEntry,
                 device_name: str, feature: str, state_attr: str,
                 cmd_on: str, cmd_off: str) -> None:
        super().__init__(coordinator, entry, state_attr)
        self._state_attr = state_attr
        self._cmd_on     = cmd_on
        self._cmd_off    = cmd_off
        self._attr_name  = f"{device_name} {feature}"

    @property
    def is_on(self) -> bool:
        return bool(getattr(self._coordinator.state, self._state_attr, False))

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._coordinator.client.send_command(self._cmd_on)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._coordinator.client.send_command(self._cmd_off)
