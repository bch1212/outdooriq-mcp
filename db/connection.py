"""Postgres + SQLite fallback connection manager.

At init, attempt to open a Postgres pool against DATABASE_URL. If that fails
(or DATABASE_URL is unset), fall back to a bundled SQLite database seeded
with 100+ lakes and ~250 stocking events. The server always starts.

All query helpers below normalize results to the same dict shape so the
tools layer can be agnostic to the underlying engine.
"""
from __future__ import annotations

import asyncio
import json
import logging
import math
import os
from typing import Any, Iterable, Optional, Sequence

import aiosqlite

try:  # asyncpg is optional in some test environments
    import asyncpg  # type: ignore
except Exception:  # pragma: no cover - asyncpg should be installed in prod
    asyncpg = None  # type: ignore

log = logging.getLogger("outdooriq.db")

# Module-level state (single-process server)
_pg_pool: Any = None  # asyncpg.Pool when in Postgres mode
_sqlite_path: str = os.getenv("OUTDOORIQ_SQLITE_PATH", ":memory:")
_sqlite_db: Optional[aiosqlite.Connection] = None
_sqlite_mode: bool = False
_init_lock = asyncio.Lock()
_initialized = False


def is_sqlite_mode() -> bool:
    return _sqlite_mode


def get_mode() -> str:
    return "sqlite" if _sqlite_mode else "postgres"


# ---------------------------------------------------------------------------
# Init / shutdown
# ---------------------------------------------------------------------------

async def init_db(force_sqlite: bool = False) -> str:
    """Initialize the database. Returns the active mode string."""
    global _pg_pool, _sqlite_db, _sqlite_mode, _initialized

    async with _init_lock:
        if _initialized:
            return get_mode()

        db_url = os.getenv("DATABASE_URL")
        if db_url and not force_sqlite and asyncpg is not None:
            try:
                _pg_pool = await asyncpg.create_pool(
                    db_url, min_size=1, max_size=10, timeout=5.0
                )
                # smoke probe
                async with _pg_pool.acquire() as conn:
                    await conn.fetchval("SELECT 1")
                _sqlite_mode = False
                _initialized = True
                log.info("[OutdoorIQ] Running in Postgres mode")
                return "postgres"
            except Exception as exc:  # noqa: BLE001 - any failure → fall back
                log.warning("[OutdoorIQ] Postgres unavailable: %s", exc)
                _pg_pool = None

        _sqlite_mode = True
        _sqlite_db = await aiosqlite.connect(_sqlite_path)
        _sqlite_db.row_factory = aiosqlite.Row
        await _init_sqlite_schema(_sqlite_db)
        # seed
        from db.seed import seed_sqlite  # local import to avoid cycles
        await seed_sqlite(_sqlite_db)
        await _sqlite_db.commit()
        _initialized = True
        log.info("[OutdoorIQ] Running in SQLite fallback mode")
        return "sqlite"


async def shutdown_db() -> None:
    global _pg_pool, _sqlite_db, _initialized, _sqlite_mode
    if _pg_pool is not None:
        await _pg_pool.close()
        _pg_pool = None
    if _sqlite_db is not None:
        await _sqlite_db.close()
        _sqlite_db = None
    _initialized = False
    _sqlite_mode = False


async def reset_for_tests() -> None:
    """Drop in-memory state so tests can reinitialize cleanly."""
    await shutdown_db()


async def _init_sqlite_schema(db: aiosqlite.Connection) -> None:
    await db.executescript(
        """
        CREATE TABLE IF NOT EXISTS lakes (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            state TEXT NOT NULL,
            county TEXT,
            lat REAL,
            lng REAL,
            acres REAL,
            max_depth_ft REAL,
            facilities TEXT  -- JSON array
        );

        CREATE TABLE IF NOT EXISTS lake_species (
            lake_id TEXT NOT NULL,
            species TEXT NOT NULL,
            PRIMARY KEY (lake_id, species)
        );

        CREATE TABLE IF NOT EXISTS stockings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lake_id TEXT NOT NULL,
            species TEXT NOT NULL,
            count INTEGER NOT NULL,
            stocking_date REAL NOT NULL  -- unix epoch
        );

        CREATE INDEX IF NOT EXISTS idx_stockings_lake ON stockings(lake_id);
        CREATE INDEX IF NOT EXISTS idx_stockings_species ON stockings(species);
        CREATE INDEX IF NOT EXISTS idx_lakes_state ON lakes(state);
        """
    )


