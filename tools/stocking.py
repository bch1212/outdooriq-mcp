"""Stocking-data tools."""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Optional

from db import connection as db


def _format_event(row: dict) -> dict:
    ts = float(row["stocking_date"])
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    return {
        "lake_id": row["lake_id"],
        "lake_name": row.get("lake_name"),
        "state": row.get("state"),
        "species": row["species"],
        "count": int(row["count"]),
        "stocking_date": dt.date().isoformat(),
        "stocking_timestamp": ts,
        "age_days": int((time.time() - ts) / 86400),
    }


async def get_stocking_data(
    *,
    lake_id: Optional[str] = None,
    species: Optional[str] = None,
    year: Optional[int] = None,
    limit: int = 25,
) -> dict[str, Any]:
    rows = await db.get_stockings(
        lake_id=lake_id, species=species, year=year, limit=limit
    )
    return {
        "count": len(rows),
        "events": [_format_event(r) for r in rows],
        "mode": db.get_mode(),
    }


async def get_stocking_schedule(
    *,
    state: Optional[str] = None,
    species: Optional[str] = None,
    month: Optional[int] = None,
    limit: int = 50,
) -> dict[str, Any]:
    """Most recent stocking activity matching the filters.

    "Schedule" is a forward-looking concept the prompt requested. The CastIQ
    dataset is historical, so we surface the most-recent prior events for the
    requested month/species/state — agents use this as a planning prior:
    "what does this state typically stock in May?"
    """
    rows = await db.get_stockings(
        state=state, species=species, month=month, limit=limit
    )
    return {
        "filters": {"state": state, "species": species, "month": month},
        "count": len(rows),
        "events": [_format_event(r) for r in rows],
        "mode": db.get_mode(),
    }


async def search_species(
    *,
    state: Optional[str] = None,
    season: Optional[str] = None,  # accepted but advisory only
) -> dict[str, Any]:
    species = await db.get_distinct_species(state=state)
    return {
        "state": state,
        "season": season,
        "count": len(species),
        "species": species,
        "mode": db.get_mode(),
    }
