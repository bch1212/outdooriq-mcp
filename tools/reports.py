"""Natural-language fishing report summaries (deterministic templating)."""
from __future__ import annotations

import time
from typing import Any

from db import connection as db
from tools.scoring import compute_fishing_score


def _bucket_label(score: int) -> str:
    if score >= 80:
        return "excellent"
    if score >= 65:
        return "very good"
    if score >= 50:
        return "good"
    if score >= 35:
        return "fair"
    return "slow"


def _weather_line(weather: dict[str, Any]) -> str:
    if not weather or "current" not in weather:
        return "Weather data unavailable; rely on local conditions."
    cur = weather["current"]
    temp = cur.get("temperature_2m")
    wind = cur.get("wind_speed_10m")
    precip = cur.get("precipitation", 0)
    parts = []
    if temp is not None:
        parts.append(f"current temp {round(float(temp))}°F")
    if wind is not None:
        parts.append(f"wind {round(float(wind))} mph")
    if precip:
        parts.append(f"{precip} in precip")
    daily = weather.get("daily") or {}
    highs = daily.get("temperature_2m_max") or []
    lows = daily.get("temperature_2m_min") or []
    if highs and lows:
        parts.append(
            f"7-day range {round(float(min(lows)))}–{round(float(max(highs)))}°F"
        )
    return ", ".join(parts) or "conditions look stable"


def _stocking_line(stockings: list[dict]) -> str:
    if not stockings:
        return "No recent stocking events on file."
    now = time.time()
    recent = [s for s in stockings if (now - float(s["stocking_date"])) / 86400 <= 60]
    if not recent:
        most_recent = stockings[0]
        age = int((now - float(most_recent["stocking_date"])) / 86400)
        return (
            f"Last stocking was {age} days ago "
            f"({int(most_recent['count']):,} {most_recent['species']})."
        )
    species_counts: dict[str, int] = {}
    for s in recent:
        species_counts[s["species"]] = species_counts.get(s["species"], 0) + int(s["count"])
    summary = ", ".join(f"{c:,} {sp}" for sp, c in species_counts.items())
    return f"In the last 60 days: {summary}."


async def get_fishing_report_summary(lake_id: str) -> dict[str, Any]:
    """Return a short natural-language summary plus the structured fields."""
    from tools.weather import get_weather as _get_weather

    lake = await db.get_lake(lake_id)
    if not lake:
        return {"error": "lake_not_found", "lake_id": lake_id}

    stockings = await db.get_stockings(lake_id=lake_id, limit=25)
    try:
        weather = await _get_weather(lake["lat"], lake["lng"])
    except Exception:
        weather = {}

    score = compute_fishing_score(lake, stockings, weather or {})
    label = _bucket_label(score)

    species_str = ", ".join(lake.get("species") or []) or "no documented target species"
    summary_lines = [
        f"{lake['name']} ({lake['state']}) — fishing outlook is {label} "
        f"(score {score}/100).",
        f"Acreage: {int(lake.get('acres') or 0):,}; species: {species_str}.",
        _stocking_line(stockings),
        f"Weather: {_weather_line(weather or {})}.",
    ]

    return {
        "lake_id": lake_id,
        "lake_name": lake["name"],
        "state": lake["state"],
        "fishing_score": score,
        "outlook": label,
        "summary": " ".join(summary_lines),
        "lines": summary_lines,
        "mode": db.get_mode(),
    }
