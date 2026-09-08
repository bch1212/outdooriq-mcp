"""OutdoorIQ MCP Server.

A paid MCP server exposing fishing intelligence — lake search, stocking
events, fishing-favorability scoring, and outdoor recreation conditions.

Surfaces:
- POST /mcp     — MCP JSON-RPC HTTP transport (initialize, tools/list, tools/call)
- GET  /        — banner / pricing
- GET  /health  — liveness + DB mode
- REST routes  — one per tool, useful for direct testing

Auth:
- All `/mcp` and `/v1/*` routes require an `X-API-Key` header.
- Free key (`outdooriq-dev-key-001` by default) gets 50 calls/day.
- Pro keys are unlimited.
"""
from __future__ import annotations

import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Awaitable, Callable, Optional

from fastapi import Body, Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from db import connection as dbconn
from db import keys as keymgr
from tools import lakes as lake_tools
from tools import reports as report_tools
from tools import scoring as scoring_tools
from tools import stocking as stocking_tools
from tools import weather as weather_tools

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
log = logging.getLogger("outdooriq.server")

VERSION = "0.1.0"
SERVER_NAME = "OutdoorIQ MCP"

# ---------------------------------------------------------------------------
# fastmcp registration (best-effort — versions vary)
# ---------------------------------------------------------------------------
try:
    from fastmcp import FastMCP  # type: ignore

    mcp = FastMCP(SERVER_NAME)
    _FASTMCP_AVAILABLE = True
except Exception as _exc:  # pragma: no cover - keeps server up on version drift
    log.warning("fastmcp import failed (%s); MCP JSON-RPC still served manually", _exc)
    mcp = None  # type: ignore
    _FASTMCP_AVAILABLE = False


# ---------------------------------------------------------------------------
# Tool registry — single source of truth.
# Each entry: (name, description, json_schema, async callable)
# ---------------------------------------------------------------------------
TOOL_REGISTRY: list[dict[str, Any]] = [
    {
        "name": "search_lakes",
        "description": "Search lakes by name, state, county, and acreage range.",
        "schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "state": {"type": "string", "description": "Two-letter state code (e.g., 'WI')"},
                "county": {"type": "string"},
                "min_acres": {"type": "number"},
                "max_acres": {"type": "number"},
                "limit": {"type": "integer", "default": 25, "maximum": 200},
            },
            "additionalProperties": False,
        },
        "fn": lake_tools.search_lakes,
    },
    {
        "name": "get_lake_details",
        "description": "Fetch full details for a single lake (coords, acreage, depth, species, facilities).",
        "schema": {
            "type": "object",
            "properties": {"lake_id": {"type": "string"}},
            "required": ["lake_id"],
            "additionalProperties": False,
        },
        "fn": lake_tools.get_lake_details,
    },
    {
        "name": "get_stocking_data",
        "description": "Recent stocking events for a lake (filter by species/year).",
        "schema": {
            "type": "object",
            "properties": {
                "lake_id": {"type": "string"},
                "species": {"type": "string"},
                "year": {"type": "integer"},
                "limit": {"type": "integer", "default": 25, "maximum": 500},
            },
            "additionalProperties": False,
        },
        "fn": stocking_tools.get_stocking_data,
    },
    {
        "name": "get_fishing_score",
        "description": "Compute a 0-100 fishing-favorability score for a lake with breakdown.",
        "schema": {
            "type": "object",
            "properties": {"lake_id": {"type": "string"}},
            "required": ["lake_id"],
            "additionalProperties": False,
        },
        "fn": scoring_tools.get_fishing_score,
    },
    {
        "name": "get_nearby_lakes",
        "description": "Lakes near a GPS coordinate, sorted by fishing score.",
        "schema": {
            "type": "object",
            "properties": {
                "lat": {"type": "number"},
                "lng": {"type": "number"},
                "radius_miles": {"type": "number", "default": 25},
                "min_score": {"type": "integer", "default": 0},
                "limit": {"type": "integer", "default": 20, "maximum": 100},
            },
            "required": ["lat", "lng"],
            "additionalProperties": False,
        },
        "fn": lake_tools.get_nearby_lakes,
    },
    {
        "name": "get_weather_for_lake",
        "description": "Current conditions + 7-day forecast at a lake (Open-Meteo).",
        "schema": {
            "type": "object",
            "properties": {"lake_id": {"type": "string"}},
            "required": ["lake_id"],
            "additionalProperties": False,
        },
        "fn": weather_tools.get_weather_for_lake,
    },
    {
        "name": "get_top_lakes",
        "description": "Highest-scoring lakes for a state and/or species.",
        "schema": {
            "type": "object",
            "properties": {
                "state": {"type": "string"},
                "species": {"type": "string"},
                "limit": {"type": "integer", "default": 10, "maximum": 50},
            },
            "additionalProperties": False,
        },
        "fn": lake_tools.get_top_lakes,
    },
    {
        "name": "get_stocking_schedule",
        "description": "Most-recent stocking activity matching state/species/month — agents use this as a planning prior.",
        "schema": {
            "type": "object",
            "properties": {
                "state": {"type": "string"},
                "species": {"type": "string"},
                "month": {"type": "integer", "minimum": 1, "maximum": 12},
                "limit": {"type": "integer", "default": 50, "maximum": 200},
            },
            "additionalProperties": False,
        },
        "fn": stocking_tools.get_stocking_schedule,
    },
    {
        "name": "search_species",
        "description": "List actively-stocked species in a state (optionally filtered by season).",
        "schema": {
            "type": "object",
            "properties": {
                "state": {"type": "string"},
                "season": {"type": "string"},
            },
            "additionalProperties": False,
        },
        "fn": stocking_tools.search_species,
    },
    {
        "name": "get_fishing_report_summary",
        "description": "Natural-language fishing report for a lake.",
        "schema": {
            "type": "object",
            "properties": {"lake_id": {"type": "string"}},
            "required": ["lake_id"],
            "additionalProperties": False,
        },
        "fn": report_tools.get_fishing_report_summary,
    },
]


