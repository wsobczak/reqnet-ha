"""Config flow for reQnet — auto-configures MQTT broker on the device."""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components import mqtt
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ReqnetApi, ReqnetConnectionError
from .const import CONF_HOST, CONF_MQTT_TOPIC, DOMAIN

_LOGGER = logging.getLogger(__name__)

CONF_MQTT_BROKER   = "mqtt_broker"
CONF_MQTT_PORT     = "mqtt_port"
CONF_MQTT_USER     = "mqtt_user"
CONF_MQTT_PASSWORD = "mqtt_password"

_MAC_RE = re.compile(r"^([0-9A-Fa-f]{2}[:\-]){5}[0-9A-Fa-f]{2}$")
_DISCOVERY_TIMEOUT = 30  # seconds


def _ha_mqtt_defaults(hass) -> dict:
    """Pre-fill MQTT credentials from HA's own MQTT integration."""
    d = {"broker": "", "port": 1883, "username": "", "password": ""}
    for entry in hass.config_entries.async_entries("mqtt"):
        d.update({
            "broker":   entry.data.get("broker", ""),
            "port":     int(entry.data.get("port", 1883)),
            "username": entry.data.get("username", ""),
            "password": entry.data.get("password", ""),
        })
        break
    # Replace loopback with HA's actual IP
    if not d["broker"] or d["broker"] in ("localhost", "127.0.0.1", "::1"):
        try:
            d["broker"] = hass.config.api.host  # type: ignore[union-attr]
        except Exception:
            pass
    return d


class ReqnetConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow:
      Step 1 (user)         — IP + MQTT broker credentials
      Step 2 (discover_mac) — push config to device, wait for first MQTT message
      Step 3 (confirm)      — confirm discovered MAC
      Fallback (manual_mac) — enter MAC manually on timeout
    """

    VERSION = 1

    def __init__(self) -> None:
        self._host = ""
        self._mqtt_broker = ""
        self._mqtt_port = 1883
        self._mqtt_user = ""
        self._mqtt_password = ""
        self._discovered_mac: str | None = None
        self._discovery_task: asyncio.Task | None = None

    # ── Step 1 ─────────────────────────────────────────────────────

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}
        defaults = _ha_mqtt_defaults(self.hass)

        if user_input is not None:
            self._host          = user_input[CONF_HOST].strip()
            self._mqtt_broker   = user_input[CONF_MQTT_BROKER].strip()
            self._mqtt_port     = int(user_input[CONF_MQTT_PORT])
            self._mqtt_user     = user_input.get(CONF_MQTT_USER, "").strip()
            self._mqtt_password = user_input.get(CONF_MQTT_PASSWORD, "").strip()

            session = async_get_clientsession(self.hass)
            api = ReqnetApi(self._host, session)

            try:
                await api._call("CurrentWorkParameters")
            except ReqnetConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("ReqNet config flow: unexpected error")
                errors["base"] = "unknown"

            if not errors:
                try:
                    await api.configure_mqtt_broker(
                        self._mqtt_broker,
                        self._mqtt_port,
                        self._mqtt_user,
                        self._mqtt_password,
                    )
                except Exception as exc:
                    _LOGGER.warning("ReqNet: broker config call failed: %s", exc)
                    errors["base"] = "broker_config_failed"

            if not errors:
                return await self.async_step_discover_mac()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_MQTT_BROKER, default=defaults["broker"]): str,
                vol.Optional(CONF_MQTT_PORT,     default=defaults["port"]): vol.All(int, vol.Range(min=1, max=65535)),
                vol.Optional(CONF_MQTT_USER,     default=defaults["username"]): str,
                vol.Optional(CONF_MQTT_PASSWORD, default=defaults["password"]): str,
            }),
            errors=errors,
        )

    # ── Step 2 — MAC discovery ─────────────────────────────────────

    async def async_step_discover_mac(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if self._discovery_task is None:
            self._discovery_task = self.hass.async_create_task(
                self._discover_mac_from_mqtt(),
                eager_start=False,
            )

        if not self._discovery_task.done():
            return self.async_show_progress(
                step_id="discover_mac",
                progress_action="discovering",
                progress_task=self._discovery_task,
            )

        if self._discovered_mac:
            return self.async_show_progress_done(next_step_id="confirm")
        return self.async_show_progress_done(next_step_id="manual_mac")

    async def _discover_mac_from_mqtt(self) -> None:
        """Subscribe '#' and extract MAC from first matching topic."""
        found: asyncio.Future[str] = self.hass.loop.create_future()

        def _on_message(msg: mqtt.ReceiveMessage) -> None:
            raw = msg.payload
            if isinstance(raw, (bytes, bytearray)):
                try:
                    raw = raw.decode("utf-8")
                except UnicodeDecodeError:
                    return
            candidate = msg.topic.split("/")[0]
            if _MAC_RE.match(candidate) and not found.done():
                found.set_result(candidate.upper())

        unsub = await mqtt.async_subscribe(
            self.hass, "#", _on_message, qos=0, encoding=None,
        )
        try:
            mac = await asyncio.wait_for(found, timeout=_DISCOVERY_TIMEOUT)
            _LOGGER.info("ReqNet: discovered MAC %s", mac)
            self._discovered_mac = mac
        except asyncio.TimeoutError:
            _LOGGER.warning(
                "ReqNet: MQTT discovery timed out (%ss) — broker %s:%s",
                _DISCOVERY_TIMEOUT, self._mqtt_broker, self._mqtt_port,
            )
            self._discovered_mac = None
        finally:
            unsub()

    # ── Step 3 — Confirm ───────────────────────────────────────────

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            return self._create_entry(self._discovered_mac)  # type: ignore[arg-type]
        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema({}),
            description_placeholders={"mac": self._discovered_mac or "?"},
        )

    # ── Fallback — manual MAC entry ────────────────────────────────

    async def async_step_manual_mac(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            mac = user_input[CONF_MQTT_TOPIC].strip().upper()
            if _MAC_RE.match(mac):
                return self._create_entry(mac)
            errors[CONF_MQTT_TOPIC] = "invalid_mac"

        return self.async_show_form(
            step_id="manual_mac",
            data_schema=vol.Schema({vol.Required(CONF_MQTT_TOPIC): str}),
            errors=errors,
            description_placeholders={
                "broker": self._mqtt_broker,
                "port":   str(self._mqtt_port),
                "timeout": str(_DISCOVERY_TIMEOUT),
            },
        )

    def _create_entry(self, mac: str) -> FlowResult:
        return self.async_create_entry(
            title=f"reQnet {mac}",
            data={CONF_HOST: self._host, CONF_MQTT_TOPIC: mac},
        )
