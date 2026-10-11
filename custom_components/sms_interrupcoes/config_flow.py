"""Config flow for SMS Interrupções."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_NAME,
    CONF_RADIUS,
    CONF_SCAN_INTERVAL,
    CONF_SOURCE,
    DEFAULT_NAME,
    DEFAULT_RADIUS,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_URL,
    DOMAIN,
)


class SMSConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SMS Interrupções."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return OptionsFlowHandler()

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            name = user_input.get(CONF_NAME, DEFAULT_NAME).strip() or DEFAULT_NAME
            source = user_input.get(CONF_SOURCE, DEFAULT_URL).strip() or DEFAULT_URL
            minutes = int(user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))
            radius = int(user_input.get(CONF_RADIUS, DEFAULT_RADIUS))

            await self.async_set_unique_id(source)
            self._abort_if_unique_id_configured()

            data = {
                CONF_NAME: name,
                CONF_SOURCE: source,
                CONF_SCAN_INTERVAL: minutes,
                CONF_RADIUS: radius,
            }
            return self.async_create_entry(title=name, data=data)

        data_schema = vol.Schema({
            vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
            vol.Optional(CONF_SOURCE, default=DEFAULT_URL): str,
            vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
                int, vol.Range(min=1, max=1440)
            ),
            vol.Optional(CONF_RADIUS, default=DEFAULT_RADIUS): vol.All(
                int, vol.Range(min=0, max=50000)
            ),
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "hint": "Defina o raio em metros (0 para monitorizar todos os eventos no concelho de Setúbal)."
            },
        )


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for an existing entry."""

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        if user_input is not None:
            name = user_input.get(CONF_NAME, self.config_entry.data.get(CONF_NAME, DEFAULT_NAME))
            source = user_input.get(CONF_SOURCE, self.config_entry.data.get(CONF_SOURCE, DEFAULT_URL))
            minutes = int(user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))
            radius = int(user_input.get(CONF_RADIUS, DEFAULT_RADIUS))

            options = {
                CONF_NAME: name,
                CONF_SOURCE: source,
                CONF_SCAN_INTERVAL: minutes,
                CONF_RADIUS: radius,
            }
            return self.async_create_entry(title="", data=options)

        current = {**self.config_entry.data, **self.config_entry.options}
        current_name = current.get(CONF_NAME, DEFAULT_NAME)
        current_minutes = int(current.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))
        current_radius = int(current.get(CONF_RADIUS, DEFAULT_RADIUS))

        data_schema = vol.Schema({
            vol.Optional(CONF_NAME, default=current_name): str,
            vol.Optional(CONF_SOURCE, default=current.get(CONF_SOURCE, DEFAULT_URL)): str,
            vol.Optional(CONF_SCAN_INTERVAL, default=current_minutes): vol.All(
                int, vol.Range(min=1, max=1440)
            ),
            vol.Optional(CONF_RADIUS, default=current_radius): vol.All(
                int, vol.Range(min=0, max=50000)
            ),
        })

        return self.async_show_form(step_id="init", data_schema=data_schema)
