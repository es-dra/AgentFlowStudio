from __future__ import annotations

from typing import Any

from apps.api.runtime_workbench_support import artifact_ids, event_title, status


def build_job_center(jobs: list[dict[str, Any]]) -> dict[str, Any]:
    items = [_job_item(job) for job in jobs]
    counts = _counts(items)
    return {
        "status": _center_status(counts),
        "title": "Job center",
        "summary": _summary(counts),
        "counts": counts,
        "items": items,
        "polling": {
            "enabled": True,
            "manual_refresh_action": "refresh",
            "suggested_interval_ms": 5000,
            "scope": "current_project_jobs",
        },
        "non_claims": ["runtime verification is not human acceptance", "provider preflight is not provider smoke"],
    }


def _job_item(job: dict[str, Any]) -> dict[str, Any]:
    progress = job.get("progress") if isinstance(job.get("progress"), dict) else {}
    ids = artifact_ids(job)
    item_status = status(job)
    return {
        "job_id": str(job.get("job_id") or ""),
        "action": str(job.get("action") or "runtime_event"),
        "title": event_title(job),
        "status": item_status,
        "stage": str(progress.get("stage") or job.get("action") or ""),
        "percent": int(progress.get("percent") or 0),
        "terminal": progress.get("terminal") is True,
        "primary_artifact_id": ids[0] if ids else "",
        "artifact_ids": ids,
        "artifact_count": len(ids),
        "guidance": _guidance(str(job.get("action") or ""), item_status, str(job.get("error") or "")),
    }


def _counts(items: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"total": len(items), "running": 0, "blocked": 0, "failed": 0, "succeeded": 0}
    for item in items:
        item_status = item["status"]
        if item_status in counts:
            counts[item_status] += 1
    return counts


def _center_status(counts: dict[str, int]) -> str:
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
        return "No runtime jobs yet."
    return (
        f"{counts['total']} jobs: {counts['succeeded']} succeeded, "
        f"{counts['blocked']} blocked, {counts['failed']} failed."
    )


def _guidance(action: str, item_status: str, error: str) -> str:
    if item_status == "failed":
        return error or "Open the run details and inspect the error before retrying."
    if action == "provider_validation_plan" and item_status == "blocked":
        return "Provider remains gated; authorize the exact capability before real smoke."
    if action == "asset_test_run" and item_status == "blocked":
        return "Open the first-check report, add missing project material, then retry."
    if action == "two_round_validate" and item_status == "blocked":
        return "Open the next-round report and resolve blocked context refs."
    if action == "record_review_decision":
        return "Decision is evidence only; it does not become durable memory."
    if action == "record_feedback":
        return "Raw feedback is stored as evidence for later review."
    if item_status == "succeeded":
        return "Open the safe artifact to inspect the generated evidence."
    return "Refresh the workbench to update runtime state."


__all__ = ("build_job_center",)
