from __future__ import annotations

from typing import Any

from apps.api.runtime_store import RuntimeStore
from apps.api.runtime_workbench_support import list_value as _list


def build_style_memory(store: RuntimeStore, manifest: dict[str, Any]) -> dict[str, Any]:
    profile_refs = [item for item in _list(manifest.get("profile_version_refs")) if isinstance(item, dict)]
    feedback_refs = [item for item in _list(manifest.get("feedback_refs")) if isinstance(item, dict)]
    latest_ref = profile_refs[-1] if profile_refs else {}
    latest_artifact_id = str(latest_ref.get("artifact_id") or "")
    return {
        "status": "ready" if latest_artifact_id else "not_started",
        "title": "Project style memory",
        "summary": _summary(latest_artifact_id),
        "profile_version_count": len(profile_refs),
        "feedback_count": len(feedback_refs),
        "latest_profile_artifact_id": latest_artifact_id,
        "reusable_preferences": _preferences(store, latest_artifact_id),
        "next_pass_usage": "Use this profile in the next round context." if latest_artifact_id else "Run and review a first pass before reuse.",
        "non_claims": ["not durable company memory", "not human acceptance", "not business validation"],
    }


def _summary(latest_artifact_id: str) -> str:
    if latest_artifact_id:
        return "Reviewed project style profile is available for the next pass."
    return "No project style memory has been applied yet."


def _preferences(store: RuntimeStore, artifact_id: str) -> list[str]:
    if not artifact_id:
        return []
    try:
        payload = store.read_artifact(artifact_id).get("payload")
    except (KeyError, ValueError):
        payload = {}
    if not isinstance(payload, dict):
        return []
    candidates = payload.get("style_preferences") or payload.get("profile_summary") or payload.get("summary")
    if isinstance(candidates, list):
        return [str(item) for item in candidates[:4]]
    if isinstance(candidates, str) and candidates:
        return [candidates]
    return ["Reuse the reviewed profile version for next-pass consistency."]


__all__ = ("build_style_memory",)
