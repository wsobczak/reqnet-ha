"""reQnet Recuperator — local push integration via MQTT."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ReqnetApi
from .const import CONF_HOST, CONF_MQTT_TOPIC, DOMAIN
from .mqtt_handler import ReqnetMqttHandler

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.CLIMATE,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.SELECT,
    Platform.NUMBER,
    Platform.BUTTON,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up reQnet from a config entry."""
    host       = entry.data[CONF_HOST]
    mqtt_topic = entry.data[CONF_MQTT_TOPIC]

    session = async_get_clientsession(hass)
    api     = ReqnetApi(host, session)
    handler = ReqnetMqttHandler(hass, mqtt_topic)

    await handler.async_setup()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "handler": handler,
        "api":     api,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unloaded := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        store = hass.data[DOMAIN].pop(entry.entry_id)
        store["handler"].async_teardown()
    return unloaded