# ---------------------------------------------------------------------------
# Query helpers (engine-agnostic)
# ---------------------------------------------------------------------------

def _row_to_lake(row: Any) -> dict:
    """Normalize a row from either backend into a lake dict."""
    facilities = row["facilities"] if "facilities" in row.keys() else None
    if isinstance(facilities, str):
        try:
            facilities = json.loads(facilities)
        except Exception:
            facilities = []
    elif facilities is None:
        facilities = []
    return {
        "id": row["id"],
        "name": row["name"],
        "state": row["state"],
        "county": row["county"] if "county" in row.keys() else None,
        "lat": row["lat"],
        "lng": row["lng"],
        "acres": row["acres"],
        "max_depth_ft": row["max_depth_ft"] if "max_depth_ft" in row.keys() else None,
        "facilities": facilities or [],
    }


async def _sqlite_fetch_all(query: str, params: Sequence[Any] = ()) -> list[dict]:
    assert _sqlite_db is not None
    async with _sqlite_db.execute(query, params) as cur:
        rows = await cur.fetchall()
    return [dict(row) for row in rows]


async def _sqlite_fetch_one(query: str, params: Sequence[Any] = ()) -> Optional[dict]:
    assert _sqlite_db is not None
    async with _sqlite_db.execute(query, params) as cur:
        row = await cur.fetchone()
    return dict(row) if row else None


async def _pg_fetch_all(query: str, params: Sequence[Any] = ()) -> list[dict]:
    assert _pg_pool is not None
    async with _pg_pool.acquire() as conn:
        rows = await conn.fetch(query, *params)
    return [dict(r) for r in rows]


async def _pg_fetch_one(query: str, params: Sequence[Any] = ()) -> Optional[dict]:
    assert _pg_pool is not None
    async with _pg_pool.acquire() as conn:
        row = await conn.fetchrow(query, *params)
    return dict(row) if row else None


async def _hydrate_species(lakes: list[dict]) -> list[dict]:
    if not lakes:
        return lakes
    if _sqlite_mode:
        ids = [l["id"] for l in lakes]
        placeholders = ",".join("?" * len(ids))
        rows = await _sqlite_fetch_all(
            f"SELECT lake_id, species FROM lake_species WHERE lake_id IN ({placeholders})",
            ids,
        )
    else:
        ids = [l["id"] for l in lakes]
        rows = await _pg_fetch_all(
            "SELECT lake_id, species FROM lake_species WHERE lake_id = ANY($1)",
            (ids,),
        )
    by_id: dict[str, list[str]] = {}
    for r in rows:
        by_id.setdefault(r["lake_id"], []).append(r["species"])
    for l in lakes:
        l["species"] = sorted(by_id.get(l["id"], []))
    return lakes


# Public query API ----------------------------------------------------------

async def search_lakes(
    *,
    name: Optional[str] = None,
    state: Optional[str] = None,
    county: Optional[str] = None,
    min_acres: Optional[float] = None,
    max_acres: Optional[float] = None,
    limit: int = 25,
) -> list[dict]:
    limit = max(1, min(int(limit or 25), 200))
    if _sqlite_mode:
        clauses, params = [], []
        if name:
            clauses.append("LOWER(name) LIKE ?")
            params.append(f"%{name.lower()}%")
        if state:
            clauses.append("state = ?")
            params.append(state.upper())
        if county:
            clauses.append("LOWER(county) = ?")
            params.append(county.lower())
        if min_acres is not None:
            clauses.append("acres >= ?")
            params.append(float(min_acres))
        if max_acres is not None:
            clauses.append("acres <= ?")
            params.append(float(max_acres))
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        rows = await _sqlite_fetch_all(
            f"SELECT * FROM lakes {where} ORDER BY acres DESC LIMIT ?",
            (*params, limit),
        )
    else:
        clauses, params = [], []
        i = 1
        if name:
            clauses.append(f"LOWER(name) LIKE ${i}")
            params.append(f"%{name.lower()}%")
            i += 1
        if state:
            clauses.append(f"state = ${i}")
            params.append(state.upper())
            i += 1
        if county:
            clauses.append(f"LOWER(county) = ${i}")
            params.append(county.lower())
            i += 1
        if min_acres is not None:
            clauses.append(f"acres >= ${i}")
            params.append(float(min_acres))
            i += 1
        if max_acres is not None:
            clauses.append(f"acres <= ${i}")
            params.append(float(max_acres))
            i += 1
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        rows = await _pg_fetch_all(
            f"SELECT id, name, state, county, lat, lng, acres, max_depth_ft, facilities "
            f"FROM lakes {where} ORDER BY acres DESC NULLS LAST LIMIT ${i}",
            (*params, limit),
        )
    lakes = [_row_to_lake(r) for r in rows]
    return await _hydrate_species(lakes)


