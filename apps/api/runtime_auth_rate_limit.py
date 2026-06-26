from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from agentflow.harness.json_io import write_json
from apps.api.runtime_auth_security import hash_text, now, parse_datetime
from apps.api.runtime_store import read_json


AUTH_RATE_LIMIT_MAX_FAILURES_ENV = "AFS_AUTH_RATE_LIMIT_MAX_FAILURES"
AUTH_RATE_LIMIT_WINDOW_SECONDS_ENV = "AFS_AUTH_RATE_LIMIT_WINDOW_SECONDS"
AUTH_RATE_LIMIT_LOCK_SECONDS_ENV = "AFS_AUTH_RATE_LIMIT_LOCK_SECONDS"
DEFAULT_MAX_FAILURES = 5
DEFAULT_WINDOW_SECONDS = 900
DEFAULT_LOCK_SECONDS = 900


def enforce_auth_rate_limit(
    path: Path,
    *,
    scope: str,
    client_ip: str,
    identifier: str,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    policy = rate_limit_policy(env)
    if policy["max_failures"] <= 0:
        return {"limited": False}
    state = _state(path)
    bucket = state["buckets"].get(_key(scope, client_ip, identifier), {})
    locked_until = parse_datetime(str(bucket.get("locked_until", "")))
    current = parse_datetime(now())
    if locked_until and current and locked_until > current:
        raise HTTPException(status_code=429, detail="too many authentication attempts; retry later")
    return {"limited": False}


def record_auth_failure(
    path: Path,
    *,
    scope: str,
    client_ip: str,
    identifier: str,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    policy = rate_limit_policy(env)
    if policy["max_failures"] <= 0:
        return {"status": "disabled", "failure_count": 0}
    state = _state(path)
    key = _key(scope, client_ip, identifier)
    bucket = dict(state["buckets"].get(key) or {})
    current = parse_datetime(now())
    first_failed_at = parse_datetime(str(bucket.get("first_failed_at", "")))
    if not current or not first_failed_at or current - first_failed_at > timedelta(seconds=policy["window_seconds"]):
        bucket = {"first_failed_at": now(), "failure_count": 0, "locked_until": ""}
    bucket["failure_count"] = int(bucket.get("failure_count") or 0) + 1
    if bucket["failure_count"] >= policy["max_failures"] and current:
        bucket["locked_until"] = (current + timedelta(seconds=policy["lock_seconds"])).isoformat()
    bucket["last_failed_at"] = now()
    state["buckets"][key] = bucket
    write_json(path, state)
    return {"status": "recorded", "failure_count": bucket["failure_count"], "locked_until": bucket.get("locked_until", "")}


def clear_auth_failures(path: Path, *, scope: str, client_ip: str, identifier: str) -> None:
    state = _state(path)
    if state["buckets"].pop(_key(scope, client_ip, identifier), None) is not None:
        write_json(path, state)


def rate_limit_policy(env: dict[str, str] | None = None) -> dict[str, int]:
    values = env if env is not None else os.environ
    return {
        "max_failures": _int_env(values.get(AUTH_RATE_LIMIT_MAX_FAILURES_ENV), DEFAULT_MAX_FAILURES),
        "window_seconds": _int_env(values.get(AUTH_RATE_LIMIT_WINDOW_SECONDS_ENV), DEFAULT_WINDOW_SECONDS),
        "lock_seconds": _int_env(values.get(AUTH_RATE_LIMIT_LOCK_SECONDS_ENV), DEFAULT_LOCK_SECONDS),
    }


def _state(path: Path) -> dict[str, Any]:
    if path.exists():
        try:
            payload = read_json(path)
        except (OSError, ValueError):
            payload = {}
    else:
        payload = {}
    buckets = payload.get("buckets")
    if not isinstance(buckets, dict):
        buckets = {}
    return {"schema_version": "0.1.0", "buckets": buckets}


def _key(scope: str, client_ip: str, identifier: str) -> str:
    folded = f"{scope}:{client_ip}:{identifier}".strip().lower()
    return f"{scope}:{hash_text(folded)[:24]}"


def _int_env(value: str | None, default: int) -> int:
    try:
        parsed = int(str(value or "").strip())
    except ValueError:
        return default
    return max(0, parsed)


__all__ = (
    "AUTH_RATE_LIMIT_LOCK_SECONDS_ENV",
    "AUTH_RATE_LIMIT_MAX_FAILURES_ENV",
    "AUTH_RATE_LIMIT_WINDOW_SECONDS_ENV",
    "clear_auth_failures",
    "enforce_auth_rate_limit",
    "record_auth_failure",
)
