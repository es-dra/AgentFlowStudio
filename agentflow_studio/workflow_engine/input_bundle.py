from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_workflow_inputs(input_path: str | Path) -> dict[str, Any]:
    path = Path(input_path)
    if path.suffix.lower() != ".json":
        return {"input_text_file": str(path)}

    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {"input_text_file": str(path)}

    if not isinstance(payload, dict):
        return {"input_text_file": str(path)}
    if _is_real_video_bundle(payload):
        return _flatten_real_video_bundle(payload)
    if _is_clip_plan_to_real_clips_bundle(payload):
        return _flatten_clip_plan_to_real_clips_bundle(payload)
    return payload


def _is_real_video_bundle(payload: dict[str, Any]) -> bool:
    return all(isinstance(payload.get(key), dict) for key in ["project", "video", "roi", "clip_plan"])


def _flatten_real_video_bundle(payload: dict[str, Any]) -> dict[str, Any]:
    project = payload["project"]
    video = payload["video"]
    roi = payload["roi"]
    clip_plan = payload["clip_plan"]
    output = payload.get("output") if isinstance(payload.get("output"), dict) else {}
    return {
        "project_id": project.get("project_id"),
        "project_name": project.get("name"),
        "input_video_file": video.get("path"),
        "roi_config": roi.get("path"),
        "clip_plan": clip_plan.get("path"),
        "output_clips_dir": output.get("clips_dir", "clips"),
    }


def _is_clip_plan_to_real_clips_bundle(payload: dict[str, Any]) -> bool:
    return all(isinstance(payload.get(key), dict) for key in ["video", "clip_plan"])


def _flatten_clip_plan_to_real_clips_bundle(payload: dict[str, Any]) -> dict[str, Any]:
    project = payload.get("project") if isinstance(payload.get("project"), dict) else {}
    video = payload["video"]
    clip_plan = payload["clip_plan"]
    output = payload.get("output") if isinstance(payload.get("output"), dict) else {}
    return {
        "project_id": project.get("project_id"),
        "project_name": project.get("name"),
        "video_path": video.get("path"),
        "clip_plan_path": clip_plan.get("path"),
        "output_clips_dir": output.get("clips_dir", "clips"),
    }
