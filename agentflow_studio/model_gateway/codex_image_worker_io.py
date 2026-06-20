from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from agentflow_studio.model_gateway.codex_image_handoff import RESULT_FILENAME


def append_worker_event(
    job_root: Path,
    *,
    job_id: str,
    status: str,
    image_path: str | None = None,
    error_summary: str | None = None,
) -> None:
    event = {
        "time": datetime.now(timezone.utc).isoformat(),
        "job_id": job_id,
        "status": status,
        "image_path": image_path,
        "error_summary": error_summary,
        "provider_raw_response_stored": False,
    }
    path = job_root / "_logs" / "events.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def trim_finished_job_dir(job_dir: Path) -> None:
    for item in Path(job_dir).iterdir():
        if item.name == RESULT_FILENAME:
            continue
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink(missing_ok=True)


__all__ = ("append_worker_event", "trim_finished_job_dir")
