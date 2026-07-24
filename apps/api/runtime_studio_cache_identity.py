from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

from fastapi import Request

from apps.api.runtime_auth_security import bearer_token


CACHE_IDENTITY_SCHEMA_VERSION = "afs.studio_cache_identity.v0.1"


def studio_cache_identity(
    request: Request,
    *,
    user_id: str,
    project_id: str,
    state_version: str,
    state: dict[str, Any],
) -> dict[str, str]:
    token = bearer_token(request.headers.get("authorization", ""))
    if not token or not user_id or not project_id or not isinstance(state, dict):
        return {}
    state_sha256 = hashlib.sha256(_canonical_json(state).encode("utf-8")).hexdigest()
    message = _identity_message(
        user_id=user_id,
        project_id=project_id,
        state_version=state_version,
        state_sha256=state_sha256,
    )
    proof = hmac.new(token.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()
    return {
        "schema_version": CACHE_IDENTITY_SCHEMA_VERSION,
        "account_id": user_id,
        "project_id": project_id,
        "state_version": state_version,
        "state_sha256": state_sha256,
        "proof": proof,
    }


def _identity_message(*, user_id: str, project_id: str, state_version: str, state_sha256: str) -> str:
    return "\x1f".join((
        CACHE_IDENTITY_SCHEMA_VERSION,
        user_id,
        project_id,
        state_version,
        state_sha256,
    ))


def _canonical_json(value: Any) -> str:
    return json.dumps(_canonical_value(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _canonical_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _canonical_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_canonical_value(item) for item in value]
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


__all__ = ("CACHE_IDENTITY_SCHEMA_VERSION", "studio_cache_identity")
