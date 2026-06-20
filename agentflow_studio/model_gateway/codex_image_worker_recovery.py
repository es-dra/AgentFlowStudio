from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from agentflow.harness.json_io import write_json
from agentflow_studio.model_gateway.codex_image_handoff import (
    JOB_ROOT_DIR,
    REQUEST_FILENAME,
    RESULT_FILENAME,
    failed_result_payload,
)
from agentflow_studio.model_gateway.codex_image_worker_io import append_worker_event, trim_finished_job_dir
from agentflow_studio.model_gateway.codex_image_worker_result import ProcessResult


def recover_stale_running_jobs(root: str | Path, *, stale_running_sec: float = 3600.0) -> list[ProcessResult]:
    recovered: list[ProcessResult] = []
    now = time.time()
    for running in _running_job_dirs(Path(root)):
        if now - _latest_mtime(running) < stale_running_sec:
            continue
        job_id = running.name
        job_root = running.parents[1]
        result_path = running / RESULT_FILENAME
        result = _safe_existing_result(result_path)
        if result and result.get("status") == "succeeded":
            destination = job_root / "completed" / job_id
            status = "succeeded"
            event_status = "succeeded"
        else:
            if not result:
                result = failed_result_payload(job_id=job_id, reason="Image generation worker timed out.")
                write_json(result_path, result)
            destination = job_root / "failed" / job_id
            status = "failed"
            event_status = "failed"
        if destination.exists():
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        running.rename(destination)
        trim_finished_job_dir(destination)
        append_worker_event(
            job_root,
            job_id=job_id,
            status=event_status,
            error_summary=None if status == "succeeded" else result["blocks"][0]["reason"],
        )
        recovered.append(ProcessResult(job_id=job_id, status=status, job_dir=destination))
    return recovered


def _running_job_dirs(root: Path) -> list[Path]:
    running_dirs: list[Path] = []
    direct = root / JOB_ROOT_DIR / "running"
    if direct.is_dir():
        running_dirs.append(direct)
    for path in root.rglob("running"):
        if path.parent.name == JOB_ROOT_DIR:
            running_dirs.append(path)
    seen: set[Path] = set()
    jobs: list[Path] = []
    for running_dir in running_dirs:
        resolved = running_dir.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        for job_dir in sorted(running_dir.iterdir(), key=lambda item: item.stat().st_mtime):
            if job_dir.is_dir() and (job_dir / REQUEST_FILENAME).is_file():
                jobs.append(job_dir)
    return jobs


def _latest_mtime(path: Path) -> float:
    latest = path.stat().st_mtime
    for item in path.rglob("*"):
        try:
            latest = max(latest, item.stat().st_mtime)
        except FileNotFoundError:
            continue
    return latest


def _safe_existing_result(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


__all__ = ("recover_stale_running_jobs",)
