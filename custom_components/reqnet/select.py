"""Select entity for bypass mode."""
from __future__ import annotations
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import BYPASS_INT_TO_STR, BYPASS_MODES, DOMAIN
from .entity import ReqnetEntity

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    store = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ReqnetBypass(store["handler"], store["api"], entry.entry_id)])

class ReqnetBypass(ReqnetEntity, SelectEntity):
    _attr_name = "Tryb bypass"
    _attr_icon = "mdi:valve"
    _attr_options = BYPASS_MODES
    def __init__(self, handler, api, entry_id) -> None:
        super().__init__(handler, api, entry_id, "bypass_mode")
    @property
    def current_option(self) -> str | None:
        return self._handler.get_data().get("bypass_mode", "auto")
    async def async_select_option(self, option: str) -> None:
        await self._api.set_bypass_mode(option)