async def get_lake(lake_id: str) -> Optional[dict]:
    if _sqlite_mode:
        row = await _sqlite_fetch_one("SELECT * FROM lakes WHERE id = ?", (lake_id,))
    else:
        row = await _pg_fetch_one(
            "SELECT id, name, state, county, lat, lng, acres, max_depth_ft, facilities "
            "FROM lakes WHERE id = $1",
            (lake_id,),
        )
    if not row:
        return None
    lake = _row_to_lake(row)
    await _hydrate_species([lake])
    return lake


async def get_stockings(
    *,
    lake_id: Optional[str] = None,
    species: Optional[str] = None,
    state: Optional[str] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    limit: int = 50,
) -> list[dict]:
    limit = max(1, min(int(limit or 50), 500))
    if _sqlite_mode:
        clauses, params = [], []
        if lake_id:
            clauses.append("s.lake_id = ?")
            params.append(lake_id)
        if species:
            clauses.append("LOWER(s.species) = ?")
            params.append(species.lower())
        if state:
            clauses.append("l.state = ?")
            params.append(state.upper())
        if year is not None:
            clauses.append("CAST(strftime('%Y', s.stocking_date, 'unixepoch') AS INTEGER) = ?")
            params.append(int(year))
        if month is not None:
            clauses.append("CAST(strftime('%m', s.stocking_date, 'unixepoch') AS INTEGER) = ?")
            params.append(int(month))
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        rows = await _sqlite_fetch_all(
            f"SELECT s.id, s.lake_id, s.species, s.count, s.stocking_date, l.name AS lake_name, l.state "
            f"FROM stockings s JOIN lakes l ON l.id = s.lake_id "
            f"{where} ORDER BY s.stocking_date DESC LIMIT ?",
            (*params, limit),
        )
    else:
        clauses, params = [], []
        i = 1
        if lake_id:
            clauses.append(f"s.lake_id = ${i}")
            params.append(lake_id)
            i += 1
        if species:
            clauses.append(f"LOWER(s.species) = ${i}")
            params.append(species.lower())
            i += 1
        if state:
            clauses.append(f"l.state = ${i}")
            params.append(state.upper())
            i += 1
        if year is not None:
            clauses.append(f"EXTRACT(YEAR FROM to_timestamp(s.stocking_date)) = ${i}")
            params.append(int(year))
            i += 1
        if month is not None:
            clauses.append(f"EXTRACT(MONTH FROM to_timestamp(s.stocking_date)) = ${i}")
            params.append(int(month))
            i += 1
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        rows = await _pg_fetch_all(
            f"SELECT s.id, s.lake_id, s.species, s.count, s.stocking_date, l.name AS lake_name, l.state "
            f"FROM stockings s JOIN lakes l ON l.id = s.lake_id "
            f"{where} ORDER BY s.stocking_date DESC LIMIT ${i}",
            (*params, limit),
        )
    return rows


