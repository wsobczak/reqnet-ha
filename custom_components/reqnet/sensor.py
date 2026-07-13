"""Sensor entities for reQnet recuperator."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONCENTRATION_PARTS_PER_MILLION,
    PERCENTAGE,
    REVOLUTIONS_PER_MINUTE,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, WORK_MODE_MAP
from .entity import ReqnetEntity


@dataclass(frozen=True)
class ReqnetSensorDesc(SensorEntityDescription):
    value_fn: Callable[[dict[str, Any]], Any] = lambda _: None


def _t(key: str) -> Callable:
    """Float temperature from data dict."""
    return lambda d: round(float(d[key]), 1) if d.get(key) is not None else None


def _i(key: str) -> Callable:
    """Integer from data dict."""
    return lambda d: int(d[key]) if d.get(key) is not None else None


def _fan_pct(d: dict[str, Any]) -> float | None:
    """Compute fan speed % from measured airflow vs system max."""
    try:
        supply  = float(d.get("airflow_supply") or 0)
        extract = float(d.get("airflow_extract") or 0)
        max_flow = float(d.get("max_airflow") or 500)
        if max_flow <= 0:
            return None
        return round(min(100.0, (supply + extract) / 2 / max_flow * 100), 0)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _heat_recovery(d: dict[str, Any]) -> float | None:
    """(T_supply - T_intake) / (T_extract - T_intake) × 100."""
    try:
        ts = float(d["temp_supply"])
        te = float(d["temp_extract"])
        ti = float(d["temp_intake"])
        delta = te - ti
        if abs(delta) < 0.5:
            return None
        return round(max(0.0, min(100.0, (ts - ti) / delta * 100)), 1)
    except (TypeError, ValueError, KeyError, ZeroDivisionError):
        return None


def _wifi_dbm(d: dict[str, Any]) -> int | None:
    """Parse dBm from string like 'excellent (-57 dBm)'."""
    import re
    desc = d.get("wifi_desc", "")
    m = re.search(r"\((-?\d+)\s*dBm\)", str(desc))
    return int(m.group(1)) if m else None


SENSORS: tuple[ReqnetSensorDesc, ...] = (
    # ── Temperatures ──────────────────────────────────────────────
    ReqnetSensorDesc(
        key="temp_supply", name="Temperatura nawiewu",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        icon="mdi:thermometer-chevron-up",
        value_fn=_t("temp_supply"),
    ),
    ReqnetSensorDesc(
        key="temp_extract", name="Temperatura wywiewu",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        icon="mdi:thermometer-chevron-down",
        value_fn=_t("temp_extract"),
    ),
    ReqnetSensorDesc(
        key="temp_intake", name="Temperatura zewnętrzna",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        icon="mdi:thermometer",
        value_fn=_t("temp_intake"),
    ),
    ReqnetSensorDesc(
        key="temp_exhaust", name="Temperatura wyrzutu",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        icon="mdi:thermometer-off",
        value_fn=_t("temp_exhaust"),
    ),
    ReqnetSensorDesc(
        key="temp_heater", name="Temperatura nagrzewnicy",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        icon="mdi:heating-coil",
        entity_registry_enabled_default=False,
        value_fn=_t("temp_heater"),
    ),
    ReqnetSensorDesc(
        key="temp_gwc", name="Temperatura GWC",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        icon="mdi:pipe",
        entity_registry_enabled_default=False,
        value_fn=_t("temp_gwc"),
    ),
    ReqnetSensorDesc(
        key="comfort_temp", name="Temperatura komfortu",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        icon="mdi:home-thermometer-outline",
        value_fn=_t("comfort_temp"),
    ),
    # ── Air quality ───────────────────────────────────────────────
    ReqnetSensorDesc(
        key="humidity", name="Wilgotność",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:water-percent",
        value_fn=_i("humidity"),
    ),
    ReqnetSensorDesc(
        key="co2", name="Stężenie CO₂",
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        device_class=SensorDeviceClass.CO2,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:molecule-co2",
        value_fn=_i("co2"),
    ),
    # ── Airflow & fan ─────────────────────────────────────────────
    ReqnetSensorDesc(
        key="airflow_supply", name="Przepływ nawiewu",
        native_unit_of_measurement="m³/h",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:air-filter",
        value_fn=_i("airflow_supply"),
    ),
    ReqnetSensorDesc(
        key="airflow_extract", name="Przepływ wywiewu",
        native_unit_of_measurement="m³/h",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:air-filter",
        value_fn=_i("airflow_extract"),
    ),
    ReqnetSensorDesc(
        key="fan_pct", name="Wentylator",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:fan",
        suggested_display_precision=0,
        value_fn=_fan_pct,
    ),
    ReqnetSensorDesc(
        key="fan_supply_rpm", name="Wentylator nawiewny — obroty",
        native_unit_of_measurement=REVOLUTIONS_PER_MINUTE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:fan-speed-1",
        entity_registry_enabled_default=False,
        value_fn=_i("fan_supply_rpm"),
    ),
    ReqnetSensorDesc(
        key="fan_extract_rpm", name="Wentylator wywiewny — obroty",
        native_unit_of_measurement=REVOLUTIONS_PER_MINUTE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:fan-speed-1",
        entity_registry_enabled_default=False,
        value_fn=_i("fan_extract_rpm"),
    ),
    # ── Calculated ────────────────────────────────────────────────
    ReqnetSensorDesc(
        key="heat_recovery", name="Sprawność odzysku ciepła",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:recycle",
        suggested_display_precision=0,
        value_fn=_heat_recovery,
    ),
    # ── Status ────────────────────────────────────────────────────
    ReqnetSensorDesc(
        key="filter_days", name="Dni do wymiany filtrów",
        native_unit_of_measurement="d",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:air-filter",
        value_fn=_i("filter_days"),
    ),
    ReqnetSensorDesc(
        key="work_mode", name="Tryb pracy",
        icon="mdi:hvac",
        value_fn=lambda d: WORK_MODE_MAP.get(int(d.get("work_mode", 9)), "unknown"),
    ),
    ReqnetSensorDesc(
        key="wifi_signal", name="Sygnał WiFi",
        native_unit_of_measurement="dBm",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=_wifi_dbm,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    store = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        ReqnetSensor(store["handler"], store["api"], entry.entry_id, desc)
        for desc in SENSORS
    )


class ReqnetSensor(ReqnetEntity, SensorEntity):
    entity_description: ReqnetSensorDesc

    def __init__(self, handler, api, entry_id, desc: ReqnetSensorDesc) -> None:
        super().__init__(handler, api, entry_id, desc.key)
        self.entity_description = desc

    @property
    def native_value(self) -> Any:
        try:
            return self.entity_description.value_fn(self._handler.get_data())
        except Exception:
            return None
