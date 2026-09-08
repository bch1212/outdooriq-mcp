#!/usr/bin/env bash
# OutdoorIQ MCP — Railway deploy script.
# Run this on YOUR Mac, not inside Cowork. The Cowork sandbox can't reach
# Railway/Stripe/Cloudflare APIs.
#
# Prereqs:
#   - Railway CLI installed:   brew install railway
#   - RAILWAY_API_TOKEN exported (or RAILWAY_TOKEN copied to RAILWAY_API_TOKEN —
#     Railway CLI rejects when both are set, so unset RAILWAY_TOKEN after copy).
#   - Optional: CASTIQ_DATABASE_URL exported if you want Postgres mode.

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="${RAILWAY_PROJECT_NAME:-outdooriq-mcp}"
SHARED_ENV="${PROJECT_DIR}/../.deploy-secrets.env"

# ---------------------------------------------------------------------------
# 1) Inherit shared secrets if available
# ---------------------------------------------------------------------------
if [[ -f "$SHARED_ENV" ]]; then
    echo "→ Loading shared secrets from $SHARED_ENV"
    set -a
    # shellcheck disable=SC1090
    source "$SHARED_ENV"
    set +a
fi

# Railway CLI is exclusive: if both RAILWAY_TOKEN and RAILWAY_API_TOKEN are
# set it will refuse to run. Promote the shared one and unset the other.
if [[ -n "${RAILWAY_TOKEN:-}" && -z "${RAILWAY_API_TOKEN:-}" ]]; then
    export RAILWAY_API_TOKEN="$RAILWAY_TOKEN"
fi
unset RAILWAY_TOKEN

if [[ -z "${RAILWAY_API_TOKEN:-}" ]]; then
    echo "ERROR: RAILWAY_API_TOKEN not set. Export it (or RAILWAY_TOKEN) before running." >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# 2) Verify CLI
# ---------------------------------------------------------------------------
if ! command -v railway >/dev/null 2>&1; then
    echo "ERROR: railway CLI not found. Install with: brew install railway" >&2
    exit 1
fi

cd "$PROJECT_DIR"

# ---------------------------------------------------------------------------
# 3) Init / link project
# ---------------------------------------------------------------------------
if [[ ! -f .railway/project.json && ! -f .railway.json ]]; then
    echo "→ Initializing Railway project: $PROJECT_NAME"
    railway init --name "$PROJECT_NAME" || true
fi

# ---------------------------------------------------------------------------
# 4) Set service env vars
# ---------------------------------------------------------------------------
echo "→ Setting environment variables"

set_var() {
    local key="$1"
    local val="$2"
    if [[ -n "$val" ]]; then
        railway variables --set "$key=$val" >/dev/null
        echo "   $key set"
    fi
}

# Postgres-mode CastIQ DB (optional — leave unset to force SQLite fallback)
set_var DATABASE_URL "${CASTIQ_DATABASE_URL:-}"

# Pro keys (comma-separated key:plan, e.g. abc123:pro,xyz789:pro)
set_var OUTDOORIQ_EXTRA_KEYS "${OUTDOORIQ_EXTRA_KEYS:-}"

# Override the dev key if you don't want the public default
set_var OUTDOORIQ_DEV_KEY "${OUTDOORIQ_DEV_KEY:-outdooriq-dev-key-001}"

# Free-tier daily call budget
set_var OUTDOORIQ_FREE_DAILY_LIMIT "${OUTDOORIQ_FREE_DAILY_LIMIT:-50}"

# ---------------------------------------------------------------------------
# 5) Deploy
# ---------------------------------------------------------------------------
echo "→ Deploying via nixpacks (start: python -m run)"
railway up --detach

# ---------------------------------------------------------------------------
# 6) Domain hookup hint
# ---------------------------------------------------------------------------
echo
echo "Deploy submitted. Tail logs with:    railway logs"
echo "Add the canonical custom domain:     railway domain mcp.castiq.net --service web"
echo "Smoke check:                         curl https://<your-railway-url>/health"
