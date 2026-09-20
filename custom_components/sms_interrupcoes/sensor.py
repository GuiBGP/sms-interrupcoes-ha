
import logging
import os
from datetime import timedelta, datetime

import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from homeassistant.core import HomeAssistant
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
    CoordinatorEntity,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.config_entries import ConfigEntry

from .const import (
    DOMAIN, DEFAULT_NAME, DEFAULT_URL, USER_AGENT,
    CONF_SOURCE, CONF_NAME, CONF_SCAN_INTERVAL
)
from .parser import extract_locations_full_from_html

_LOGGER = logging.getLogger(__name__)

# ---- YAML support (optional) ----
PLATFORM_SCHEMA = vol.Schema(
    {
        vol.Required("platform"): cv.string,  # "sms_interrupcoes"
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_SOURCE, default=DEFAULT_URL): cv.string,
        vol.Optional(CONF_SCAN_INTERVAL, default=timedelta(minutes=10)): cv.time_period,
    }
)

async def async_setup_platform(hass: HomeAssistant, config, async_add_entities, discovery_info=None):
    """YAML-based setup (optional)."""
    name = config.get(CONF_NAME, DEFAULT_NAME)
    source = config.get(CONF_SOURCE, DEFAULT_URL)
    scan_interval = config.get(CONF_SCAN_INTERVAL, timedelta(minutes=10))
    coordinator = await _create_coordinator(hass, source, scan_interval)
    await coordinator.async_config_entry_first_refresh()
    async_add_entities([SmsInterrupcoesSensor(coordinator, name)])

# ---- Config Entry setup ----
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """UI-based setup via config entries."""
    # Options override data
    cfg = {**entry.data, **entry.options}
    name = cfg.get(CONF_NAME, DEFAULT_NAME)
    source = cfg.get(CONF_SOURCE, DEFAULT_URL)
    scan_interval = cfg.get(CONF_SCAN_INTERVAL, timedelta(minutes=10))
    coordinator = await _create_coordinator(hass, source, scan_interval)
    await coordinator.async_config_entry_first_refresh()
    async_add_entities([SmsInterrupcoesSensor(coordinator, name)])

async def _create_coordinator(hass: HomeAssistant, source: str, scan_interval: timedelta):
    session = async_get_clientsession(hass)

    async def _async_fetch_parse():
        try:
            if source.lower().startswith(("http://", "https://")):
                headers = {"User-Agent": USER_AGENT}
                async with session.get(source, headers=headers, timeout=20) as resp:
                    html_text = await resp.text(encoding="utf-8", errors="ignore")
            else:
                if not os.path.exists(source):
                    raise FileNotFoundError(f"File not found: {source}")
                try:
                    with open(source, "r", encoding="utf-8") as f:
                        html_text = f.read()
                except UnicodeDecodeError:
                    with open(source, "r", encoding="latin-1", errors="ignore") as f:
                        html_text = f.read()

            items = extract_locations_full_from_html(html_text)
            data = {
                "count": len(items),
                "items": items,
                "last_updated": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
                "source": source,
                "source_type": "url" if source.lower().startswith(("http://", "https://")) else "file",
            }
            return data

        except Exception as err:
            raise UpdateFailed(f"fetch/parse failed: {err}") from err

    return DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"{DOMAIN}_coordinator::{source}",
        update_method=_async_fetch_parse,
        update_interval=scan_interval,
    )

class SmsInterrupcoesSensor(CoordinatorEntity, SensorEntity):
    """Sensor entity showing the count of interruptions; details in attributes."""
    _attr_icon = "mdi:water-off"
    _attr_should_poll = False

    def __init__(self, coordinator: DataUpdateCoordinator, name: str):
        super().__init__(coordinator)
        self._attr_name = name
        src = coordinator.name.split("::", 1)[-1]
        self._attr_unique_id = f"sms_interrupcoes::{src}"

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    @property
    def native_value(self):
        data = self.coordinator.data or {}
        return data.get("count", 0)

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data or {}
        return {
            "items": data.get("items", []),
            "last_updated": data.get("last_updated"),
            "source": data.get("source"),
            "source_type": data.get("source_type"),
        }
