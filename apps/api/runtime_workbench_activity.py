from __future__ import annotations

from typing import Any

from apps.api.runtime_workbench_support import artifact_ids, event_title, status


NON_CLAIMS = ["not human acceptance", "not business validation", "not durable memory"]


def build_activity_timeline(jobs: list[dict[str, Any]]) -> dict[str, Any]:
    items = [_activity_item(index, job) for index, job in enumerate(reversed(jobs), start=1)]
    counts = _counts(items)
    return {
        "status": _timeline_status(counts),
        "title": "Activity timeline",
        "summary": _summary(counts),
        "counts": counts,
        "items": items,
        "non_claims": NON_CLAIMS,
    }


def _activity_item(index: int, job: dict[str, Any]) -> dict[str, Any]:
    ids = artifact_ids(job)
    primary_artifact_id = _primary_artifact_id(job, ids)
    return {
        "event_id": f"activity:{index}:{job.get('job_id')}",
        "title": event_title(job),
        "action": str(job.get("action") or "runtime_event"),
        "status": status(job),
        "job_id": str(job.get("job_id") or ""),
        "primary_artifact_id": primary_artifact_id,
        "artifact_ids": ids,
        "artifact_count": len(ids),
    }


def _primary_artifact_id(job: dict[str, Any], ids: list[str]) -> str:
    artifacts = job.get("artifacts", {}) if isinstance(job.get("artifacts"), dict) else {}
    for role in (
        "provider_safe_manifest",
        "real_asset_test_report",
        "two_round_context_runtime_report",
        "runtime_feedback_event",
        "runtime_review_decision",
    ):
        artifact_ref = artifacts.get(role)
        if isinstance(artifact_ref, dict) and artifact_ref.get("artifact_id"):
            return str(artifact_ref["artifact_id"])
    return ids[0] if ids else ""


def _counts(items: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"total": len(items), "running": 0, "blocked": 0, "failed": 0, "succeeded": 0}
    for item in items:
        item_status = item["status"]
        if item_status in counts:
            counts[item_status] += 1
    return counts


def _timeline_status(counts: dict[str, int]) -> str:
    if counts["failed"]:
        return "failed"
    if counts["blocked"]:
        return "blocked"
    if counts["running"]:
        return "running"
    if counts["succeeded"]:
        return "succeeded"
    return "not_started"


def _summary(counts: dict[str, int]) -> str:
    if not counts["total"]:
        return "No runtime activity yet."
    return f"{counts['total']} runtime events with {counts['blocked']} blocked and {counts['failed']} failed."


__all__ = ("build_activity_timeline",)
