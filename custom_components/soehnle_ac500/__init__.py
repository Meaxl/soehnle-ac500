"""Soehnle Airfresh Clean Connect 500 – Home Assistant Integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform, CONF_ADDRESS, CONF_NAME
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .ble_client import AC500BleClient
from .coordinator import AC500Coordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.FAN,
    Platform.SWITCH,
    Platform.SENSOR,
    Platform.SELECT,
    Platform.BINARY_SENSOR,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    client      = AC500BleClient(entry.data[CONF_ADDRESS])
    coordinator = AC500Coordinator(
        hass, client, entry.data.get(CONF_NAME, "AC500")
    )
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await coordinator.async_start()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator: AC500Coordinator = hass.data[DOMAIN][entry.entry_id]
    await coordinator.async_stop()
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
