"""Lake search / details / nearby tools."""
from __future__ import annotations

import math
from typing import Any, Optional

from db import connection as db


def _haversine_miles(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 3958.8
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlng / 2) ** 2
    )
    return 2 * R * math.asin(math.sqrt(a))


async def search_lakes(
    *,
    name: Optional[str] = None,
    state: Optional[str] = None,
    county: Optional[str] = None,
    min_acres: Optional[float] = None,
    max_acres: Optional[float] = None,
    limit: int = 25,
) -> dict[str, Any]:
    rows = await db.search_lakes(
        name=name,
        state=state,
        county=county,
        min_acres=min_acres,
        max_acres=max_acres,
        limit=limit,
    )
    return {
        "count": len(rows),
        "mode": db.get_mode(),
        "lakes": [
            {
                "id": r["id"],
                "name": r["name"],
                "state": r["state"],
                "county": r.get("county"),
                "lat": r["lat"],
                "lng": r["lng"],
                "acres": r["acres"],
                "species": r.get("species", []),
            }
            for r in rows
        ],
    }


async def get_lake_details(lake_id: str) -> dict[str, Any]:
    lake = await db.get_lake(lake_id)
    if not lake:
        return {"error": "lake_not_found", "lake_id": lake_id}
    return {
        "lake": {
            "id": lake["id"],
            "name": lake["name"],
            "state": lake["state"],
            "county": lake.get("county"),
            "coordinates": {"lat": lake["lat"], "lng": lake["lng"]},
            "acres": lake["acres"],
            "max_depth_ft": lake.get("max_depth_ft"),
            "species": lake.get("species", []),
            "facilities": lake.get("facilities", []),
        },
        "mode": db.get_mode(),
    }


async def get_nearby_lakes(
    *,
    lat: float,
    lng: float,
    radius_miles: float = 25.0,
    min_score: int = 0,
    limit: int = 20,
) -> dict[str, Any]:
    """Lakes within `radius_miles`, sorted by fishing score descending."""
    from tools.scoring import compute_fishing_score
    from tools.weather import get_weather as _get_weather

    candidates = await db.get_lakes_within_bbox(
        lat=lat, lng=lng, radius_miles=float(radius_miles), limit=limit * 4
    )

    # exact filter by haversine
    enriched: list[dict[str, Any]] = []
    for lake in candidates:
        if lake["lat"] is None or lake["lng"] is None:
            continue
        d = _haversine_miles(lat, lng, lake["lat"], lake["lng"])
        if d > float(radius_miles):
            continue
        stockings = await db.get_stockings(lake_id=lake["id"], limit=50)
        # weather is best-effort — skip on failure to avoid slow N×http on miss
        try:
            weather = await _get_weather(lake["lat"], lake["lng"])
        except Exception:
            weather = None
        score = compute_fishing_score(lake, stockings, weather or {})
        if score < int(min_score):
            continue
        enriched.append(
            {
                "id": lake["id"],
                "name": lake["name"],
                "state": lake["state"],
                "lat": lake["lat"],
                "lng": lake["lng"],
                "acres": lake["acres"],
                "species": lake.get("species", []),
                "distance_miles": round(d, 1),
                "fishing_score": score,
            }
        )

    enriched.sort(key=lambda x: (-x["fishing_score"], x["distance_miles"]))
    return {
        "origin": {"lat": lat, "lng": lng},
        "radius_miles": float(radius_miles),
        "count": len(enriched[:limit]),
        "lakes": enriched[:limit],
        "mode": db.get_mode(),
    }


async def get_top_lakes(
    *,
    state: Optional[str] = None,
    species: Optional[str] = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Top lakes by fishing score in a state and/or filtered by species."""
    from tools.scoring import compute_fishing_score
    from tools.weather import get_weather as _get_weather

    candidates = await db.get_top_lakes_by_state(
        state=state, species=species, limit=max(int(limit) * 3, 30)
    )
    enriched: list[dict[str, Any]] = []
    for lake in candidates:
        stockings = await db.get_stockings(lake_id=lake["id"], limit=50)
        try:
            weather = await _get_weather(lake["lat"], lake["lng"]) if lake["lat"] else None
        except Exception:
            weather = None
        score = compute_fishing_score(lake, stockings, weather or {})
        enriched.append(
            {
                "id": lake["id"],
                "name": lake["name"],
                "state": lake["state"],
                "acres": lake["acres"],
                "species": lake.get("species", []),
                "fishing_score": score,
            }
        )

    enriched.sort(key=lambda x: -x["fishing_score"])
    return {
        "filters": {"state": state, "species": species},
        "count": len(enriched[: int(limit)]),
        "lakes": enriched[: int(limit)],
        "mode": db.get_mode(),
    }
