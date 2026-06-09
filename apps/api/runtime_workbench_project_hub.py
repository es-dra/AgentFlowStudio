from __future__ import annotations

from typing import Any

from apps.api.runtime_workbench_support import artifact_ids, event_title, list_value, status


NON_CLAIMS = ["not human acceptance", "not business validation", "not durable memory"]


def build_project_hub(
    manifest: dict[str, Any],
    jobs: list[dict[str, Any]],
    project: dict[str, Any],
    command_hub: dict[str, Any],
) -> dict[str, Any]:
    return {
        "status": str(command_hub.get("status") or project.get("status") or "not_started"),
        "title": "Project hub",
        "summary": str(project.get("goal") or "Runtime project."),
        "active_project": {
            "project_id": str(project.get("project_id") or manifest.get("project_id") or ""),
            "project_type": str(project.get("project_type") or manifest.get("project_type") or ""),
            "goal": str(project.get("goal") or manifest.get("goal") or ""),
            "status": str(project.get("status") or manifest.get("status") or "in_progress"),
            "artifact_id": str(project.get("artifact_id") or ""),
        },
        "counts": {
            "source_assets": len(list_value(manifest.get("source_assets"))),
            "content_cards": len(list_value(manifest.get("content_cards"))),
            "runs": len(list_value(manifest.get("runs"))),
            "jobs": len(jobs),
            "feedback_refs": len(list_value(manifest.get("feedback_refs"))),
            "profile_versions": len(list_value(manifest.get("profile_version_refs"))),
        },
        "next_command": _safe_command(command_hub.get("primary_command")),
        "recent_jobs": [_safe_job(job) for job in reversed(jobs[-3:])],
        "non_claims": NON_CLAIMS,
    }


def _safe_command(value: Any) -> dict[str, Any]:
    command = value if isinstance(value, dict) else {}
    return {
        "command_id": str(command.get("command_id") or ""),
        "label": str(command.get("label") or "Continue"),
        "backend_action": str(command.get("backend_action") or ""),
        "ui_action": str(command.get("ui_action") or ""),
        "view": str(command.get("view") or "Create"),
        "summary": str(command.get("summary") or ""),
        "enabled": command.get("enabled") is True,
        "blocked_reason": str(command.get("blocked_reason") or ""),
        "requires_input": [str(item) for item in list_value(command.get("requires_input"))],
    }


def _safe_job(job: dict[str, Any]) -> dict[str, Any]:
    ids = artifact_ids(job)
    return {
        "job_id": str(job.get("job_id") or ""),
        "title": event_title(job),
        "action": str(job.get("action") or "runtime_event"),
        "status": status(job),
        "primary_artifact_id": _primary_artifact_id(job, ids),
        "artifact_ids": ids,
        "artifact_count": len(ids),
    }


def _primary_artifact_id(job: dict[str, Any], ids: list[str]) -> str:
    artifacts = job.get("artifacts", {}) if isinstance(job.get("artifacts"), dict) else {}
    for role in (
        "provider_safe_manifest",
        "two_round_context_runtime_report",
        "runtime_feedback_event",
        "runtime_review_decision",
        "real_asset_test_report",
    ):
        artifact_ref = artifacts.get(role)
        if isinstance(artifact_ref, dict) and artifact_ref.get("artifact_id"):
            return str(artifact_ref["artifact_id"])
    return ids[0] if ids else ""


__all__ = ("build_project_hub",)