async def get_lakes_within_bbox(
    *,
    lat: float,
    lng: float,
    radius_miles: float,
    limit: int = 100,
) -> list[dict]:
    """Return lakes inside a bounding-box approximation, then we'll filter exactly."""
    delta_lat = radius_miles / 69.0
    delta_lng = radius_miles / max(0.0001, (69.0 * math.cos(math.radians(lat))))
    lat_min, lat_max = lat - delta_lat, lat + delta_lat
    lng_min, lng_max = lng - delta_lng, lng + delta_lng
    if _sqlite_mode:
        rows = await _sqlite_fetch_all(
            "SELECT * FROM lakes WHERE lat BETWEEN ? AND ? AND lng BETWEEN ? AND ? LIMIT ?",
            (lat_min, lat_max, lng_min, lng_max, limit * 4),
        )
    else:
        rows = await _pg_fetch_all(
            "SELECT id, name, state, county, lat, lng, acres, max_depth_ft, facilities "
            "FROM lakes WHERE lat BETWEEN $1 AND $2 AND lng BETWEEN $3 AND $4 LIMIT $5",
            (lat_min, lat_max, lng_min, lng_max, limit * 4),
        )
    lakes = [_row_to_lake(r) for r in rows]
    return await _hydrate_species(lakes)


async def get_top_lakes_by_state(
    *,
    state: Optional[str] = None,
    species: Optional[str] = None,
    limit: int = 20,
) -> list[dict]:
    limit = max(1, min(int(limit or 20), 100))
    if _sqlite_mode:
        if species:
            rows = await _sqlite_fetch_all(
                """
                SELECT l.* FROM lakes l
                JOIN lake_species ls ON ls.lake_id = l.id
                WHERE (? IS NULL OR l.state = ?)
                  AND LOWER(ls.species) = ?
                ORDER BY l.acres DESC
                LIMIT ?
                """,
                (state.upper() if state else None, state.upper() if state else None,
                 species.lower(), limit),
            )
        else:
            rows = await _sqlite_fetch_all(
                "SELECT * FROM lakes WHERE (? IS NULL OR state = ?) ORDER BY acres DESC LIMIT ?",
                (state.upper() if state else None, state.upper() if state else None, limit),
            )
    else:
        if species:
            rows = await _pg_fetch_all(
                """
                SELECT l.id, l.name, l.state, l.county, l.lat, l.lng, l.acres, l.max_depth_ft, l.facilities
                FROM lakes l
                JOIN lake_species ls ON ls.lake_id = l.id
                WHERE ($1::text IS NULL OR l.state = $1)
                  AND LOWER(ls.species) = $2
                ORDER BY l.acres DESC NULLS LAST
                LIMIT $3
                """,
                (state.upper() if state else None, species.lower(), limit),
            )
        else:
            rows = await _pg_fetch_all(
                "SELECT id, name, state, county, lat, lng, acres, max_depth_ft, facilities "
                "FROM lakes WHERE ($1::text IS NULL OR state = $1) "
                "ORDER BY acres DESC NULLS LAST LIMIT $2",
                (state.upper() if state else None, limit),
            )
    lakes = [_row_to_lake(r) for r in rows]
    return await _hydrate_species(lakes)


async def get_distinct_species(state: Optional[str] = None) -> list[str]:
    if _sqlite_mode:
        if state:
            rows = await _sqlite_fetch_all(
                "SELECT DISTINCT s.species FROM stockings s "
                "JOIN lakes l ON l.id = s.lake_id WHERE l.state = ? "
                "ORDER BY s.species",
                (state.upper(),),
            )
        else:
            rows = await _sqlite_fetch_all(
                "SELECT DISTINCT species FROM stockings ORDER BY species"
            )
    else:
        if state:
            rows = await _pg_fetch_all(
                "SELECT DISTINCT s.species FROM stockings s "
                "JOIN lakes l ON l.id = s.lake_id WHERE l.state = $1 "
                "ORDER BY s.species",
                (state.upper(),),
            )
        else:
            rows = await _pg_fetch_all(
                "SELECT DISTINCT species FROM stockings ORDER BY species"
            )
    return [r["species"] for r in rows]


# ---------------------------------------------------------------------------
# Test helper — direct SQLite handle, used by seed.py
# ---------------------------------------------------------------------------

def _sqlite_handle() -> aiosqlite.Connection:
    assert _sqlite_db is not None, "SQLite not initialized"
    return _sqlite_db
