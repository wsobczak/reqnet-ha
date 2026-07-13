"""Climate entity — main control for reQnet recuperator."""
from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import BYPASS_INT_TO_STR, DOMAIN, MODE_MANUAL, MODE_STANDBY, WORK_MODE_MAP
from .entity import ReqnetEntity

# Map reQnet mode strings → HA HVAC modes
_REQNET_TO_HVAC = {
    MODE_STANDBY: HVACMode.OFF,
    MODE_MANUAL:  HVACMode.FAN_ONLY,
    # Everything else → AUTO
}
_FAN_MODES = [str(v) for v in range(10, 101, 10)]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    store = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ReqnetClimate(store["handler"], store["api"], entry.entry_id)])


class ReqnetClimate(ReqnetEntity, ClimateEntity):
    """Main climate card for the recuperator."""

    _attr_name = None  # uses device name
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = 0.5
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.FAN_ONLY, HVACMode.AUTO]
    _attr_fan_modes = _FAN_MODES
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )

    def __init__(self, handler, api, entry_id: str) -> None:
        super().__init__(handler, api, entry_id, "climate")

    # ── State ──────────────────────────────────────────────────────

    @property
    def min_temp(self) -> float:
        return float(self._handler.get_data().get("min_comfort_temp") or 15.0)

    @property
    def max_temp(self) -> float:
        return float(self._handler.get_data().get("max_comfort_temp") or 30.0)

    @property
    def hvac_mode(self) -> HVACMode:
        d = self._handler.get_data()
        if not d.get("is_on", True):
            return HVACMode.OFF
        mode_str = WORK_MODE_MAP.get(int(d.get("work_mode", 9)), "auto")
        return _REQNET_TO_HVAC.get(mode_str, HVACMode.AUTO)

    @property
    def current_temperature(self) -> float | None:
        v = self._handler.get_data().get("temp_supply")
        return float(v) if v is not None else None

    @property
    def target_temperature(self) -> float | None:
        v = self._handler.get_data().get("comfort_temp")
        return float(v) if v is not None else None

    @property
    def fan_mode(self) -> str | None:
        """Report manual fan preset as fan_mode."""
        d = self._handler.get_data()
        v = d.get("fan_manual_supply")
        if v is not None:
            return str(max(10, min(100, round(int(v) / 10) * 10)))
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        d = self._handler.get_data()
        return {
            "bypass_open":      d.get("bypass_open"),
            "bypass_mode":      d.get("bypass_mode"),
            "airflow_supply":   d.get("airflow_supply"),
            "airflow_extract":  d.get("airflow_extract"),
            "fan_supply_rpm":   d.get("fan_supply_rpm"),
            "fan_extract_rpm":  d.get("fan_extract_rpm"),
            "humidity":         d.get("humidity"),
            "co2":              d.get("co2"),
            "temp_intake":      d.get("temp_intake"),
            "temp_exhaust":     d.get("temp_exhaust"),
            "fw_version":       d.get("fw_version"),
            "device_time":      d.get("device_time"),
        }

    # ── Commands ───────────────────────────────────────────────────

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode == HVACMode.OFF:
            await self._api.turn_off()
        elif hvac_mode == HVACMode.FAN_ONLY:
            await self._api.turn_on()
            await self._api.set_manual_mode()
        else:
            await self._api.turn_on()
            await self._api.set_automatic_mode()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        if temp := kwargs.get(ATTR_TEMPERATURE):
            await self._api.set_comfort_temperature(float(temp))

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        speed = int(fan_mode)
        await self._api.set_manual_mode(fan_supply=speed, fan_extract=speed)

    async def async_turn_on(self) -> None:
        await self._api.turn_on()

    async def async_turn_off(self) -> None:
        await self._api.turn_off()
