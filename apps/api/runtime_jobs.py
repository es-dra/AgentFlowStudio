from __future__ import annotations

from typing import Any

from apps.api.runtime_store import RuntimeStore, public_job, safe_id


def runtime_job(
    job_id: str,
    project_id: str,
    action: str,
    status: str,
    *,
    artifacts: dict[str, Any] | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    job: dict[str, Any] = {
        "job_id": job_id,
        "project_id": project_id,
        "action": action,
        "status": status,
        "progress": job_progress(action, status),
        "artifacts": artifacts or {},
    }
    if error:
        job["error"] = error
    return job


def public_job_from_store(store: RuntimeStore, job_id: str) -> dict[str, Any]:
    return public_job(store.load_job(job_id))


def job_progress(action: str, status: str) -> dict[str, Any]:
    terminal = status in {"succeeded", "failed", "blocked", "cancelled"}
    percent = 100 if terminal else 50 if status == "running" else 0
    return {"stage": action, "percent": percent, "terminal": terminal}


def safe_job_id(value: str) -> str:
    return safe_id(value)


__all__ = (
    "job_progress",
    "public_job_from_store",
    "runtime_job",
    "safe_job_id",
)