def _tool_by_name(name: str) -> Optional[dict[str, Any]]:
    for t in TOOL_REGISTRY:
        if t["name"] == name:
            return t
    return None


# Register with fastmcp if available
if _FASTMCP_AVAILABLE and mcp is not None:
    for tool in TOOL_REGISTRY:
        try:
            mcp.tool(name=tool["name"], description=tool["description"])(tool["fn"])
        except Exception as exc:  # pragma: no cover
            log.warning("fastmcp tool registration failed for %s: %s", tool["name"], exc)


# ---------------------------------------------------------------------------
# Lifespan: init DB on startup, close on shutdown
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    keymgr.load_keys_from_env()
    await dbconn.init_db()
    log.info("[OutdoorIQ] %s ready (mode=%s)", SERVER_NAME, dbconn.get_mode())
    yield
    await dbconn.shutdown_db()


app = FastAPI(title=SERVER_NAME, version=VERSION, lifespan=lifespan)


# ---------------------------------------------------------------------------
# Auth dependency
# ---------------------------------------------------------------------------
def require_api_key(x_api_key: Optional[str] = Header(default=None)) -> keymgr.KeyInfo:
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header.")
    info = keymgr.lookup(x_api_key)
    if info is None:
        raise HTTPException(status_code=401, detail="Invalid API key.")
    if keymgr.is_over_limit(info):
        raise HTTPException(
            status_code=429,
            detail={"error": "Upgrade at mcpize.com/outdooriq-mcp"},
        )
    keymgr.record_call(info.key)
    return info


# ---------------------------------------------------------------------------
# Public banner + health
# ---------------------------------------------------------------------------
@app.get("/", response_class=PlainTextResponse)
async def banner() -> str:
    return (
        f"{SERVER_NAME} v{VERSION}\n"
        "Powered by 72,000+ US lakes and 293,000+ stocking events across 12 states.\n"
        "Pricing: $14/mo Pro or $0.01/call.\n"
        "Listing: https://mcpize.com/outdooriq-mcp\n"
        "Install: claude mcp add outdooriq-mcp --url https://mcp.castiq.net/mcp\n"
    )


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "ok": True,
        "version": VERSION,
        "db_mode": dbconn.get_mode(),
        "fastmcp": _FASTMCP_AVAILABLE,
        "tool_count": len(TOOL_REGISTRY),
    }


