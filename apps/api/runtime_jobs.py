from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import HTTPException

from apps.api.runtime_store import RuntimeStore, public_job, safe_id


def optional_path(value: str | None) -> Path | None:
    return Path(value) if value else None


def presence_ref(role: str, value: str | None) -> dict[str, str]:
    return {"role": role, "ref": "provided_redacted" if value else "not_provided"}


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
        "artifacts": artifacts or {},
    }
    if error:
        job["error"] = error
    return job


def public_job_from_store(store: RuntimeStore, job_id: str) -> dict[str, Any]:
    return public_job(store.load_job(job_id))


def load_round_1_job(store: RuntimeStore, job_id: str) -> dict[str, Any]:
    try:
        job = store.load_job(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="round 1 job not found") from exc
    if job.get("action") != "asset_test_run" or not job.get("_output_dir"):
        raise HTTPException(status_code=422, detail="round_1_job_id must reference an asset_test_run job")
    return job


def safe_job_id(value: str) -> str:
    return safe_id(value)


__all__ = (
    "load_round_1_job",
    "optional_path",
    "presence_ref",
    "public_job_from_store",
    "runtime_job",
    "safe_job_id",
)
