from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fastapi.testclient import TestClient

from apps.api.runtime_service import create_runtime_app
from tools.studio_asset_context_followup_scenarios import (
    HAIR_LOCK,
    PROJECT_ID,
    prepare_assets,
    run_group2,
    run_group3,
)
from tools.studio_asset_context_sample_reference import (
    write_sample_reference,
    write_sample_scene_reference,
)


IMAGE_GATE = "AFS_ALLOW_REMOTE_IMAGE"
PROVIDER_CONFIG = "AFS_PROVIDER_CONFIG"
TRUE_VALUES = {"1", "true", "yes", "on"}


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    runtime_root = Path(args.runtime_root or tempfile.mkdtemp(prefix="afs-studio-s1-followup-")).resolve()
    output_dir = Path(args.output_dir or REPO_ROOT / "runs" / "studio_asset_context_followup_20260612").resolve()
    report_path = Path(args.report or output_dir / "followup_comparison_summary.json").resolve()
    runtime_root.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    if args.provider_config:
        os.environ[PROVIDER_CONFIG] = str(Path(args.provider_config).resolve())
    if not args.character_reference:
        args.character_reference = str(write_sample_reference(output_dir / "inputs" / "lin-wan-reference.png"))
    if not args.scene_reference:
        args.scene_reference = str(write_sample_scene_reference(output_dir / "inputs" / "observatory-reference.png"))

    preflight = _preflight(args)
    if preflight is not None:
        _write_json(report_path, preflight)
        print(json.dumps({"status": preflight["status"], "report": str(report_path)}, ensure_ascii=False))
        return 2

    client = TestClient(create_runtime_app(runtime_root=runtime_root))
    assets = prepare_assets(client, args)
    scenarios: dict[str, Any] = {}
    if args.scenario in {"all", "group2"}:
        scenarios["group2_character_scene"] = run_group2(client, args, assets)
    if args.scenario in {"all", "group3"}:
        scenarios["group3_lock_conflict"] = run_group3(client, args, assets)

    report = _runner_report(
        scenarios,
        runtime_root=runtime_root,
        output_dir=output_dir,
        live_authorized=args.allow_live_provider,
        provider_config_supplied=bool(os.environ.get(PROVIDER_CONFIG)),
        assets=assets,
    )
    _persist_evidence(runtime_root, output_dir, report)
    _write_json(report_path, report)
    print(json.dumps({"status": report["status"], "report": str(report_path)}, ensure_ascii=False))
    if args.allow_live_provider and report["status"] != "succeeded":
        return 3
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run AFS Studio S1 follow-up live comparisons.")
    parser.add_argument("--runtime-root", default="")
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--report", default="")
    parser.add_argument("--provider-config", default="")
    parser.add_argument("--provider-service-id", default="codex_image")
    parser.add_argument("--character-reference", default="")
    parser.add_argument("--scene-reference", default="")
    parser.add_argument("--scenario", choices=["all", "group2", "group3"], default="all")
    parser.add_argument("--allow-live-provider", action="store_true")
    return parser.parse_args(argv)


def _preflight(args: argparse.Namespace) -> dict[str, Any] | None:
    if _image_gate_ready() and not args.allow_live_provider:
        return _preflight_report("blocked", "live_provider_flag_missing", "AFS_ALLOW_REMOTE_IMAGE is true, but --allow-live-provider was not supplied.")
    if args.allow_live_provider and not _image_gate_ready():
        return _preflight_report("blocked", "image_gate_closed", "Live provider follow-up requires AFS_ALLOW_REMOTE_IMAGE=true.")
    if args.allow_live_provider and not os.environ.get(PROVIDER_CONFIG, "").strip():
        return _preflight_report("blocked", "provider_config_missing", "Live provider follow-up requires AFS_PROVIDER_CONFIG or --provider-config.")
    for field, path in (("character_reference", args.character_reference), ("scene_reference", args.scene_reference)):
        if args.allow_live_provider and not Path(path).is_file():
            return _preflight_report("blocked", f"{field}_missing", f"Live provider follow-up requires a local {field} image.")
    return None


