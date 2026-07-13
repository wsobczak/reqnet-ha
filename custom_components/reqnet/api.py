"""REST API client for reQnet — used for commands only.

State is received via MQTT push (see mqtt_handler.py).
API endpoint: GET http://{host}/API/RunFunction?name={Function}&param=value
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)
_TIMEOUT = aiohttp.ClientTimeout(total=10)


class ReqnetApiError(Exception):
    """General API error."""


class ReqnetConnectionError(ReqnetApiError):
    """Cannot reach device."""


class ReqnetApi:
    """reQnet REST API client."""

    def __init__(self, host: str, session: aiohttp.ClientSession) -> None:
        self._host = host.rstrip("/")
        self._session = session
        self._base = f"http://{self._host}/API/RunFunction"

    async def _call(self, fn: str, params: dict[str, Any] | None = None) -> dict:
        q: dict[str, Any] = {"name": fn}
        if params:
            q.update(params)
        try:
            async with self._session.get(self._base, params=q, timeout=_TIMEOUT) as r:
                r.raise_for_status()
                return await r.json(content_type=None) or {}
        except aiohttp.ClientConnectionError as exc:
            raise ReqnetConnectionError(f"Cannot connect to {self._host}") from exc
        except asyncio.TimeoutError as exc:
            raise ReqnetConnectionError(f"Timeout connecting to {self._host}") from exc
        except Exception as exc:
            raise ReqnetApiError(str(exc)) from exc

    # ── Power ──────────────────────────────────────────────────────
    async def turn_on(self) -> dict:
        return await self._call("TurnOn")

    async def turn_off(self) -> dict:
        return await self._call("TurnOff")

    # ── Operating modes ────────────────────────────────────────────
    async def set_automatic_mode(self) -> dict:
        return await self._call("AutomaticMode")

    async def set_manual_mode(
        self,
        fan_supply: int | None = None,
        fan_extract: int | None = None,
    ) -> dict:
        p: dict[str, Any] = {}
        if fan_supply is not None:
            p["FAN_SUPPLY"] = fan_supply
        if fan_extract is not None:
            p["FAN_EXTRACT"] = fan_extract
        return await self._call("ManualMode", p or None)

    async def set_comfort_temperature(self, temp: float) -> dict:
        return await self._call("SetComfortTemperature", {"COMFORT_TEMP": temp})

    async def set_bypass_mode(self, mode: str) -> dict:
        value = {"auto": 0, "open": 1, "closed": 2}.get(mode, 0)
        return await self._call("SetByPassMode", {"BYPASS_MODE": value})

    # ── Functional modes ───────────────────────────────────────────
    async def set_airing(self, on: bool, duration_min: int | None = None) -> dict:
        """Enable/disable airing mode. duration_min=0 or None means no time limit."""
        if on:
            params = {"TIME": duration_min} if duration_min else None
            return await self._call("TurnOnAiring", params)
        return await self._call("TurnOffAiring")

    async def set_cleaning(self, on: bool) -> dict:
        return await self._call("TurnOnCleaning" if on else "TurnOffCleaning")

    async def set_heating(self, on: bool) -> dict:
        return await self._call("TurnOnHeating" if on else "TurnOffHeating")

    async def set_cooling(self, on: bool) -> dict:
        return await self._call("TurnOnCooling" if on else "TurnOffCooling")

    async def set_fast_heating(self, on: bool) -> dict:
        return await self._call("TurnOnFastHeating" if on else "TurnOffFastHeating")

    async def set_fast_cooling(self, on: bool) -> dict:
        return await self._call("TurnOnFastCooling" if on else "TurnOffFastCooling")

    async def set_fireplace(self, on: bool, duration_min: int | None = None) -> dict:
        if on:
            params = {"TIME": duration_min} if duration_min else None
            return await self._call("TurnOnFireplace", params)
        return await self._call("TurnOffFireplace")

    async def set_holiday(self, on: bool) -> dict:
        return await self._call("TurnOnHoliday" if on else "TurnOffHoliday")

    async def set_schedule(self, on: bool) -> dict:
        return await self._call("TurnOnSchedule" if on else "TurnOffSchedule")

    async def set_gwc(self, on: bool) -> dict:
        return await self._call("SetGWCMode", {"GWC_MODE": 1 if on else 0})

    # ── Maintenance ────────────────────────────────────────────────
    async def replace_filters(self) -> dict:
        return await self._call("ReplaceFilters")

    async def delete_error_log(self) -> dict:
        return await self._call("DeleteErrorLog")

    # ── MQTT broker configuration ──────────────────────────────────
    async def configure_mqtt_broker(
        self,
        broker_ip: str,
        port: int = 1883,
        user: str = "",
        password: str = "",
    ) -> dict:
        """Push secondary MQTT broker config to the device."""
        result = await self._call("ChangeAdditionalBrokerConfiguration", {
            "MQTT_ADDITIONAL_BROKER_ADDRESS":  broker_ip,
            "MQTT_ADDITIONAL_BROKER_PORT":     port,
            "MQTT_ADDITIONAL_BROKER_USER":     user,
            "MQTT_ADDITIONAL_BROKER_PASSWORD": password,
        })
        _LOGGER.warning(
            "ReqNet MQTT broker config sent: %s:%s user=%r → %s",
            broker_ip, port, user, result,
        )
        return result
