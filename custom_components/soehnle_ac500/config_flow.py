"""Config Flow – UI-basierte Einrichtung der Integration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_ADDRESS, CONF_NAME
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN

def _normalize_address(address: str) -> str:
    """MAC-Adresse für Matching konsistent normalisieren."""
    return address.strip().upper()

class SoehnleAC500ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            normalized_address = _normalize_address(user_input[CONF_ADDRESS])

            await self.async_set_unique_id(normalized_address)
            self._abort_if_unique_id_configured()

            entry_data = dict(user_input)
            entry_data[CONF_ADDRESS] = normalized_address

            return self.async_create_entry(
                title=user_input.get(CONF_NAME, "Soehnle AC500"),
                data=entry_data,
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_ADDRESS,
                             default="00:00:00:00:00:00"): str,
                vol.Optional(CONF_NAME,
                             default="Soehnle Airfresh AC500"): str,
            }),
        )
