"""OutdoorIQ test suite.

Covers:
- DB init in SQLite mode (Postgres absent)
- Postgres "mode" via mock pool (verifies the dispatch branch without
  needing a live Postgres server)
- All 10 MCP tools through both the REST surface and direct calls
- /mcp JSON-RPC: initialize, tools/list, tools/call
- Auth: missing key 401, bad key 401, free-key over-limit 429
- Fishing-score algorithm bucket math
"""
from __future__ import annotations

import asyncio
import os
import time
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

# Force SQLite path before anything imports `db.connection`
os.environ.pop("DATABASE_URL", None)
os.environ["OUTDOORIQ_SQLITE_PATH"] = ":memory:"
os.environ["OUTDOORIQ_DEV_KEY"] = "test-free-key"
os.environ["OUTDOORIQ_FREE_DAILY_LIMIT"] = "5"
os.environ["OUTDOORIQ_EXTRA_KEYS"] = "test-pro-key:pro"

from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402
from db import connection as dbconn  # noqa: E402
from db import keys as keymgr  # noqa: E402
from db import seed as seed_mod  # noqa: E402
from tools import scoring as scoring_tools  # noqa: E402
from tools import weather as weather_tools  # noqa: E402


FREE_HEADERS = {"X-API-Key": "test-free-key"}
PRO_HEADERS = {"X-API-Key": "test-pro-key"}


@pytest_asyncio.fixture(scope="function")
async def client():
    """Boot the FastAPI app with the lifespan handler so DB + keys init."""
    # disable real network in scoring/nearby paths by short-circuiting weather
    weather_tools.clear_cache()
    original_get = weather_tools.get_weather

    async def fake_weather(lat, lng):  # noqa: ANN001
        return {
            "current": {"temperature_2m": 65, "wind_speed_10m": 7, "precipitation": 0.0},
            "daily": {
                "temperature_2m_max": [70, 71, 69, 68, 67, 66, 70],
                "temperature_2m_min": [50, 52, 49, 48, 51, 50, 53],
                "precipitation_sum": [0, 0, 0.1, 0, 0, 0, 0],
                "weathercode": [1, 2, 3, 1, 1, 1, 2],
            },
        }

    weather_tools.get_weather = fake_weather  # type: ignore

    with TestClient(server.app) as c:
        # reset usage so each test gets a fresh budget
        keymgr.reset_usage()
        yield c

    weather_tools.get_weather = original_get  # type: ignore


# ---------------------------------------------------------------------------
# Sanity / mode
# ---------------------------------------------------------------------------

