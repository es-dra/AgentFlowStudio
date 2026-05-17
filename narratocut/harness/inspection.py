from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from narratocut.harness.quality_checks import build_quality_report
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
        "artifacts": _artifact_statuses(root),
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


def _artifact_statuses(root: Path) -> list[dict[str, str]]:
    statuses: list[dict[str, str]] = []
    for artifact in ARTIFACTS_TO_INSPECT:
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
