"""API key registry + per-day rate limiting (in-memory).

Configuration:
- The dev/free key is always loaded (default `outdooriq-dev-key-001`),
  with a daily call budget of 50.
- Pro keys can be configured via env: OUTDOORIQ_EXTRA_KEYS=key1:pro,key2:pro
- For local testing, OUTDOORIQ_DEV_KEY overrides the dev key string.

Usage tracking is per-process; deploy a single Railway replica or move to
Redis if you scale horizontally.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class KeyInfo:
    key: str
    plan: str  # "free" | "pro"
    daily_limit: Optional[int]  # None = unlimited
    name: str = "anonymous"


@dataclass
class UsageBucket:
    day: str
    count: int = 0


_keys: dict[str, KeyInfo] = {}
_usage: dict[str, UsageBucket] = {}


def _today() -> str:
    return time.strftime("%Y-%m-%d", time.gmtime())


def load_keys_from_env() -> None:
    """(Re)load key registry from environment. Idempotent."""
    _keys.clear()

    dev_key = os.getenv("OUTDOORIQ_DEV_KEY", "outdooriq-dev-key-001")
    free_limit = int(os.getenv("OUTDOORIQ_FREE_DAILY_LIMIT", "50"))
    _keys[dev_key] = KeyInfo(key=dev_key, plan="free", daily_limit=free_limit, name="dev")

    extra = os.getenv("OUTDOORIQ_EXTRA_KEYS", "")
    for chunk in extra.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if ":" in chunk:
            k, plan = chunk.split(":", 1)
            plan = plan.strip().lower()
        else:
            k, plan = chunk, "pro"
        k = k.strip()
        limit = None if plan == "pro" else free_limit
        _keys[k] = KeyInfo(key=k, plan=plan, daily_limit=limit, name=plan)


def register_key(key: str, plan: str = "pro", daily_limit: Optional[int] = None) -> KeyInfo:
    """Programmatic registration (used by tests)."""
    info = KeyInfo(key=key, plan=plan, daily_limit=daily_limit, name=plan)
    _keys[key] = info
    return info


def lookup(key: str) -> Optional[KeyInfo]:
    return _keys.get(key)


def reset_usage() -> None:
    _usage.clear()


def record_call(key: str) -> None:
    today = _today()
    bucket = _usage.get(key)
    if bucket is None or bucket.day != today:
        _usage[key] = UsageBucket(day=today, count=1)
    else:
        bucket.count += 1


def usage_today(key: str) -> int:
    bucket = _usage.get(key)
    if bucket is None or bucket.day != _today():
        return 0
    return bucket.count


def is_over_limit(info: KeyInfo) -> bool:
    if info.daily_limit is None:
        return False
    return usage_today(info.key) >= info.daily_limit