def test_sqlite_mode_active(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["db_mode"] == "sqlite"
    assert body["tool_count"] == 10


def test_root_banner_mentions_pricing(client: TestClient) -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    text = resp.text
    assert "OutdoorIQ" in text
    assert "$14/mo" in text
    assert "72,000+" in text


def test_seed_data_volume() -> None:
    assert seed_mod.lake_count() >= 100
    assert seed_mod.stocking_event_count() >= 100


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def test_auth_missing_key_returns_401(client: TestClient) -> None:
    resp = client.get("/v1/tools")
    assert resp.status_code == 401


def test_auth_invalid_key_returns_401(client: TestClient) -> None:
    resp = client.get("/v1/tools", headers={"X-API-Key": "nope"})
    assert resp.status_code == 401


def test_free_key_rate_limit_429(client: TestClient) -> None:
    keymgr.reset_usage()
    # free limit is 5
    for _ in range(5):
        r = client.get("/v1/tools", headers=FREE_HEADERS)
        assert r.status_code == 200
    r = client.get("/v1/tools", headers=FREE_HEADERS)
    assert r.status_code == 429
    detail = r.json()["detail"]
    assert "mcpize.com/outdooriq-mcp" in str(detail)


def test_pro_key_unlimited(client: TestClient) -> None:
    keymgr.reset_usage()
    for _ in range(20):
        r = client.get("/v1/tools", headers=PRO_HEADERS)
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Tool: search_lakes / get_lake_details
# ---------------------------------------------------------------------------

def test_search_lakes_by_state(client: TestClient) -> None:
    resp = client.post(
        "/v1/tools/search_lakes",
        json={"state": "WI", "limit": 50},
        headers=PRO_HEADERS,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] >= 10
    assert all(l["state"] == "WI" for l in body["lakes"])


def test_search_lakes_acreage_filter(client: TestClient) -> None:
    resp = client.post(
        "/v1/tools/search_lakes",
        json={"min_acres": 10000, "limit": 50},
        headers=PRO_HEADERS,
    )
    assert resp.status_code == 200
    for lake in resp.json()["lakes"]:
        assert lake["acres"] >= 10000


def test_get_lake_details(client: TestClient) -> None:
    resp = client.post(
        "/v1/tools/get_lake_details",
        json={"lake_id": "lake-001"},
        headers=PRO_HEADERS,
    )
    assert resp.status_code == 200
    lake = resp.json()["lake"]
    assert lake["name"] == "Lake Winnebago"
    assert "walleye" in lake["species"]
    assert lake["coordinates"]["lat"] == pytest.approx(44.0, rel=0.01)


def test_get_lake_details_unknown_returns_error(client: TestClient) -> None:
    resp = client.post(
        "/v1/tools/get_lake_details",
        json={"lake_id": "lake-does-not-exist"},
        headers=PRO_HEADERS,
    )
    assert resp.status_code == 200
    assert resp.json().get("error") == "lake_not_found"


# ---------------------------------------------------------------------------
# Tool: get_stocking_data / schedule / search_species
# ---------------------------------------------------------------------------

def test_stocking_data_for_lake(client: TestClient) -> None:
    resp = client.post(
        "/v1/tools/get_stocking_data",
        json={"lake_id": "lake-001", "limit": 10},
        headers=PRO_HEADERS,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] >= 1
    for ev in body["events"]:
        assert ev["lake_id"] == "lake-001"
        assert ev["count"] > 0


def test_stocking_schedule_state_month(client: TestClient) -> None:
    resp = client.post(
        "/v1/tools/get_stocking_schedule",
        json={"state": "MN", "limit": 25},
        headers=PRO_HEADERS,
    )
    assert resp.status_code == 200
    for ev in resp.json()["events"]:
        assert ev["state"] == "MN"


def test_search_species(client: TestClient) -> None:
    resp = client.post(
        "/v1/tools/search_species",
        json={"state": "WI"},
        headers=PRO_HEADERS,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] >= 1
    assert all(isinstance(s, str) for s in body["species"])


# ---------------------------------------------------------------------------
# Tool: scoring + nearby + top + report + weather
# ---------------------------------------------------------------------------

def test_fishing_score_buckets(client: TestClient) -> None:
    resp = client.post(
        "/v1/tools/get_fishing_score",
        json={"lake_id": "lake-001"},
        headers=PRO_HEADERS,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert 0 <= body["fishing_score"] <= 100
    bd = body["breakdown"]
    assert sum(bd.values()) == body["fishing_score"]


def test_nearby_lakes_radius_filter(client: TestClient) -> None:
    # Chicago coords
    resp = client.post(
        "/v1/tools/get_nearby_lakes",
        json={"lat": 41.88, "lng": -87.63, "radius_miles": 150, "limit": 10},
        headers=PRO_HEADERS,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] >= 1
    assert all(l["distance_miles"] <= 150 for l in body["lakes"])
    # sorted by score desc
    scores = [l["fishing_score"] for l in body["lakes"]]
    assert scores == sorted(scores, reverse=True)


def test_top_lakes_filtered_by_state_and_species(client: TestClient) -> None:
    resp = client.post(
        "/v1/tools/get_top_lakes",
        json={"state": "WI", "species": "walleye", "limit": 5},
        headers=PRO_HEADERS,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] >= 1
    for lake in body["lakes"]:
        assert lake["state"] == "WI"
        assert "walleye" in lake["species"]


def test_weather_for_lake(client: TestClient) -> None:
    resp = client.post(
        "/v1/tools/get_weather_for_lake",
        json={"lake_id": "lake-001"},
        headers=PRO_HEADERS,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is True
    assert body["current"]["temperature_2m"] == 65


def test_fishing_report_summary(client: TestClient) -> None:
    resp = client.post(
        "/v1/tools/get_fishing_report_summary",
        json={"lake_id": "lake-001"},
        headers=PRO_HEADERS,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "Lake Winnebago" in body["summary"]
    assert body["outlook"] in {"excellent", "very good", "good", "fair", "slow"}


# ---------------------------------------------------------------------------
# MCP JSON-RPC
# ---------------------------------------------------------------------------

def test_mcp_initialize(client: TestClient) -> None:
    resp = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "initialize"},
        headers=PRO_HEADERS,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["result"]["serverInfo"]["name"] == "OutdoorIQ MCP"


def test_mcp_tools_list(client: TestClient) -> None:
    resp = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        headers=PRO_HEADERS,
    )
    assert resp.status_code == 200
    tools = resp.json()["result"]["tools"]
    names = {t["name"] for t in tools}
    expected = {
        "search_lakes", "get_lake_details", "get_stocking_data",
        "get_fishing_score", "get_nearby_lakes", "get_weather_for_lake",
        "get_top_lakes", "get_stocking_schedule", "search_species",
        "get_fishing_report_summary",
    }
    assert expected.issubset(names)


def test_mcp_tools_call_search_lakes(client: TestClient) -> None:
    resp = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "search_lakes", "arguments": {"state": "MO", "limit": 5}},
        },
        headers=PRO_HEADERS,
    )
    assert resp.status_code == 200
    result = resp.json()["result"]
    assert result["isError"] is False
    structured = result["structuredContent"]
    assert structured["count"] >= 1
    assert all(l["state"] == "MO" for l in structured["lakes"])