# ---------------------------------------------------------------------------
# REST routes — one per tool
# ---------------------------------------------------------------------------
async def _invoke(tool_name: str, args: dict[str, Any]) -> Any:
    tool = _tool_by_name(tool_name)
    if tool is None:
        raise HTTPException(status_code=404, detail=f"Unknown tool: {tool_name}")
    try:
        return await tool["fn"](**(args or {}))
    except TypeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/v1/tools/{tool_name}")
async def invoke_tool(
    tool_name: str,
    body: dict[str, Any] = Body(default_factory=dict),
    _info: keymgr.KeyInfo = Depends(require_api_key),
) -> Any:
    return await _invoke(tool_name, body or {})


@app.get("/v1/tools")
async def list_tools(_info: keymgr.KeyInfo = Depends(require_api_key)) -> dict[str, Any]:
    return {
        "count": len(TOOL_REGISTRY),
        "tools": [
            {
                "name": t["name"],
                "description": t["description"],
                "input_schema": t["schema"],
            }
            for t in TOOL_REGISTRY
        ],
    }


# ---------------------------------------------------------------------------
# MCP JSON-RPC endpoint
# ---------------------------------------------------------------------------
def _jsonrpc_error(req_id: Any, code: int, message: str, data: Any = None) -> dict:
    err: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": req_id, "error": err}


def _jsonrpc_result(req_id: Any, result: Any) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


@app.post("/mcp")
async def mcp_endpoint(
    request: Request,
    _info: keymgr.KeyInfo = Depends(require_api_key),
) -> JSONResponse:
    """MCP JSON-RPC over HTTP transport.

    Supports `initialize`, `tools/list`, `tools/call`, `ping`. Single-request
    only (no streaming SSE) — sufficient for `claude mcp add --url`-style
    clients that speak JSON-RPC.
    """
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(_jsonrpc_error(None, -32700, "Parse error"))
    if isinstance(payload, list):
        # batch
        out = [await _handle_jsonrpc(p) for p in payload]
        return JSONResponse(out)
    return JSONResponse(await _handle_jsonrpc(payload))


async def _handle_jsonrpc(payload: dict[str, Any]) -> dict[str, Any]:
    req_id = payload.get("id")
    method = payload.get("method")
    params = payload.get("params") or {}

    if method == "initialize":
        return _jsonrpc_result(
            req_id,
            {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": SERVER_NAME, "version": VERSION},
                "capabilities": {"tools": {"listChanged": False}},
            },
        )

    if method == "ping":
        return _jsonrpc_result(req_id, {})

    if method == "tools/list":
        return _jsonrpc_result(
            req_id,
            {
                "tools": [
                    {
                        "name": t["name"],
                        "description": t["description"],
                        "inputSchema": t["schema"],
                    }
                    for t in TOOL_REGISTRY
                ]
            },
        )

    if method == "tools/call":
        name = params.get("name")
        args = params.get("arguments") or {}
        tool = _tool_by_name(name) if name else None
        if tool is None:
            return _jsonrpc_error(req_id, -32601, f"Unknown tool: {name}")
        try:
            result = await tool["fn"](**args)
        except TypeError as exc:
            return _jsonrpc_error(req_id, -32602, f"Invalid params: {exc}")
        except Exception as exc:  # noqa: BLE001
            return _jsonrpc_error(req_id, -32000, f"Tool error: {exc}")
        return _jsonrpc_result(
            req_id,
            {
                "content": [
                    {"type": "text", "text": json.dumps(result, default=str)}
                ],
                "isError": False,
                "structuredContent": result,
            },
        )

    return _jsonrpc_error(req_id, -32601, f"Method not found: {method}")


# ---------------------------------------------------------------------------
# CLI entry (only for local dev — Railway uses run.py)
# ---------------------------------------------------------------------------
if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run(
        "server:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8080")),
        reload=False,
    )
