"""MQTT state handler for reQnet recuperators.

The device publishes JSON payloads to sub-topics under its MAC address:
  {MAC}/CurrentWorkParametersResult  — main operating data (Values[] array)
  {MAC}/CurrentTemperaturesResult    — temperatures + humidity + CO2
  {MAC}/APIResult                    — firmware version, WiFi, MQTT status
  {MAC}/StatusDeviceResult           — basic device info
  {MAC}/GetWorkParametersResult      — advanced config
  {MAC}/GetDateTimeResult            — device clock
"""
from __future__ import annotations

import json
import logging
from typing import Any, Callable

from homeassistant.components import mqtt
from homeassistant.core import HomeAssistant, callback

from .const import (
    API_DEVICE_TYPE, API_ERROR_CODE, API_FW_VERSION,
    API_MAC, API_MQTT_STATUS, API_WIFI_DESC, API_WIFI_SIGNAL,
    BYPASS_INT_TO_STR,
    CT_CO2, CT_EXTRACT, CT_HUMIDITY, CT_INTAKE, CT_LAUNCHER, CT_SUPPLY,
    IDX_AIRING, IDX_BYPASS_MODE, IDX_BYPASS_STATUS,
    IDX_CLEANING, IDX_COMFORT_TEMP, IDX_COOLING,
    IDX_AIRFLOW_EXTRACT, IDX_AIRFLOW_SUPPLY,
    IDX_FAN_EXTRACT_RPM, IDX_FAN_HUMIDITY_MIRROR,
    IDX_FAN_MANUAL_EXTRACT, IDX_FAN_MANUAL_SUPPLY, IDX_FAN_SUPPLY_RPM,
    IDX_FAST_COOLING, IDX_FAST_HEATING, IDX_FILTER_ALARM, IDX_FILTER_DAYS,
    IDX_FIREPLACE, IDX_GWC, IDX_HEATING, IDX_HOLIDAY,
    IDX_IS_ON, IDX_MAX_AIRFLOW, IDX_MAX_COMFORT_TEMP, IDX_MIN_COMFORT_TEMP,
    IDX_SCHEDULE, IDX_TEMP_EXTRACT, IDX_TEMP_GWC,
    IDX_TEMP_HEATER, IDX_TEMP_INTAKE, IDX_TEMP_LAUNCHER,
    IDX_TEMP_SUPPLY, IDX_WORK_MODE,
)

_LOGGER = logging.getLogger(__name__)


