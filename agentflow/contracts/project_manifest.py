from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentflow.harness.constants import AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS

PROJECT_MANIFEST_ARTIFACT_TYPE = "agentflow_project_manifest"
PROJECT_MANIFEST_SCHEMA_VERSION = "0.1.0"
PROJECT_MANIFEST_STATUSES = frozenset({"in_progress", "blocked", "ready_for_next_round"})
PROJECT_MANIFEST_REF_LIST_FIELDS = (
    "source_assets",
    "runs",
    "packages",
    "feedback_refs",
    "profile_version_refs",
)
UNSAFE_PROJECT_MANIFEST_FRAGMENTS = (
    "api_key",
    "token",
    "cookie",
    "signed_url",
    "private-user-images",
    "provider response",
    "data:image/",
    ".mp4",
    ".mov",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
)


def load_project_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("project manifest must be a JSON object")
    validate_project_manifest(payload)
    return payload


def validate_project_manifest(payload: dict[str, Any]) -> None:
    if payload.get("artifact_type") != PROJECT_MANIFEST_ARTIFACT_TYPE:
        raise ValueError(f"project manifest artifact_type must be {PROJECT_MANIFEST_ARTIFACT_TYPE}")
    if payload.get("schema_version") != PROJECT_MANIFEST_SCHEMA_VERSION:
        raise ValueError(f"project manifest schema_version must be {PROJECT_MANIFEST_SCHEMA_VERSION}")
    _require_text(payload, "project_id")
    _require_text(payload, "project_type")
    _require_text(payload, "goal")
    if payload.get("status") not in PROJECT_MANIFEST_STATUSES:
        raise ValueError("project manifest status is unsupported")
    for field in PROJECT_MANIFEST_REF_LIST_FIELDS:
        if not isinstance(payload.get(field), list):
            raise ValueError(f"project manifest {field} must be a list")
    for field in ("does_not_store_secrets", "does_not_store_private_asset_bytes", "does_not_auto_sync"):
        if payload.get(field) is not True:
            raise ValueError(f"project manifest requires {field} true")
    _reject_private_or_secret_fragments(payload)


def _require_text(payload: dict[str, Any], field: str) -> None:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"project manifest requires {field}")


def _reject_private_or_secret_fragments(payload: dict[str, Any]) -> None:
    raw = json.dumps(payload, ensure_ascii=False).lower()
    fragments = AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS + UNSAFE_PROJECT_MANIFEST_FRAGMENTS
    if any(fragment.lower() in raw for fragment in fragments):
        raise ValueError("project manifest contains private paths, media bytes, provider URL, or secret")


__all__ = (
    "PROJECT_MANIFEST_ARTIFACT_TYPE",
    "PROJECT_MANIFEST_REF_LIST_FIELDS",
    "PROJECT_MANIFEST_SCHEMA_VERSION",
    "PROJECT_MANIFEST_STATUSES",
    "load_project_manifest",
    "validate_project_manifest",
)
