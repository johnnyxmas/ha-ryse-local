"""Config flow for RYSE SmartBridge (local)."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from . import RyseApiError, RyseClient
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
            session = async_get_clientsession(self.hass)
            client = RyseClient(session, host=host, serial=serial)
            try:
                device = await client.async_get_device()
            except RyseApiError:
                errors["base"] = "cannot_connect"
            else:
                dvc_id = device.get("dvc_id")
                await self.async_set_unique_id(dvc_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=device.get("dvc_name", "RYSE SmartBridge"),
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
