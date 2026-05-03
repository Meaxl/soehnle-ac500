"""Lüfter-Entität – Geschwindigkeit, Voreinstellungen, Ein/Aus."""
from __future__ import annotations

import logging
import math
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, PRESET_MODES, SPEED_MAP
from .coordinator import AC500Coordinator
from .entity_base import AC500EntityBase

_LOGGER = logging.getLogger(__name__)

SPEED_TO_PCT = {0: 25, 1: 50, 2: 75, 3: 100}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                            async_add_entities: AddEntitiesCallback) -> None:
    coordinator: AC500Coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([AC500Fan(coordinator, entry)])


class AC500Fan(AC500EntityBase, FanEntity):
    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.PRESET_MODE
        | FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
    )

    def __init__(self, coordinator: AC500Coordinator,
                 entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "fan")
        self._attr_name = None

    @property
    def is_on(self) -> bool:
        return self._coordinator.state.power

    @property
    def percentage(self) -> int | None:
        if not self._coordinator.state.power:
            return 0
        return SPEED_TO_PCT.get(self._coordinator.state.speed, 25)

    @property
    def speed_count(self) -> int:
        return 4

    @property
    def preset_mode(self) -> str | None:
        if not self._coordinator.state.power:
            return None
        if self._coordinator.state.auto:
            return "auto"
        return SPEED_MAP.get(self._coordinator.state.speed, "speed_1")

    @property
    def preset_modes(self) -> list[str]:
        return PRESET_MODES

    async def async_turn_on(self, percentage: int | None = None,
                            preset_mode: str | None = None,
                            **kwargs: Any) -> None:
        await self._coordinator.client.send_command("power_on")
        if preset_mode:
            await self.async_set_preset_mode(preset_mode)
        elif percentage is not None:
            await self.async_set_percentage(percentage)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._coordinator.client.send_command("power_off")

    async def async_set_percentage(self, percentage: int) -> None:
        if percentage == 0:
            return await self.async_turn_off()
        idx = max(0, min(3, math.ceil(percentage / 25) - 1))
        await self._coordinator.client.send_command(
            ["speed_1", "speed_2", "speed_3", "speed_4"][idx]
        )

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        if preset_mode == "auto":
            await self._coordinator.client.send_command("auto_on")
        elif preset_mode in ("speed_1", "speed_2", "speed_3", "speed_4"):
            await self._coordinator.client.send_command(preset_mode)
