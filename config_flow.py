
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    DOMAIN, DEFAULT_NAME, DEFAULT_URL, DEFAULT_SCAN_INTERVAL,
    CONF_SOURCE, CONF_NAME, CONF_SCAN_INTERVAL
)

# Helper: convert minutes (int) to a string time period Home Assistant can store easily
def _minutes_to_td(minutes: int):
    from datetime import timedelta
    return timedelta(minutes=minutes)

class SMSConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SMS Interrupções."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            name = user_input.get(CONF_NAME, DEFAULT_NAME).strip() or DEFAULT_NAME
            source = user_input.get(CONF_SOURCE, DEFAULT_URL).strip() or DEFAULT_URL
            minutes = user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

            # Avoid duplicate entries (same source)
            unique_id = f"{source}"
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            data = {
                CONF_NAME: name,
                CONF_SOURCE: source,
                CONF_SCAN_INTERVAL: _minutes_to_td(int(minutes)),
            }
            return self.async_create_entry(title=name, data=data)

        #Gui's Note: DATA_SCHEMA is WHAT will appear on the Form
        data_schema = vol.Schema({
            vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
            vol.Optional(CONF_SOURCE, default=DEFAULT_URL): str,  # URL or local file path
            vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(int, vol.Range(min=1, max=1440)),
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "hint": "Provide either the live URL or a local HTML file path containing the `locations` variable."
            }
        )

class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for an existing entry."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        if user_input is not None:
            name = user_input.get(CONF_NAME, self.config_entry.data.get(CONF_NAME))
            source = user_input.get(CONF_SOURCE, self.config_entry.data.get(CONF_SOURCE))
            minutes = user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

            options = {
                CONF_NAME: name,
                CONF_SOURCE: source,
                CONF_SCAN_INTERVAL: _minutes_to_td(int(minutes)),
            }
            return self.async_create_entry(title="", data=options)

        # Prefill with current values (options override data)
        current = {**self.config_entry.data, **self.config_entry.options}
        minutes_default = int((current.get(CONF_SCAN_INTERVAL) or _minutes_to_td(10)).total_seconds() // 60)

        data_schema = vol.Schema({
            vol.Optional(CONF_NAME, default=current.get(CONF_NAME, DEFAULT_NAME)): str,
            vol.Optional(CONF_SOURCE, default=current.get(CONF_SOURCE, DEFAULT_URL)): str,
            vol.Optional(CONF_SCAN_INTERVAL, default=minutes_default): vol.All(int, vol.Range(min=1, max=1440)),
        })

        return self.async_show_form(step_id="init", data_schema=data_schema)
