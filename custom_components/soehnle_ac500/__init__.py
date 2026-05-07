"""Soehnle Airfresh Clean Connect 500 – Home Assistant Integration (Setup & Koordination)."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, CONF_NAME, Platform
from homeassistant.core import HomeAssistant

from .ble_client import AC500BleClient
from .const import DOMAIN
from .coordinator import AC500Coordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.FAN,
    Platform.SWITCH,
    Platform.SENSOR,
    Platform.SELECT,
    Platform.BINARY_SENSOR,
]

def _normalize_address(address: str) -> str:
    return address.strip().upper()

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    normalized_address = _normalize_address(entry.data[CONF_ADDRESS])
    client      = AC500BleClient(normalized_address)
    coordinator = AC500Coordinator(
        hass, client, entry.data.get(CONF_NAME, "AC500")
    )

    # Migration bestehender Entries: data + unique_id konsistent halten
    if normalized_address != entry.data[CONF_ADDRESS] or entry.unique_id != normalized_address:
        new_data = dict(entry.data)
        new_data[CONF_ADDRESS] = normalized_address
        hass.config_entries.async_update_entry(
            entry,
            data=new_data,
            unique_id=normalized_address,
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
