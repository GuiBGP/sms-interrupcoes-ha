"""Sensor platform for SMS Interrupções."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
import os

import aiohttp
import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import DiscoveryInfoType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)
import voluptuous as vol

from .const import (
    CONF_NAME,
    CONF_SCAN_INTERVAL,
    CONF_SOURCE,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_URL,
    DOMAIN,
    USER_AGENT,
)
from .parser import extract_locations_full_from_html

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = vol.Schema(
    {
        vol.Required("platform"): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_SOURCE, default=DEFAULT_URL): cv.string,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): cv.positive_int,
    }
)


def _read_local_file(filepath: str) -> str:
    """Read local file synchronously inside executor."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        with open(filepath, "r", encoding="latin-1", errors="ignore") as f:
            return f.read()


async def _create_coordinator(hass: HomeAssistant, source: str, scan_interval: timedelta) -> DataUpdateCoordinator:
    """Initialize the DataUpdateCoordinator."""
    session = async_get_clientsession(hass)

    async def _async_fetch_parse():
        try:
            if source.lower().startswith(("http://", "https://")):
                headers = {"User-Agent": USER_AGENT}
                timeout = aiohttp.ClientTimeout(total=20)
                async with session.get(source, headers=headers, timeout=timeout) as resp:
                    resp.raise_for_status()
                    html_text = await resp.text(encoding="utf-8", errors="ignore")
            else:
                html_text = await hass.async_add_executor_job(_read_local_file, source)

            items = extract_locations_full_from_html(html_text)
            return {
                "count": len(items),
                "items": items,
                "last_updated": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                "source": source,
                "source_type": "url" if source.lower().startswith(("http://", "https://")) else "file",
            }
        except Exception as err:
            raise UpdateFailed(f"Failed fetching or parsing SMS interruptions: {err}") from err

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"{DOMAIN}_{source}",
        update_method=_async_fetch_parse,
        update_interval=scan_interval,
    )
    return coordinator


async def async_setup_platform(
    hass: HomeAssistant,
    config: dict,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up platform from YAML."""
    name = config.get(CONF_NAME, DEFAULT_NAME)
    source = config.get(CONF_SOURCE, DEFAULT_URL)
    raw_interval = config.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    scan_interval = (
        raw_interval if isinstance(raw_interval, timedelta) else timedelta(minutes=int(raw_interval))
    )

    coordinator = await _create_coordinator(hass, source, scan_interval)
    await coordinator.async_config_entry_first_refresh()
    async_add_entities([SmsInterrupcoesSensor(coordinator, name, source)])


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up platform from a ConfigEntry."""
    cfg = {**entry.data, **entry.options}
    name = cfg.get(CONF_NAME, DEFAULT_NAME)
    source = cfg.get(CONF_SOURCE, DEFAULT_URL)

    raw_interval = cfg.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    scan_interval = (
        raw_interval if isinstance(raw_interval, timedelta) else timedelta(minutes=int(raw_interval))
    )

    coordinator = await _create_coordinator(hass, source, scan_interval)
    await coordinator.async_config_entry_first_refresh()
    async_add_entities([SmsInterrupcoesSensor(coordinator, name, entry.entry_id)])


class SmsInterrupcoesSensor(CoordinatorEntity, SensorEntity):
    """Sensor entity for water outages."""

    _attr_icon = "mdi:water-off"

    def __init__(self, coordinator: DataUpdateCoordinator, name: str, source: str) -> None:
        super().__init__(coordinator)
        self._attr_name = name
        # Exactly matches your original unique_id format:
        self._attr_unique_id = f"sms_interrupcoes::{source}"

    @property
    def native_value(self) -> int:
        """Return interruption count."""
        if self.coordinator.data:
            return self.coordinator.data.get("count", 0)
        return 0

    @property
    def extra_state_attributes(self) -> dict:
        """Return interruption metadata."""
        if not self.coordinator.data:
            return {}
        return {
            "items": self.coordinator.data.get("items", []),
            "last_updated": self.coordinator.data.get("last_updated"),
            "source": self.coordinator.data.get("source"),
            "source_type": self.coordinator.data.get("source_type"),
        }