def test_mcp_tools_call_unknown_returns_jsonrpc_error(client: TestClient) -> None:
    resp = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "definitely_not_a_tool", "arguments": {}},
        },
        headers=PRO_HEADERS,
    )
    assert resp.status_code == 200
    assert "error" in resp.json()
    assert resp.json()["error"]["code"] == -32601


# ---------------------------------------------------------------------------
# Algorithm unit tests
# ---------------------------------------------------------------------------

def test_score_recent_stocking_bucket() -> None:
    now = time.time()
    lake = {"acres": 1000}
    stockings_recent = [{"species": "walleye", "stocking_date": now - 86400 * 10}]
    stockings_old = [{"species": "walleye", "stocking_date": now - 86400 * 200}]
    s_recent = scoring_tools.compute_fishing_score(lake, stockings_recent, {})
    s_old = scoring_tools.compute_fishing_score(lake, stockings_old, {})
    # same lake/species, only recency differs → recent must beat old by >=20
    assert s_recent - s_old >= 20


def test_score_weather_bucket() -> None:
    lake = {"acres": 1000}
    stockings = [
        {"species": "walleye", "stocking_date": time.time() - 86400 * 10},
    ]
    perfect = {"current": {"temperature_2m": 65, "precipitation": 0}}
    bad = {"current": {"temperature_2m": 95, "precipitation": 1.0}}
    assert (
        scoring_tools.compute_fishing_score(lake, stockings, perfect)
        > scoring_tools.compute_fishing_score(lake, stockings, bad)
    )


def test_score_capped_at_100() -> None:
    now = time.time()
    lake = {"acres": 100000}
    stockings = [
        {"species": s, "stocking_date": now - 86400}
        for s in ("walleye", "bass", "musky", "trout", "perch", "crappie")
    ]
    weather = {"current": {"temperature_2m": 65, "precipitation": 0}}
    assert scoring_tools.compute_fishing_score(lake, stockings, weather) == 100


# ---------------------------------------------------------------------------
# Postgres dispatch path — verify with mocked pool
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_postgres_mode_dispatches_to_pg_pool(monkeypatch) -> None:
    """Reset state, install a fake asyncpg pool, then verify search_lakes
    routes to the Postgres branch."""
    await dbconn.reset_for_tests()

    fake_rows = [
        {
            "id": "pg-001", "name": "PG Lake", "state": "WI", "county": "Test",
            "lat": 44.0, "lng": -88.0, "acres": 1000.0, "max_depth_ft": 30.0,
            "facilities": '["boat_ramp"]',
        }
    ]
    species_rows = [{"lake_id": "pg-001", "species": "walleye"}]

    # Fake connection used inside the pool's `async with acquire():`
    class FakeConn:
        async def fetchval(self, *_):
            return 1

        async def fetch(self, query, *params):
            if "lake_species" in query:
                return [type("R", (), {"__getitem__": lambda self, k: species_rows[0][k],
                                       "keys": lambda self: list(species_rows[0].keys())})()]
            return [type("R", (), {"__getitem__": lambda self, k: fake_rows[0][k],
                                   "keys": lambda self: list(fake_rows[0].keys())})()]

        async def fetchrow(self, query, *params):
            return None

    class _AcquireCtx:
        async def __aenter__(self):
            return FakeConn()
        async def __aexit__(self, *exc):
            return False

    class FakePool:
        def acquire(self):
            return _AcquireCtx()

        async def close(self):
            pass

    fake_asyncpg = MagicMock()
    fake_asyncpg.create_pool = AsyncMock(return_value=FakePool())

    monkeypatch.setenv("DATABASE_URL", "postgresql://fake/fake")
    monkeypatch.setattr(dbconn, "asyncpg", fake_asyncpg)

    mode = await dbconn.init_db()
    assert mode == "postgres"
    assert dbconn.is_sqlite_mode() is False

    rows = await dbconn.search_lakes(state="WI", limit=5)
    assert len(rows) == 1
    assert rows[0]["id"] == "pg-001"
    # species hydration ran
    assert "walleye" in rows[0]["species"]

    await dbconn.shutdown_db()


# ---------------------------------------------------------------------------
# Counts: prove we registered all 10 tools
# ---------------------------------------------------------------------------

def test_registry_has_all_ten_tools() -> None:
    assert len(server.TOOL_REGISTRY) == 10
    names = {t["name"] for t in server.TOOL_REGISTRY}
    assert names == {
        "search_lakes", "get_lake_details", "get_stocking_data",
        "get_fishing_score", "get_nearby_lakes", "get_weather_for_lake",
        "get_top_lakes", "get_stocking_schedule", "search_species",
        "get_fishing_report_summary",
    }
