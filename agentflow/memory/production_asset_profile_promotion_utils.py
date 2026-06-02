from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentflow.harness.constants import AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS

UNSAFE_EXTRA_FRAGMENTS = (
    "http://",
    "https://",
    "file://",
    "data:image/",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".mp4",
    ".mov",
    "private-user-images",
    "authorization",
    "bearer",
    "provider result url",
)


def reject_unsafe_asset_profile_promotion(value: Any) -> None:
    raw = json.dumps(value, ensure_ascii=False).lower()
    fragments = AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS + UNSAFE_EXTRA_FRAGMENTS
    if any(fragment.lower() in raw for fragment in fragments):
        raise ValueError("asset profile promotion contains private fragments, media bytes, provider URL, or secret")


def safe_id(prefix: str, target_ref: str, created_at: str) -> str:
    raw = f"{prefix}:{target_ref}:{created_at}"
    safe = "".join(char.lower() if char.isalnum() else "-" for char in raw).strip("-")
    while "--" in safe:
        safe = safe.replace("--", "-")
    return safe


def require_text(payload: dict[str, Any], field: str) -> None:
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"asset profile promotion requires {field}")


def dict_value(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def list_value(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def profile_promotion_claim_boundaries() -> dict[str, str]:
    return {
        "human_acceptance": "not_claimed",
        "business_validation": "not_validated",
        "provider_success": "not_attempted",
        "durable_memory_runtime": "not_implemented",
        "company_kb_promotion": "not_performed",
        "profile_promotion": "local_project_profile_version_only",
    }


def profile_promotion_non_claims() -> list[str]:
    return [
        "not human acceptance",
        "not business validation",
        "not durable memory",
        "not Company KB promotion",
        "not provider success",
        "not next-pass execution",
    ]


def next_version_label(current: str) -> str:
    if current.startswith("v") and current[1:].isdigit():
        return f"v{int(current[1:]) + 1}"
    return "v2"


def next_profile_id(profile_id: str, next_label: str) -> str:
    parts = profile_id.split(":")
    if parts and parts[-1].startswith("v") and parts[-1][1:].isdigit():
        parts[-1] = next_label
        return ":".join(parts)
    return f"{profile_id}:{next_label}"


def version_change_summary(
    *,
    source_profile_id: str,
    target_profile_id: str,
    candidate: dict[str, Any],
    decision: dict[str, Any],
    patch_ops: list[dict[str, Any]],
) -> dict[str, Any]:
    decision_value = str(decision["decision"])
    return {
        "summary": f"Applied {len(patch_ops)} structured profile patch operations from explicit {decision_value} decision.",
        "source_profile_id": source_profile_id,
        "target_profile_id": target_profile_id,
        "source_candidate_id": candidate["candidate_id"],
        "source_decision_id": decision["decision_id"],
        "decision": decision_value,
        "patch_ops_count": len(patch_ops),
        "applied_paths": sorted({str(op.get("path")) for op in patch_ops}),
    }


def remove_stale_profile_version_outputs(output_root: Path) -> None:
    for name in ("asset_profile_version.json", "asset_profile_version.md"):
        path = output_root / name
        if path.exists():
            path.unlink()


__all__ = (
    "dict_value",
    "list_value",
    "next_profile_id",
    "next_version_label",
    "profile_promotion_claim_boundaries",
    "profile_promotion_non_claims",
    "reject_unsafe_asset_profile_promotion",
    "require_text",
    "remove_stale_profile_version_outputs",
    "safe_id",
    "version_change_summary",
)
