"""Auswahl-Entität – Timer (aus / 2h / 4h / 8h)."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import AC500Coordinator
from .entity_base import AC500EntityBase

TIMER_OPTIONS  = ["off", "2h", "4h", "8h"]
TIMER_TO_CMD   = {"off": "timer_off", "2h": "timer_2h", "4h": "timer_4h", "8h": "timer_8h"}
VAL_TO_OPTION  = {0: "off", 2: "2h", 4: "4h", 8: "8h"}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                            async_add_entities: AddEntitiesCallback) -> None:
    coordinator: AC500Coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([AC500TimerSelect(coordinator, entry)])


class AC500TimerSelect(AC500EntityBase, SelectEntity):
    _attr_options = TIMER_OPTIONS
    _attr_icon    = "mdi:timer-outline"

    def __init__(self, coordinator: AC500Coordinator,
                 entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "timer")
        self._attr_name  = "Timer"

    @property
    def current_option(self) -> str:
        return VAL_TO_OPTION.get(self._coordinator.state.timer_hours, "off")

    async def async_select_option(self, option: str) -> None:
        cmd = TIMER_TO_CMD.get(option)
        if cmd:
            await self._coordinator.client.send_command(cmd)
