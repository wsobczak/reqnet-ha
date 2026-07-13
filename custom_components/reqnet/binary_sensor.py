"""Binary sensor entities for reQnet."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass, BinarySensorEntity, BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import DOMAIN
from .entity import ReqnetEntity

@dataclass(frozen=True)
class ReqnetBSDesc(BinarySensorEntityDescription):
    value_fn: Callable[[dict[str, Any]], bool | None] = lambda _: None

SENSORS: tuple[ReqnetBSDesc, ...] = (
    ReqnetBSDesc(
        key="filter_alarm", name="Alarm filtrów",
        device_class=BinarySensorDeviceClass.PROBLEM, icon="mdi:air-filter",
        value_fn=lambda d: bool(d.get("filter_alarm", False)),
    ),
    ReqnetBSDesc(
        key="bypass_open", name="Bypass otwarty",
        device_class=BinarySensorDeviceClass.OPENING, icon="mdi:valve-open",
        value_fn=lambda d: bool(d.get("bypass_open", False)),
    ),
    ReqnetBSDesc(
        key="error_code", name="Błąd urządzenia",
        device_class=BinarySensorDeviceClass.PROBLEM, icon="mdi:alert-circle",
        value_fn=lambda d: int(d.get("error_code", 0)) != 0,
    ),
    ReqnetBSDesc(
        key="mqtt_ok", name="MQTT połączone",
        device_class=BinarySensorDeviceClass.CONNECTIVITY, icon="mdi:cloud-check",
        entity_registry_enabled_default=False,
        value_fn=lambda d: bool(d.get("mqtt_ok", False)),
    ),
)

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    store = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        ReqnetBS(store["handler"], store["api"], entry.entry_id, d) for d in SENSORS
    )

class ReqnetBS(ReqnetEntity, BinarySensorEntity):
    entity_description: ReqnetBSDesc
    def __init__(self, handler, api, entry_id, desc: ReqnetBSDesc) -> None:
        super().__init__(handler, api, entry_id, desc.key)
        self.entity_description = desc
    @property
    def is_on(self) -> bool | None:
        try:
            return self.entity_description.value_fn(self._handler.get_data())
        except Exception:
            return None
