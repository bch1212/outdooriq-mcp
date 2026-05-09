# OutdoorIQ MCP — Launch Posts (Brett owns timing)

Per the steady-state policy, Brett picks the day to send these. URLs are live now:

- Repo: https://github.com/bch1212/outdooriq-mcp
- Live MCP: https://mcp.castiq.net/mcp (Railway fallback: https://web-production-9b8950.up.railway.app/mcp)
- Anthropic MCP Registry entry: `io.github.bch1212/outdooriq-mcp`
- awesome-mcp-servers PR: https://github.com/punkpeye/awesome-mcp-servers/pull/6121

---

## 1. Show HN

**Title:** Show HN: OutdoorIQ MCP – fishing/lake intelligence for AI agents

**Body:**

I built OutdoorIQ, a paid MCP server that lets AI agents query US fishing data — lakes, fish-stocking events, and live conditions — through one endpoint instead of stitching together state DNR scrapers, weather APIs, and lake catalogs.

The dataset behind it: 72,669 lakes and 293,821 stocking events across 12 states, normalized from state agency feeds (the same data powering my CastIQ catalog).

10 tools, a few interesting ones:
- `get_fishing_score(lake_id)` — 0-100 score from recent stocking events, species diversity, lake size, and current weather. Bucket breakdown is returned so the agent can explain the score.
- `get_nearby_lakes(lat, lng, radius_miles)` — sorted by score, not just distance. Useful for "find me a good lake within 100 miles for tomorrow."
- `get_fishing_report_summary(lake_id)` — natural-language report combining the above.

Live HTTP MCP at https://mcp.castiq.net/mcp. Free tier (50 calls/day) with the dev key in the README; $14/mo Pro for unlimited or $0.01/call. Built on FastAPI + fastmcp + asyncpg with a SQLite fallback so the server stays up if the Postgres dataset blips.

Code: https://github.com/bch1212/outdooriq-mcp

Curious what other dataset shapes you'd want behind a similar paid-MCP wrapper — courts, permits, transit?

---

## 2. r/ClaudeAI / r/LocalLLaMA / r/mcp

**Title:** Built a paid MCP for fishing intelligence — 72k lakes, 293k stocking events, $14/mo

**Body:**

Sharing a new MCP I just shipped: **OutdoorIQ**, an HTTP MCP server for outdoor-rec AI agents.

The premise: trip-planning assistants and fishing apps need lake info, recent stocking events, and weather all together. Today that means three integrations and a lot of glue. OutdoorIQ collapses it to one endpoint with 10 tools.

**Install for Claude:**
```
claude mcp add outdooriq-mcp -- npx -y mcp-remote https://mcp.castiq.net/mcp --header "X-API-Key:outdooriq-dev-key-001"
```

That dev key is real and good for 50 calls/day — try it. Pro keys ($14/mo) unlock unlimited.

Sample agent prompt that hits 3 tools:
> "Find top 5 trout lakes near Chicago for this weekend, with conditions."

Live registry entry: https://registry.modelcontextprotocol.io (search "outdooriq")
Repo: https://github.com/bch1212/outdooriq-mcp

Open to feedback on which tool surfaces would matter most for your agent.

---

## 3. Product Hunt

**Tagline:** Outdoor recreation intelligence for AI agents — one MCP, 72,000+ lakes.

**Description:**

OutdoorIQ MCP gives any AI agent — Claude, GPT-based agents, custom tooling — instant access to US outdoor recreation data. 72,669 lakes, 293,821 fish-stocking events, live weather, and a 0-100 fishing-favorability score, all behind one authenticated MCP endpoint.

Built for trip-planning assistants, fishing apps, travel concierges, and outdoor-brand agents. $14/mo Pro for unlimited, free 50 calls/day for prototyping.

**First comment:**
Hey PH! Builder here. The "why now" for OutdoorIQ: every agentic outdoor app I see is duct-taping together state DNR feeds, OpenWeather, and Google Places. We aggregated those into the CastIQ pipeline a few months ago and now expose them as an MCP. One install, 10 tools, predictable pricing. Happy to answer anything.

---

## 4. Twitter / X

**Thread (5 tweets):**

1/ shipped OutdoorIQ today — paid MCP server for fishing/lake/outdoor data.

72,669 US lakes. 293,821 stocking events. 12 states.

one endpoint, 10 tools. install: `claude mcp add outdooriq-mcp --url https://mcp.castiq.net/mcp`

2/ the killer tool is `get_fishing_score(lake_id)` — 0-100 score that bakes in recent stocking, species diversity, lake size, and weather.

bucket breakdown returned so the agent can *explain* the score, not just rank.

3/ pricing: $14/mo Pro. or $0.01/call. or 50 free calls/day with the dev key in the README.

no auth dance, no signup wizard. paste a key, ship.

4/ stack: FastAPI + fastmcp + asyncpg + Open-Meteo. SQLite fallback if the Postgres dataset blips so the server is never down.

remote-only entry in @AnthropicAI's MCP registry: io.github.bch1212/outdooriq-mcp

5/ if you build trip planners, fishing apps, or outdoor agents — try it for free, tell me what's missing.

repo: https://github.com/bch1212/outdooriq-mcp

---

## 5. LinkedIn

**Headline:** Shipped OutdoorIQ — paid MCP for outdoor-rec AI agents

**Body:**

If you're building consumer-facing AI in the outdoor / travel / fishing space, integrating data is currently a slog: state DNR scraping, weather APIs, lake catalogs, GPS reverse-lookup, and gluing it all together yourself.

OutdoorIQ MCP collapses that to one authenticated endpoint:

→ 72,669 US lakes (12 states, normalized)
→ 293,821 fish-stocking events
→ Live weather + 7-day forecast
→ 0-100 fishing-favorability score with explainable bucket breakdown
→ 10 MCP tools, predictable pricing ($14/mo Pro)

Built on the same dataset that powers our CastIQ catalog. Live now at https://mcp.castiq.net/mcp.

Open source: https://github.com/bch1212/outdooriq-mcp

Looking for early integration partners — fishing-app teams, trip planners, outdoor-brand agents. DM if interested.

---

## 6. Discord (#mcp, #anthropic, fishing-tech servers)

Hey folks — just shipped OutdoorIQ, a paid HTTP MCP exposing US fishing/lake/stocking data to AI agents. 72k lakes, 293k events, 10 tools, $14/mo Pro.

Free dev key in the README (50 calls/day) for prototyping.

Install: `claude mcp add outdooriq-mcp --url https://mcp.castiq.net/mcp`
Repo: https://github.com/bch1212/outdooriq-mcp

Sample agent prompt: "Find top 5 trout lakes near Chicago for this weekend."

Feedback welcome.
