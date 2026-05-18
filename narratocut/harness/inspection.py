from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from narratocut.harness.highlight_artifacts import (
    highlight_artifacts_to_inspect,
    is_highlight_quality_profile,
)
from narratocut.harness.final_video_quality import final_video_artifacts_to_inspect
from narratocut.harness.quality_checks import build_quality_report
from narratocut.harness.quality_profiles import (
    FINAL_VIDEO_PROFILE,
    REAL_CLIP_QUALITY_PROFILES,
    SUBTITLE_EXPORT_PROFILE,
)
from narratocut.harness.subtitle_quality import subtitle_artifacts_to_inspect
from narratocut.harness.video_artifacts import (
    is_video_quality_profile,
    video_artifacts_to_inspect,
)
from narratocut.utils import write_json


ARTIFACTS_TO_INSPECT = [
    "hooks.json",
    "scripts.json",
    "clip_plans.json",
    "slice_manifest.json",
    "manifest.json",
    "run_manifest.json",
    "trace.json",
    "clips/",
]

REAL_VIDEO_ARTIFACTS_TO_INSPECT = [
    "video_metadata.json",
    "clip_plan_validation.json",
    "real_slice_manifest.json",
    "run_manifest.json",
    "trace.json",
    "clips/",
]


def inspect_run(run_dir: str | Path) -> dict[str, Any]:
    root = Path(run_dir)
    run_manifest = _load_json_object(root / "run_manifest.json")
    legacy_manifest = _load_json_object(root / "manifest.json")
    quality_report = build_quality_report(root)
    write_json(root / "quality_report.json", quality_report)

    return {
        "run_id": _run_id(root, run_manifest, legacy_manifest),
        "workflow": _workflow(run_manifest, legacy_manifest),
        "status": quality_report["status"],
        "artifacts": _artifact_statuses(root, run_manifest),
        "quality_report": quality_report,
    }


def _run_id(
    root: Path,
    run_manifest: dict[str, Any] | None,
    legacy_manifest: dict[str, Any] | None,
) -> str:
    if run_manifest and run_manifest.get("run_id"):
        return str(run_manifest["run_id"])
    if legacy_manifest and legacy_manifest.get("run_id"):
        return str(legacy_manifest["run_id"])
    return root.name


def _workflow(
    run_manifest: dict[str, Any] | None,
    legacy_manifest: dict[str, Any] | None,
) -> str:
    if run_manifest and run_manifest.get("workflow"):
        return str(run_manifest["workflow"])
    if legacy_manifest and legacy_manifest.get("workflow_name"):
        return str(legacy_manifest["workflow_name"])
    return "unknown"


def _artifact_statuses(root: Path, run_manifest: dict[str, Any] | None) -> list[dict[str, str]]:
    statuses: list[dict[str, str]] = []
    quality_profile = run_manifest.get("quality_profile") if run_manifest else None
    if is_video_quality_profile(quality_profile):
        artifacts = video_artifacts_to_inspect(quality_profile)
    elif is_highlight_quality_profile(quality_profile):
        artifacts = highlight_artifacts_to_inspect(quality_profile)
    elif quality_profile in REAL_CLIP_QUALITY_PROFILES:
        artifacts = REAL_VIDEO_ARTIFACTS_TO_INSPECT
    elif quality_profile == FINAL_VIDEO_PROFILE:
        artifacts = final_video_artifacts_to_inspect()
    elif quality_profile == SUBTITLE_EXPORT_PROFILE:
        artifacts = subtitle_artifacts_to_inspect()
    else:
        artifacts = ARTIFACTS_TO_INSPECT
    for artifact in artifacts:
        path = root / artifact.rstrip("/")
        exists = path.is_dir() if artifact.endswith("/") else path.is_file()
        statuses.append({"path": artifact, "status": "found" if exists else "missing"})
    return statuses


def _load_json_object(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None
