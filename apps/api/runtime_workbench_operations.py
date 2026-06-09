from __future__ import annotations

from typing import Any


NON_CLAIMS = [
    "runtime verification is not human acceptance",
    "provider preflight is not provider smoke",
    "blocked provider gates require explicit capability authorization",
]


def build_operations_workspace(
    *,
    job_center: dict[str, Any],
    activity_timeline: dict[str, Any],
    provider_gate: dict[str, Any],
    command_hub: dict[str, Any],
) -> dict[str, Any]:
    jobs = _list(job_center.get("items"))
    activity = _list(activity_timeline.get("items"))
    selected_job_id = _selected_job_id(jobs, activity)
    provider_blockers = _list(provider_gate.get("blockers"))
    return {
        "status": _status(job_center, provider_gate),
        "title": "任务与 Provider",
        "summary": _summary(job_center, provider_blockers),
        "selected_job_id": selected_job_id,
        "counts": _counts(job_center, activity_timeline, jobs, provider_blockers),
        "job_queue": jobs,
        "latest_activity": activity[:6],
        "provider_gate": _provider_gate(provider_gate),
        "provider_controls": _provider_controls(provider_gate, command_hub),
        "polling": dict(job_center.get("polling", {})) if isinstance(job_center.get("polling"), dict) else {},
        "non_claims": NON_CLAIMS,
    }


def _status(job_center: dict[str, Any], provider_gate: dict[str, Any]) -> str:
    job_status = str(job_center.get("status") or "not_started")
    provider_status = str(provider_gate.get("status") or "ready_not_run")
    if job_status == "failed":
        return "failed"
    if job_status == "blocked" or provider_status == "blocked":
        return "blocked"
    if job_status == "running":
        return "running"
    if job_status == "succeeded":
        return "succeeded"
    return "not_started"


def _summary(job_center: dict[str, Any], provider_blockers: list[dict[str, Any]]) -> str:
    job_counts = dict(job_center.get("counts", {})) if isinstance(job_center.get("counts"), dict) else {}
    total = int(job_counts.get("total") or 0)
    if not total:
        return "暂无运行任务；项目素材准备后可进行 Provider 预检。"
    if provider_blockers:
        return f"已跟踪 {total} 个运行任务；Provider 预检有 {len(provider_blockers)} 个阻塞项。"
    return f"已跟踪 {total} 个运行任务，Provider 预检暂无阻塞项。"


def _counts(
    job_center: dict[str, Any],
    activity_timeline: dict[str, Any],
    jobs: list[dict[str, Any]],
    provider_blockers: list[dict[str, Any]],
) -> dict[str, int]:
    job_counts = dict(job_center.get("counts", {})) if isinstance(job_center.get("counts"), dict) else {}
    activity_counts = dict(activity_timeline.get("counts", {})) if isinstance(activity_timeline.get("counts"), dict) else {}
    return {
        "jobs": int(job_counts.get("total") or 0),
        "running": int(job_counts.get("running") or 0),
        "blocked": int(job_counts.get("blocked") or 0),
        "failed": int(job_counts.get("failed") or 0),
        "succeeded": int(job_counts.get("succeeded") or 0),
        "activities": int(activity_counts.get("total") or 0),
        "artifact_refs": len(_artifact_ids(jobs)),
        "provider_blockers": len(provider_blockers),
    }


def _selected_job_id(jobs: list[dict[str, Any]], activity: list[dict[str, Any]]) -> str:
    latest_job_id = str(activity[0].get("job_id") or "") if activity else ""
    if latest_job_id:
        return latest_job_id
    return str(jobs[0].get("job_id") or "") if jobs else ""


def _provider_gate(provider_gate: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": str(provider_gate.get("status") or "ready_not_run"),
        "title": str(provider_gate.get("title") or "Provider 预检"),
        "summary": str(provider_gate.get("summary") or "Provider 预检尚未运行。"),
        "primary_artifact_id": str(provider_gate.get("primary_artifact_id") or ""),
        "blockers": [_blocker(item) for item in _list(provider_gate.get("blockers"))],
        "actions": [str(item) for item in _list(provider_gate.get("actions"))],
    }


def _provider_controls(provider_gate: dict[str, Any], command_hub: dict[str, Any]) -> dict[str, Any]:
    command = _provider_command(provider_gate, command_hub)
    return {
        "primary_action": str(command.get("backend_action") or "run_provider_preflight"),
        "primary_label": str(command.get("label") or "运行 Provider 预检"),
        "ui_action": str(command.get("ui_action") or ""),
        "enabled": command.get("enabled") is True,
        "handoff_view": str(command.get("view") or "Jobs"),
        "summary": str(command.get("summary") or "Provider 预检仍处于闸门控制下。"),
        "blocked_reason": str(command.get("blocked_reason") or ""),
        "requires_input": [str(item) for item in _list(command.get("requires_input"))],
    }


def _provider_command(provider_gate: dict[str, Any], command_hub: dict[str, Any]) -> dict[str, Any]:
    primary = dict(command_hub.get("primary_command", {})) if isinstance(command_hub.get("primary_command"), dict) else {}
    if primary.get("backend_action") == "resolve_provider_preflight" or provider_gate.get("status") == "blocked":
        return primary
    for command in _list(command_hub.get("commands")):
        if isinstance(command, dict) and command.get("backend_action") == "run_provider_preflight":
            return dict(command)
    return primary


def _artifact_ids(jobs: list[dict[str, Any]]) -> set[str]:
    ids: set[str] = set()
    for job in jobs:
        for artifact_id in _list(job.get("artifact_ids")):
            value = str(artifact_id or "")
            if value:
                ids.add(value)
    return ids


def _blocker(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        text = str(value or "blocked")
        return {"blocker_id": text, "message": text, "user_action": ""}
    return {
        "blocker_id": str(value.get("blocker_id") or value.get("reason") or "blocked"),
        "message": str(value.get("message") or value.get("summary") or value.get("reason") or "blocked"),
        "user_action": str(value.get("user_action") or ""),
    }


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


__all__ = ("build_operations_workspace",)
