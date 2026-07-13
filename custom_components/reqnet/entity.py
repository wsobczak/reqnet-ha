"""Base entity for reQnet — state from MQTT, commands via REST."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN
from .mqtt_handler import ReqnetMqttHandler


class ReqnetEntity(Entity):
    """Base class for all reQnet entities."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        handler: ReqnetMqttHandler,
        api,
        entry_id: str,
        unique_suffix: str,
    ) -> None:
        self._handler = handler
        self._api = api
        self._entry_id = entry_id
        self._attr_unique_id = f"{entry_id}_{unique_suffix}"

    async def async_added_to_hass(self) -> None:
        self._handler.register_update_callback(self._on_mqtt_update)

    async def async_will_remove_from_hass(self) -> None:
        self._handler.unregister_update_callback(self._on_mqtt_update)

    def _on_mqtt_update(self) -> None:
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        return self._handler.available

    @property
    def device_info(self) -> DeviceInfo:
        data = self._handler.get_data()
        mac  = data.get("mac") or self._handler.base_topic
        fw   = data.get("fw_version") or None
        dtype = data.get("device_type")
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry_id)},
            name="reQnet Recuperator",
            manufacturer="reQnet / Inprax",
            model=f"REQNET type {dtype}" if dtype else "REQNET",
            sw_version=fw,
            configuration_url=f"http://{self._api._host}",
            connections={("mac", mac)} if mac else set(),
        )
