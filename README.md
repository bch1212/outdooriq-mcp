# OutdoorIQ MCP — Outdoor Recreation Intelligence

> **Powered by 72,000+ US lakes and 293,000+ stocking events across 12 states.**

OutdoorIQ MCP is a paid MCP server that exposes lake conditions, fish-stocking
records, fishing-favorability scoring, and live weather to AI agents. It is
built on the CastIQ dataset (the same data that powers
[fishing-seo.pages.dev](https://fishing-seo.pages.dev) and the CastIQ catalog
APIs).

If you're building a **trip-planning assistant**, a **fishing app**, a
**travel concierge**, or an **outdoor-brand agent** that needs to recommend
lakes, time visits to recent stocking events, or pull a fishing report on
demand, this is the data layer you wire up.

For consumer-facing AI products, OutdoorIQ replaces a ten-source ETL with one
authenticated MCP endpoint — and bills predictably so you don't get a surprise
S3 invoice the first weekend traffic spikes.

---

## Pricing

| Tier  | Price        | Limits                            |
|-------|--------------|-----------------------------------|
| Free  | $0           | `outdooriq-dev-key-001`, 50 calls/day |
| Pro   | **$14/mo**   | Unlimited                         |
| Pay-as-you-go | **$0.01/call** | No monthly minimum         |

Listing & checkout: <https://mcpize.com/outdooriq-mcp>

---

## Install in Claude

**Live URL:** `https://mcp.castiq.net/mcp` (Railway fallback: `https://web-production-9b8950.up.railway.app/mcp`)

The fastest path uses [`mcp-remote`](https://github.com/geelen/mcp-remote) as a stdio→HTTP bridge:

```bash
claude mcp add outdooriq-mcp -- npx -y mcp-remote \
  https://mcp.castiq.net/mcp \
  --header "X-API-Key:outdooriq-dev-key-001"
```

Or configure manually:

```json
{
  "mcpServers": {
    "outdooriq-mcp": {
      "url": "https://mcp.castiq.net/mcp",
      "headers": { "X-API-Key": "outdooriq-dev-key-001" }
    }
  }
}
```

**Anthropic MCP Registry entry:** `io.github.bch1212/outdooriq-mcp` —
listed at <https://registry.modelcontextprotocol.io>.

**Example agent prompt:**
> "Find top 5 trout lakes near Chicago for this weekend."

The agent calls `get_nearby_lakes` (lat/lng of Chicago, radius 200mi),
filters for `species: trout` via `get_top_lakes`, then pulls
`get_fishing_report_summary` for the top match.

---

## Tool Reference

| Tool | Args | Returns |
|------|------|---------|
| `search_lakes` | `name?, state?, county?, min_acres?, max_acres?, limit?` | List of matching lakes |
| `get_lake_details` | `lake_id` | Coords, acreage, depth, species, facilities |
| `get_stocking_data` | `lake_id?, species?, year?, limit?` | Recent stocking events |
| `get_fishing_score` | `lake_id` | 0-100 score with bucket breakdown |
| `get_nearby_lakes` | `lat, lng, radius_miles?, min_score?, limit?` | Lakes near GPS, sorted by score |
| `get_weather_for_lake` | `lake_id` | Current + 7-day forecast (Open-Meteo) |
| `get_top_lakes` | `state?, species?, limit?` | Highest-scoring lakes |
| `get_stocking_schedule` | `state?, species?, month?, limit?` | Most-recent matching events as a planning prior |
| `search_species` | `state?, season?` | Actively-stocked species |
| `get_fishing_report_summary` | `lake_id` | Natural-language report |

---

## Architecture

```
client (Claude / agent)
        │  HTTP POST /mcp  (JSON-RPC 2.0)
        ▼
   FastAPI app (server.py)
        │  X-API-Key auth + per-day rate limiter
        ▼
  Tool registry (10 tools)
        │
        ▼
  db.connection.py  ──────┐
        │ Postgres mode  │  → CastIQ Postgres (72k lakes, 293k stockings)
        │ SQLite fallback│  → bundled seed (100+ lakes, ~150 stockings)
        ▼
  tools.* (lakes, stocking, scoring, weather, reports)
        │
        ▼
  Open-Meteo (no key)
```

### Postgres vs SQLite mode

The server picks a backend at startup:

1. If `DATABASE_URL` is set, it tries `asyncpg.create_pool`. On success →
   logs `[OutdoorIQ] Running in Postgres mode`.
2. If the pool fails (timeout, bad creds, DB down) **or** `DATABASE_URL` is
   unset, the server seeds an in-memory SQLite DB with 100+ real lakes and
   logs `[OutdoorIQ] Running in SQLite fallback mode`.

The server **always starts**, regardless of Postgres availability.

| Capability | Postgres mode | SQLite fallback |
|------------|--------------|-----------------|
| Lake catalog | 72,669 (12 states) | ~106 (WI, MN, IL, IA, MO) |
| Stocking events | 293,821 historical | ~150 templated, recency-tuned |
| Species coverage | All states/species in CastIQ | Curated subset (walleye, bass, musky, trout, crappie, perch, pike, panfish, salmon, lake_trout, sauger, white_bass, sturgeon, catfish, bluegill, smallmouth_bass) |
| Year-over-year analysis | Yes — multi-year stockings | Limited — events are anchored relative to "now" |
| Stocking-schedule tool | Real historical patterns | Approximated from seed |
| Weather, scoring, reports | Identical | Identical |

---

## Local development

```bash
git clone <this repo>
cd mcp-outdoors
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run with SQLite fallback (no DATABASE_URL needed)
python -m run

# OR run against the CastIQ Postgres
export DATABASE_URL=postgresql://vikinetic:vikinetic_dev@localhost:5444/vikinetic
python -m run
```

Then:

```bash
curl -s http://localhost:8080/health
curl -s -X POST http://localhost:8080/mcp \
  -H "X-API-Key: outdooriq-dev-key-001" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

### Tests

```bash
pytest -v
```

The test suite covers both the SQLite fallback path and the Postgres dispatch
path (via a mocked `asyncpg` pool), plus auth, rate limits, all 10 tools,
JSON-RPC initialize / list / call, and the scoring algorithm's bucket math.

---

## Deploy to Railway

A `deploy.sh` script is included at the repo root. Run it on your Mac (the
Cowork sandbox can't reach Railway/Stripe/Cloudflare APIs):

```bash
./deploy.sh
```

It expects `RAILWAY_API_TOKEN` (or `RAILWAY_TOKEN` exported as `RAILWAY_API_TOKEN`),
points the project at `nixpacks.toml`, and sets the `DATABASE_URL` env var if
you've also provisioned the CastIQ Postgres on Railway.

> **Railway gotcha (already handled):** Railway exec's `startCommand`
> without a shell, so `$PORT` doesn't expand. We use `python -m run` and read
> `PORT` from `os.environ` inside `run.py`.

---

## MCPize listing copy

> **OutdoorIQ MCP — the data layer for outdoor-rec AI agents.** 72,000+ US
> lakes, 293,000+ fish-stocking events, and live weather behind one
> authenticated endpoint. Search lakes by name, state, or acreage; pull
> stocking history filtered by species and month; compute a 0-100
> fishing-favorability score that bakes in recency, species diversity, lake
> size, and current conditions. One JSON-RPC call replaces a multi-source
> ETL.
>
> Built for fishing apps, trip-planning assistants, travel concierges, and
> outdoor-brand agents. $14/mo Pro for unlimited use, or pay $0.01 per call.
> Free dev tier (50 calls/day) lets you ship a prototype before opening your
> wallet. Install with `claude mcp add outdooriq-mcp --url
> https://mcp.castiq.net/mcp`.

---

## License

MIT. See `LICENSE`.