class ReqnetMqttHandler:
    """Maintains device state from MQTT push messages.

    Entities call register_update_callback() to receive notifications
    whenever new data arrives.
    """

    def __init__(self, hass: HomeAssistant, mqtt_topic: str) -> None:
        self.hass = hass
        self.base_topic = mqtt_topic
        self._data: dict[str, Any] = {}
        self._listeners: list[Callable[[], None]] = []
        self._unsubs: list[Callable[[], None]] = []
        self.available = False
        # User preferences kept in memory (reset on HA restart)
        self._user_prefs: dict[str, Any] = {
            "airing_duration": 30,   # minutes; 0 = no limit
        }

    # ── Public interface ───────────────────────────────────────────

    def get_data(self) -> dict[str, Any]:
        return dict(self._data)

    def register_update_callback(self, cb: Callable[[], None]) -> None:
        self._listeners.append(cb)

    def unregister_update_callback(self, cb: Callable[[], None]) -> None:
        if cb in self._listeners:
            self._listeners.remove(cb)

    def set_user_pref(self, key: str, value: Any) -> None:
        self._user_prefs[key] = value

    def get_user_pref(self, key: str, default: Any = None) -> Any:
        return self._user_prefs.get(key, default)

    async def async_setup(self) -> None:
        """Subscribe to {MAC}/# and {MAC}.

        encoding=None lets us receive raw bytes and decode ourselves,
        avoiding HA's UTF-8 decode warnings for binary MQTT payloads
        from other integrations (e.g. Frigate camera snapshots).
        """
        for topic in (f"{self.base_topic}/#", self.base_topic):
            self._unsubs.append(
                await mqtt.async_subscribe(
                    self.hass,
                    topic,
                    self._handle_message,
                    qos=0,
                    encoding=None,
                )
            )
        _LOGGER.debug("ReqNet: subscribed to MQTT topic %s/#", self.base_topic)

    def async_teardown(self) -> None:
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()

    # ── Internal: message dispatch ─────────────────────────────────

    @callback
    def _handle_message(self, msg: mqtt.ReceiveMessage) -> None:
        raw = msg.payload
        if isinstance(raw, (bytes, bytearray)):
            try:
                raw = raw.decode("utf-8")
            except UnicodeDecodeError:
                return  # binary payload (e.g. camera image) — skip silently

        try:
            payload: dict = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return

        if not isinstance(payload, dict):
            return

        dispatched = False
        if payload.get("CurrentWorkParametersResult"):
            self._parse_cwp(payload)
            dispatched = True
        elif payload.get("CurrentTemperaturesResult"):
            self._parse_temperatures(payload)
            dispatched = True
        elif payload.get("APIResult"):
            self._parse_api_result(payload)
            dispatched = True
        elif payload.get("StatusDeviceResult"):
            self._parse_status_device(payload)
            dispatched = True
        elif payload.get("GetDateTimeResult"):
            self._parse_datetime(payload)
            dispatched = True
        elif payload.get("GetWorkParametersResult"):
            # Store raw for potential future use
            self._data["gwp_raw"] = payload.get("Values", [])
            dispatched = True

        if dispatched:
            if not self.available:
                _LOGGER.info("ReqNet: device online — %s", self.base_topic)
            self.available = True
            self._notify_listeners()

    # ── Parsers ────────────────────────────────────────────────────

    def _parse_cwp(self, p: dict) -> None:
        v: list = p.get("Values", [])

        def g(idx: int, default: Any = None) -> Any:
            try:
                return v[idx]
            except IndexError:
                return default

        self._data.update({
            "is_on":              bool(g(IDX_IS_ON, 0)),
            "work_mode":          int(g(IDX_WORK_MODE, 9)),
            "fan_manual_supply":  int(g(IDX_FAN_MANUAL_SUPPLY, 0)),
            "fan_manual_extract": int(g(IDX_FAN_MANUAL_EXTRACT, 0)),
            "fan_supply_rpm":     int(g(IDX_FAN_SUPPLY_RPM, 0)),
            "fan_extract_rpm":    int(g(IDX_FAN_EXTRACT_RPM, 0)),
            "airflow_supply":     int(g(IDX_AIRFLOW_SUPPLY, 0)),
            "airflow_extract":    int(g(IDX_AIRFLOW_EXTRACT, 0)),
            "max_airflow":        int(g(IDX_MAX_AIRFLOW, 500)),
            "comfort_temp":       float(g(IDX_COMFORT_TEMP, 20)),
            "max_comfort_temp":   float(g(IDX_MAX_COMFORT_TEMP, 30)),
            "min_comfort_temp":   float(g(IDX_MIN_COMFORT_TEMP, 15)),
            "bypass_open":        bool(g(IDX_BYPASS_STATUS, 0)),
            "bypass_mode":        BYPASS_INT_TO_STR.get(
                                      int(g(IDX_BYPASS_MODE, 0))
                                      if int(g(IDX_BYPASS_MODE, 0)) in BYPASS_INT_TO_STR
                                      else 0,
                                      "auto",
                                  ),
            "filter_days":        int(g(IDX_FILTER_DAYS, 0)),
            "filter_alarm":       bool(g(IDX_FILTER_ALARM, 0)),
            "airing":             bool(g(IDX_AIRING, 0)),
            "cleaning":           bool(g(IDX_CLEANING, 0)),
            "heating":            bool(g(IDX_HEATING, 0)),
            "cooling":            bool(g(IDX_COOLING, 0)),
            "fast_heating":       bool(g(IDX_FAST_HEATING, 0)),
            "fast_cooling":       bool(g(IDX_FAST_COOLING, 0)),
            "fireplace":          bool(g(IDX_FIREPLACE, 0)),
            "holiday":            bool(g(IDX_HOLIDAY, 0)),
            "schedule":           bool(g(IDX_SCHEDULE, 0)),
            "gwc_relay":          bool(g(IDX_GWC, 0)),
            # Temperatures from Values[] — overridden below by CurrentTemperatures
            "temp_supply":        float(g(IDX_TEMP_SUPPLY, 0)),
            "temp_extract":       float(g(IDX_TEMP_EXTRACT, 0)),
            "temp_intake":        float(g(IDX_TEMP_INTAKE, 0)),
            "temp_exhaust":       float(g(IDX_TEMP_LAUNCHER, 0)),
            "temp_heater":        float(g(IDX_TEMP_HEATER, 0)),
            "temp_gwc":           float(g(IDX_TEMP_GWC, 0)),
        })

    def _parse_temperatures(self, p: dict) -> None:
        def f(key: str, default: float = 0.0) -> float:
            try:
                return round(float(p.get(key, default)), 1)
            except (TypeError, ValueError):
                return default

        self._data.update({
            "temp_intake":  f(CT_INTAKE),
            "temp_exhaust": f(CT_LAUNCHER),
            "temp_supply":  f(CT_SUPPLY),
            "temp_extract": f(CT_EXTRACT),
            "humidity":     int(p.get(CT_HUMIDITY, 0)),
            "co2":          int(p.get(CT_CO2, 0)),
        })

    def _parse_api_result(self, p: dict) -> None:
        self._data.update({
            "fw_version":  str(p.get(API_FW_VERSION, "")),
            "wifi_signal": int(p.get(API_WIFI_SIGNAL, 0)),
            "wifi_desc":   str(p.get(API_WIFI_DESC, "")),
            "mqtt_ok":     bool(p.get(API_MQTT_STATUS, False)),
            "error_code":  int(p.get(API_ERROR_CODE, 0)),
            "device_type": int(p.get(API_DEVICE_TYPE, 0)),
            "mac":         str(p.get(API_MAC, "")),
        })

    def _parse_status_device(self, p: dict) -> None:
        self._data.setdefault("fw_version", str(p.get("RecuperatorSoftwareVersion", "")))
        self._data.setdefault("mac",        str(p.get("MAC", "")))
        self._data["wifi_ip"] = str(p.get("WIFIIP", ""))

    def _parse_datetime(self, p: dict) -> None:
        self._data["device_time"] = (
            f"{p.get('Hour', 0):02d}:{p.get('Min', 0):02d}:{p.get('Sec', 0):02d}"
            f" {p.get('Day', 1):02d}.{p.get('Month', 1):02d}.{p.get('Year', 2024)}"
        )

    def _notify_listeners(self) -> None:
        for cb in self._listeners:
            try:
                cb()
            except Exception:
                _LOGGER.exception("ReqNet: error in entity update callback")
