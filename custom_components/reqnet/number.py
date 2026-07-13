"""Number entities for reQnet — fan presets and airing duration."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import ReqnetEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    store = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        ReqnetFanPreset(store["handler"], store["api"], entry.entry_id, "supply"),
        ReqnetFanPreset(store["handler"], store["api"], entry.entry_id, "extract"),
        ReqnetAiringDuration(store["handler"], store["api"], entry.entry_id),
    ])


class ReqnetFanPreset(ReqnetEntity, NumberEntity):
    """Slider for manual fan speed preset (used when HVAC mode = FAN_ONLY)."""

    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 5
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_mode = NumberMode.SLIDER
    _attr_icon = "mdi:fan"

    def __init__(self, handler, api, entry_id: str, side: str) -> None:
        super().__init__(handler, api, entry_id, f"fan_{side}_preset")
        self._side = side
        self._attr_name = (
            "Preset ręczny — nawiew" if side == "supply" else "Preset ręczny — wywiew"
        )

    @property
    def native_value(self) -> float | None:
        key = "fan_manual_supply" if self._side == "supply" else "fan_manual_extract"
        v = self._handler.get_data().get(key)
        return float(v) if v is not None else None

    async def async_set_native_value(self, value: float) -> None:
        s = int(value)
        if self._side == "supply":
            await self._api.set_manual_mode(fan_supply=s)
        else:
            await self._api.set_manual_mode(fan_extract=s)


class ReqnetAiringDuration(ReqnetEntity, NumberEntity):
    """How many minutes to run airing mode. 0 = no time limit."""

    _attr_name = "Czas wietrzenia"
    _attr_icon = "mdi:timer-outline"
    _attr_native_min_value = 0
    _attr_native_max_value = 99
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "min"
    _attr_mode = NumberMode.BOX

    def __init__(self, handler, api, entry_id: str) -> None:
        super().__init__(handler, api, entry_id, "airing_duration")

    # Always available — value stored locally
    @property
    def available(self) -> bool:
        return True

    @property
    def native_value(self) -> float:
        return float(self._handler.get_user_pref("airing_duration", 30))

    async def async_set_native_value(self, value: float) -> None:
        self._handler.set_user_pref("airing_duration", int(value))
        self.async_write_ha_state()