def _runner_report(
    scenarios: dict[str, Any],
    *,
    runtime_root: Path,
    output_dir: Path,
    live_authorized: bool,
    provider_config_supplied: bool,
    assets: dict[str, Any],
) -> dict[str, Any]:
    scenario_statuses = [str(item.get("status")) for item in scenarios.values()]
    status = "succeeded" if scenario_statuses and all(item == "succeeded" for item in scenario_statuses) else "blocked"
    provider_calls_started = _provider_calls_started(scenarios)
    return {
        "artifact_type": "studio_asset_context_followup_comparison_report",
        "schema_version": "0.1.0",
        "status": status,
        "runner_mode": "live_provider" if live_authorized else "gate_closed_readiness",
        "runtime_root_persisted": False,
        "runtime_root_label": runtime_root.name,
        "provider_config_supplied": provider_config_supplied,
        "provider_calls_started": provider_calls_started,
        "output_dir": str(output_dir),
        "fixed_assets": {
            "character_asset_id": assets["character_visual_asset"]["asset_id"],
            "scene_asset_id": assets["scene_visual_asset"]["asset_id"],
        },
        "scenarios": scenarios,
        "evidence_files": {},
        "non_claims": [
            "live provider mode is provider smoke evidence only",
            "not human acceptance",
            "not business validation",
            "not durable memory",
        ],
    }


def _persist_evidence(runtime_root: Path, output_dir: Path, report: dict[str, Any]) -> None:
    evidence: dict[str, str] = {}
    runs_dir = runtime_root / "runs" / PROJECT_ID
    if runs_dir.is_dir():
        evidence_root = output_dir / "runtime_evidence"
        if evidence_root.exists():
            shutil.rmtree(evidence_root)
        shutil.copytree(runs_dir, evidence_root)
        evidence["runtime_runs_dir"] = str(evidence_root)
    _copy_group2_candidates(report, output_dir, evidence, runtime_root)
    _copy_group3_candidates(report, output_dir, evidence, runtime_root)
    report["evidence_files"] = evidence


def _copy_group2_candidates(report: dict[str, Any], output_dir: Path, evidence: dict[str, str], runtime_root: Path) -> None:
    group = report.get("scenarios", {}).get("group2_character_scene", {})
    job_id = str(group.get("job", {}).get("job_id") or "")
    arms = group.get("report", {}).get("arms") or []
    for arm in arms:
        arm_id = str(arm.get("arm_id") or "")
        for index, item in enumerate(arm.get("result_refs") or [], start=1):
            candidate_id = str(item.get("candidate_id") or f"candidate_{index:03d}")
            source = _candidate_source_from_run_dir(runtime_root / "runs" / PROJECT_ID / job_id / arm_id, candidate_id)
            if not source.is_file():
                continue
            target = output_dir / "group2_character_scene" / arm_id / f"candidate_{index:03d}{source.suffix.lower()}"
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            evidence[f"group2_{arm_id}_candidate_{index:03d}"] = str(target)


def _copy_group3_candidates(report: dict[str, Any], output_dir: Path, evidence: dict[str, str], runtime_root: Path) -> None:
    group = report.get("scenarios", {}).get("group3_lock_conflict", {})
    for label in ("locked", "temporary_unlocked"):
        item = group.get(label, {})
        job_id = str(item.get("job", {}).get("job_id") or "")
        for preview in item.get("candidate_previews") or []:
            candidate_id = str(preview.get("candidate_id") or "")
            source = _candidate_source_from_run_dir(runtime_root / "runs" / PROJECT_ID / job_id, candidate_id)
            if source is None or not source.is_file():
                continue
            target = output_dir / "group3_lock_conflict" / label / f"{candidate_id}{source.suffix.lower()}"
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            evidence[f"group3_{label}_{candidate_id}"] = str(target)


def _candidate_source_from_run_dir(run_dir: Path, candidate_id: str) -> Path:
    for suffix in (".jpg", ".jpeg", ".png", ".webp"):
        path = run_dir / "image_candidates" / f"{candidate_id}{suffix}"
        if path.is_file():
            return path
    return run_dir / "image_candidates" / f"{candidate_id}.jpg"


def _provider_calls_started(value: Any) -> bool:
    if isinstance(value, dict):
        if value.get("provider_calls_started") is True:
            return True
        return any(_provider_calls_started(item) for item in value.values())
    if isinstance(value, list):
        return any(_provider_calls_started(item) for item in value)
    return False


def _preflight_report(status: str, block_id: str, reason: str) -> dict[str, Any]:
    return {
        "artifact_type": "studio_asset_context_followup_comparison_report",
        "schema_version": "0.1.0",
        "status": status,
        "runner_mode": "preflight",
        "provider_gate": {"capability": "image", "env": IMAGE_GATE, "status": "ready_not_run" if _image_gate_ready() else "blocked"},
        "provider_calls_started": False,
        "blocks": [{"block_id": block_id, "reason": reason}],
        "non_claims": [
            "preflight only",
            "not live provider smoke",
            "not human acceptance",
            "not business validation",
        ],
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _image_gate_ready() -> bool:
    return os.environ.get(IMAGE_GATE, "").strip().lower() in TRUE_VALUES


if __name__ == "__main__":
    raise SystemExit(main())
