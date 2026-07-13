"""Button entities for reQnet — diagnostics and maintenance."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import ReqnetApi
from .const import DOMAIN
from .entity import ReqnetEntity


@dataclass(frozen=True)
class ReqnetButtonDesc(ButtonEntityDescription):
    press_fn: Callable[[ReqnetApi, HomeAssistant, ConfigEntry], Awaitable[Any]] = (
        lambda a, h, e: None
    )


async def _reconfigure_mqtt(
    api: ReqnetApi, hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Re-send ChangeAdditionalBrokerConfiguration with current HA MQTT credentials."""
    broker, port, user, password = "", 1883, "", ""
    for e in hass.config_entries.async_entries("mqtt"):
        broker   = e.data.get("broker", "")
        port     = int(e.data.get("port", 1883))
        user     = e.data.get("username", "")
        password = e.data.get("password", "")
        break
    if not broker or broker in ("localhost", "127.0.0.1", "::1"):
        try:
            broker = hass.config.api.host  # type: ignore[union-attr]
        except Exception:
            pass
    await api.configure_mqtt_broker(broker, port, user, password)


BUTTONS: tuple[ReqnetButtonDesc, ...] = (
    ReqnetButtonDesc(
        key="reconfigure_mqtt",
        name="Skonfiguruj broker MQTT",
        icon="mdi:mqtt",
        press_fn=_reconfigure_mqtt,
    ),
    ReqnetButtonDesc(
        key="replace_filters",
        name="Resetuj licznik filtrów",
        icon="mdi:air-filter",
        press_fn=lambda a, h, e: a.replace_filters(),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    store = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        ReqnetButton(store["handler"], store["api"], entry, hass, desc)
        for desc in BUTTONS
    )


class ReqnetButton(ReqnetEntity, ButtonEntity):
    entity_description: ReqnetButtonDesc

    def __init__(self, handler, api, entry: ConfigEntry, hass: HomeAssistant, desc: ReqnetButtonDesc) -> None:
        super().__init__(handler, api, entry.entry_id, desc.key)
        self._entry = entry
        self._hass = hass
        self.entity_description = desc

    # Buttons always available — connect independently of device state
    @property
    def available(self) -> bool:
        return True

    async def async_press(self) -> None:
        await self.entity_description.press_fn(self._api, self._hass, self._entry)
