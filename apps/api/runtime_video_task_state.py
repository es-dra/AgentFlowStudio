from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agentflow.harness.json_io import write_json
from apps.api.runtime_store import RuntimeStore, read_json, safe_id
from apps.api.runtime_video_constants import DAILY_VIDEO_SUBMIT_LIMIT
from apps.api.runtime_video_manifest import write_json_checked


def write_task_state(output_dir: Path, state: dict[str, Any]) -> None:
    write_json_checked(output_dir / "video_task_state.json", state)


def provider_task_for_state(provider_task: dict[str, Any]) -> dict[str, Any]:
    task = dict(provider_task)
    inner = task.get("task")
    if isinstance(inner, dict):
        safe_inner = dict(inner)
        safe_inner.pop("output_dir", None)
        safe_inner.pop("raw", None)
        task["task"] = safe_inner
    task.pop("output_dir", None)
    return task


def provider_task_for_poll(task: Any, output_dir: Path) -> dict[str, Any]:
    payload = dict(task) if isinstance(task, dict) else {}
    inner = payload.get("task")
    if isinstance(inner, dict):
        poll_inner = dict(inner)
        poll_inner["output_dir"] = str(output_dir)
        payload["task"] = poll_inner
    else:
        payload["output_dir"] = str(output_dir)
    return payload


def load_task_state(output_dir: Path) -> dict[str, Any]:
    path = output_dir / "video_task_state.json"
    if not path.is_file():
        raise ValueError("video task state not found")
    return read_json(path)


def daily_submit_limit() -> int:
    return DAILY_VIDEO_SUBMIT_LIMIT


def daily_submit_count(store: RuntimeStore, project_id: str) -> int:
    path = _daily_quota_path(store, project_id)
    if not path.is_file():
        return 0
    payload = read_json(path)
    return int(payload.get("submitted_count") or 0)


def increment_daily_submit_count(store: RuntimeStore, project_id: str) -> None:
    path = _daily_quota_path(store, project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    count = daily_submit_count(store, project_id) + 1
    write_json(
        path,
        {
            "artifact_type": "afs_video_daily_quota",
            "schema_version": "0.1.0",
            "project_id": project_id,
            "date": datetime.now(timezone.utc).date().isoformat(),
            "submitted_count": count,
            "does_not_store_prompt": True,
            "does_not_store_secrets": True,
        },
    )


def _daily_quota_path(store: RuntimeStore, project_id: str) -> Path:
    today = datetime.now(timezone.utc).date().isoformat()
    return store.projects_dir / safe_id(project_id) / "quota" / f"video_{today}.json"
