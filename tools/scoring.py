"""Fishing-score algorithm + tool wrapper."""
from __future__ import annotations

import time
from typing import Any

from db import connection as db


def compute_fishing_score(lake: dict, stockings: list[dict], weather: dict) -> int:
    """Compute a 0-100 fishing-favorability score.

    Buckets:
      Recent stocking      0-40
      Species diversity    0-20
      Lake size            0-15
      Weather              0-15
      Data freshness       0-10
    """
    score = 0
    now = time.time()

    # Recent stocking (0-40 pts)
    for s in stockings:
        ts = float(s.get("stocking_date", 0) or 0)
        age_days = (now - ts) / 86400 if ts else 1e9
        if age_days <= 30:
            score += 40
            break
        elif age_days <= 90:
            score += 20
            break
        elif age_days <= 180:
            score += 10
            break

    # Species diversity (0-20 pts): 4 pts per unique species, max 5
    species = {s["species"] for s in stockings if s.get("species")}
    score += min(20, len(species) * 4)

    # Lake size (0-15 pts)
    acres = lake.get("acres") or 0
    if acres >= 500:
        score += 15
    elif acres >= 100:
        score += 10
    else:
        score += 5

    # Weather bonus (0-15 pts)
    if weather and isinstance(weather, dict) and "current" in weather:
        cur = weather.get("current") or {}
        temp = cur.get("temperature_2m", 70)
        precip = cur.get("precipitation", 0)
        if 55 <= temp <= 75 and precip < 0.1:
            score += 15
        elif 45 <= temp <= 85 and precip < 0.5:
            score += 8

    # Data freshness (0-10 pts)
    if stockings:
        score += 10

    return int(min(100, max(0, score)))


def _breakdown(lake: dict, stockings: list[dict], weather: dict) -> dict[str, int]:
    """Re-derive per-bucket points so the agent sees how the score was built."""
    now = time.time()
    out = {"recent_stocking": 0, "species_diversity": 0, "lake_size": 0,
           "weather": 0, "data_freshness": 0}

    for s in stockings:
        ts = float(s.get("stocking_date", 0) or 0)
        age = (now - ts) / 86400 if ts else 1e9
        if age <= 30:
            out["recent_stocking"] = 40
            break
        elif age <= 90:
            out["recent_stocking"] = 20
            break
        elif age <= 180:
            out["recent_stocking"] = 10
            break

    species = {s["species"] for s in stockings if s.get("species")}
    out["species_diversity"] = min(20, len(species) * 4)

    acres = lake.get("acres") or 0
    out["lake_size"] = 15 if acres >= 500 else 10 if acres >= 100 else 5

    if weather and "current" in weather:
        cur = weather.get("current") or {}
        temp = cur.get("temperature_2m", 70)
        precip = cur.get("precipitation", 0)
        if 55 <= temp <= 75 and precip < 0.1:
            out["weather"] = 15
        elif 45 <= temp <= 85 and precip < 0.5:
            out["weather"] = 8

    if stockings:
        out["data_freshness"] = 10
    return out


async def get_fishing_score(lake_id: str) -> dict[str, Any]:
    from tools.weather import get_weather as _get_weather

    lake = await db.get_lake(lake_id)
    if not lake:
        return {"error": "lake_not_found", "lake_id": lake_id}
    stockings = await db.get_stockings(lake_id=lake_id, limit=50)
    try:
        weather = await _get_weather(lake["lat"], lake["lng"])
    except Exception:
        weather = {}

    score = compute_fishing_score(lake, stockings, weather or {})
    breakdown = _breakdown(lake, stockings, weather or {})
    return {
        "lake_id": lake_id,
        "lake_name": lake["name"],
        "state": lake["state"],
        "fishing_score": score,
        "breakdown": breakdown,
        "max_per_bucket": {
            "recent_stocking": 40,
            "species_diversity": 20,
            "lake_size": 15,
            "weather": 15,
            "data_freshness": 10,
        },
        "stockings_considered": len(stockings),
        "mode": db.get_mode(),
    }
