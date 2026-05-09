"""Open-Meteo integration. No API key required."""
from __future__ import annotations

import asyncio
import os
import time
from typing import Any, Optional

import httpx

from db import connection as db

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# Tiny in-process cache so consecutive scoring calls don't hammer the API.
_CACHE_TTL_SECONDS = int(os.getenv("OUTDOORIQ_WEATHER_TTL", "600"))
_cache: dict[tuple[float, float], tuple[float, dict[str, Any]]] = {}
_cache_lock = asyncio.Lock()


async def get_weather(lat: float, lng: float) -> dict[str, Any]:
    """Fetch current + 7-day forecast for a coordinate.

    Returns Open-Meteo's raw shape (with `current` and `daily` keys) so the
    score algorithm and report generator can read it directly. Returns an
    empty dict on transport error rather than raising — outdoor data tools
    must remain useful when the third-party is flaky.
    """
    if lat is None or lng is None:
        return {}
    key = (round(float(lat), 3), round(float(lng), 3))
    now = time.time()
    async with _cache_lock:
        cached = _cache.get(key)
        if cached and (now - cached[0]) < _CACHE_TTL_SECONDS:
            return cached[1]

    params = {
        "latitude": key[0],
        "longitude": key[1],
        "current": "temperature_2m,wind_speed_10m,precipitation,weathercode",
        "daily": "precipitation_sum,temperature_2m_max,temperature_2m_min,weathercode",
        "forecast_days": 7,
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(OPEN_METEO_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        return {}

    async with _cache_lock:
        _cache[key] = (now, data)
    return data


async def get_weather_for_lake(lake_id: str) -> dict[str, Any]:
    lake = await db.get_lake(lake_id)
    if not lake:
        return {"error": "lake_not_found", "lake_id": lake_id}
    weather = await get_weather(lake["lat"], lake["lng"])
    if not weather:
        return {
            "lake_id": lake_id,
            "lake_name": lake["name"],
            "available": False,
            "note": "Weather provider unreachable; try again shortly.",
        }
    return {
        "lake_id": lake_id,
        "lake_name": lake["name"],
        "state": lake["state"],
        "available": True,
        "current": weather.get("current"),
        "daily": weather.get("daily"),
        "units": {
            "temperature": "F",
            "wind_speed": "mph",
            "precipitation": "in",
        },
        "mode": db.get_mode(),
    }


def clear_cache() -> None:
    """Test helper."""
    _cache.clear()
