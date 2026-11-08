"""Config flow for RYSE SmartBridge (local)."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from pyryse import RyseBridge, RyseError

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_HOST, CONF_SERIAL, DOMAIN


class RyseConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for RYSE SmartBridge (local)."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            serial = (user_input.get(CONF_SERIAL) or "").strip() or None
            bridge = RyseBridge(
                host, async_get_clientsession(self.hass), serial=serial
            )
            try:
                device = await bridge.async_get_device()
            except RyseError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(device.id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=device.name,
                    data={CONF_HOST: host, CONF_SERIAL: serial},
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Optional(CONF_SERIAL): str,
            }
        )
        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )
