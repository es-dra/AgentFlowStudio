from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from narratocut.schemas import ClipPlan
from narratocut.utils import write_json


def mock_slice_clip_plans(clip_plans: list[ClipPlan], output_dir: str | Path) -> dict[str, Any]:
    """Write deterministic text placeholders for clip plans."""
    root = Path(output_dir)
    clips_dir = root / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    clips: list[dict[str, Any]] = []
    for index, plan in enumerate(clip_plans, start=1):
        file_name = f"{_safe_name(plan.clip_plan_id or f'clip_{index:03d}')}.txt"
        clip_path = clips_dir / file_name
        duration_sec = plan.duration_sec if plan.duration_sec is not None else _duration_from_segments(plan)
        clip_path.write_text(_mock_clip_text(plan, duration_sec), encoding="utf-8")
        clips.append(
            {
                "clip_id": f"mock_clip_{index:03d}",
                "clip_plan_id": plan.clip_plan_id,
                "script_id": plan.script_id,
                "title": plan.title,
                "duration_sec": duration_sec,
                "file_path": str(Path("clips") / file_name),
            }
        )

    manifest = {
        "status": "success",
        "clip_count": len(clips),
        "clips": clips,
    }
    write_json(root / "slice_manifest.json", manifest)
    return manifest


def _duration_from_segments(plan: ClipPlan) -> float:
    return sum(segment.end_sec - segment.start_sec for segment in plan.segments)


def _mock_clip_text(plan: ClipPlan, duration_sec: float) -> str:
    return "\n".join(
        [
            "MOCK CLIP",
            f"clip_plan_id: {plan.clip_plan_id}",
            f"script_id: {plan.script_id or ''}",
            f"title: {plan.title}",
            f"duration_sec: {duration_sec:g}",
            "",
        ]
    )


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_") or "clip"
