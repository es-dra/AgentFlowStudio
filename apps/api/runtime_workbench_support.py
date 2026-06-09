from __future__ import annotations

from typing import Any

from apps.api.runtime_store import RuntimeStore


NAVIGATION = ["Projects", "Create", "Assets", "Review", "Style Memory", "Jobs", "Settings"]
NON_CLAIMS = ["not human acceptance", "not business validation", "not durable memory"]
SAFE_REF_POLICY = "frontend stores ids and summaries only; content is read through safe artifact refs"


def event_title(job: dict[str, Any]) -> str:
    labels = {
        "asset_test_run": "首轮检查",
        "record_feedback": "审片反馈已记录",
        "record_review_decision": "审片决定已记录",
        "two_round_validate": "下一轮已准备",
        "provider_validation_plan": "Provider 预检",
    }
    return labels.get(str(job.get("action")), str(job.get("action") or "运行事件"))


def jobs_by_action(jobs: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for job in jobs:
        grouped.setdefault(str(job.get("action")), []).append(job)
    return grouped


def latest(grouped: dict[str, list[dict[str, Any]]], action: str) -> dict[str, Any] | None:
    jobs = grouped.get(action) or []
    return jobs[-1] if jobs else None


def status(job: dict[str, Any]) -> str:
    value = str(job.get("status") or "not_started")
    return value if value in {"running", "succeeded", "failed", "blocked", "cancelled"} else "not_started"


def artifact(job: dict[str, Any], role: str) -> dict[str, Any] | None:
    value = dict(job.get("artifacts", {}).get(role) or {})
    return value or None


def artifact_id(artifact_ref: dict[str, Any] | None) -> str | None:
    return str(artifact_ref.get("artifact_id")) if artifact_ref and artifact_ref.get("artifact_id") else None


def artifact_ids(job: dict[str, Any]) -> list[str]:
    return [
        str(artifact_ref.get("artifact_id"))
        for artifact_ref in dict(job.get("artifacts", {})).values()
        if isinstance(artifact_ref, dict) and artifact_ref.get("artifact_id")
    ]


def payload(store: RuntimeStore, artifact_ref: dict[str, Any] | None) -> dict[str, Any]:
    artifact_ref_id = artifact_id(artifact_ref)
    if not artifact_ref_id:
        return {}
    try:
        value = store.read_artifact(artifact_ref_id).get("payload")
    except (KeyError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def summary(payload_value: dict[str, Any], fallback: str) -> str:
    for key in ("summary", "run_status", "runtime_verification_status", "status"):
        value = payload_value.get(key)
        if isinstance(value, str) and value:
            return value
    return fallback


def list_value(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


__all__ = (
    "NAVIGATION",
    "NON_CLAIMS",
    "SAFE_REF_POLICY",
    "artifact",
    "artifact_id",
    "artifact_ids",
    "event_title",
    "jobs_by_action",
    "latest",
    "list_value",
    "payload",
    "status",
    "summary",
)
