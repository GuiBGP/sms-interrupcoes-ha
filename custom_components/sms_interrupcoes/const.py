"""Constants for the SMS Interrupções integration."""
from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "sms_interrupcoes"

DEFAULT_NAME = "SMS Interrupções Água"
DEFAULT_URL = "https://sms-setubal.pt/cliente/avisos-interrupcao-fornecimento/"
DEFAULT_SCAN_INTERVAL = 30
DEFAULT_RADIUS = 10000  # 0 means disabled (track all events)
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0 Safari/537.36"
)

CONF_SOURCE = "source"
CONF_NAME = "name"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_RADIUS = "radius"

PLATFORMS: list[Platform] = [Platform.SENSOR]
