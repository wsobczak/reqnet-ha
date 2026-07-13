"""Switch entities for reQnet functional modes."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import ReqnetApi
from .const import DOMAIN
from .entity import ReqnetEntity


@dataclass(frozen=True)
class ReqnetSwDesc(SwitchEntityDescription):
    data_key: str = ""
    on_fn:  Callable[[ReqnetApi], Awaitable[Any]] = lambda _: None
    off_fn: Callable[[ReqnetApi], Awaitable[Any]] = lambda _: None


SWITCHES: tuple[ReqnetSwDesc, ...] = (
    # Airing uses special logic (duration) — on_fn/off_fn overridden in class
    ReqnetSwDesc(key="airing",       name="Wietrzenie",        icon="mdi:weather-windy",   data_key="airing"),
    ReqnetSwDesc(key="cleaning",     name="Oczyszczanie",       icon="mdi:air-purifier",    data_key="cleaning",     on_fn=lambda a: a.set_cleaning(True),     off_fn=lambda a: a.set_cleaning(False)),
    ReqnetSwDesc(key="heating",      name="Grzanie",            icon="mdi:radiator",        data_key="heating",      on_fn=lambda a: a.set_heating(True),      off_fn=lambda a: a.set_heating(False)),
    ReqnetSwDesc(key="cooling",      name="Chłodzenie",         icon="mdi:snowflake",       data_key="cooling",      on_fn=lambda a: a.set_cooling(True),      off_fn=lambda a: a.set_cooling(False)),
    ReqnetSwDesc(key="fast_heating", name="Szybkie grzanie",    icon="mdi:fire",            data_key="fast_heating", on_fn=lambda a: a.set_fast_heating(True), off_fn=lambda a: a.set_fast_heating(False)),
    ReqnetSwDesc(key="fast_cooling", name="Szybkie chłodzenie", icon="mdi:snowflake-alert", data_key="fast_cooling", on_fn=lambda a: a.set_fast_cooling(True), off_fn=lambda a: a.set_fast_cooling(False)),
    ReqnetSwDesc(key="fireplace",    name="Kominek",            icon="mdi:fireplace",       data_key="fireplace",    on_fn=lambda a: a.set_fireplace(True),    off_fn=lambda a: a.set_fireplace(False)),
    ReqnetSwDesc(key="holiday",      name="Urlop",              icon="mdi:beach",           data_key="holiday",      on_fn=lambda a: a.set_holiday(True),      off_fn=lambda a: a.set_holiday(False)),
    ReqnetSwDesc(key="schedule",     name="Harmonogram",        icon="mdi:calendar-clock",  data_key="schedule",     on_fn=lambda a: a.set_schedule(True),     off_fn=lambda a: a.set_schedule(False)),
    ReqnetSwDesc(key="gwc_relay",    name="Nagrzewnica GWC",    icon="mdi:heating-coil",    data_key="gwc_relay",    on_fn=lambda a: a.set_gwc(True),          off_fn=lambda a: a.set_gwc(False)),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    store = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        ReqnetSwitch(store["handler"], store["api"], entry.entry_id, d)
        for d in SWITCHES
    )


class ReqnetSwitch(ReqnetEntity, SwitchEntity):
    entity_description: ReqnetSwDesc

    def __init__(self, handler, api, entry_id: str, desc: ReqnetSwDesc) -> None:
        super().__init__(handler, api, entry_id, desc.key)
        self.entity_description = desc

    @property
    def is_on(self) -> bool | None:
        val = self._handler.get_data().get(self.entity_description.data_key)
        return bool(val) if val is not None else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        if self.entity_description.key == "airing":
            duration = self._handler.get_user_pref("airing_duration", 30)
            # 0 means no time limit
            await self._api.set_airing(True, duration_min=duration if duration else None)
        else:
            await self.entity_description.on_fn(self._api)

    async def async_turn_off(self, **kwargs: Any) -> None:
        if self.entity_description.key == "airing":
            await self._api.set_airing(False)
        else:
            await self.entity_description.off_fn(self._api)
