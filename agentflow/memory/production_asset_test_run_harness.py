from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentflow.memory.production_asset_consistency_review import (
    build_asset_consistency_review,
    load_asset_consistency_review_fixture,
    write_asset_consistency_review,
)
from agentflow.memory.production_asset_feedback import (
    build_asset_feedback_event,
    load_asset_feedback_fixture,
    write_asset_feedback_event,
)
from agentflow.memory.production_asset_profile_context_projection import (
    build_asset_profile_context_projection,
    write_asset_profile_context_projection,
)
from agentflow.memory.production_asset_profile_io import write_asset_profile_test_package
from agentflow.memory.production_asset_profile_promotion import (
    build_asset_profile_promotion_review,
    write_asset_profile_promotion_review,
)
from agentflow.memory.production_asset_profile_update_candidate import (
    build_asset_profile_update_candidate,
    write_asset_profile_update_candidate,
)
from agentflow.memory.production_asset_profiles import build_asset_profile_test_package, load_asset_profile_seed
from agentflow.memory.production_asset_test_run_report import (
    REAL_ASSET_TEST_HARNESS_KIND,
    REVIEW_SCREEN_SELECTED_FILES_KIND,
    build_real_asset_test_report,
    build_review_screen_selected_files,
    render_real_asset_test_report_markdown,
)
from agentflow.memory.production_loop import load_production_memory_loop
from agentflow.memory.production_operator_loop import (
    build_production_memory_operator_loop_run,
    write_production_memory_operator_loop_run,
)
from agentflow.harness.json_io import write_json


def run_real_asset_test_harness(
    *,
    loop_path: Path,
    asset_profile_seed_path: Path,
    feedback_json_path: Path,
    consistency_review_json_path: Path,
    output_dir: Path,
    promotion_decision: str,
    promotion_rationale: str,
    generated_at: str,
    decided_at: str,
    reviewed_at: str,
    project_materials_path: Path | None = None,
    character_reference_image_path: Path | None = None,
    reviewer_role: str = "operator",
) -> dict[str, Any]:
    _require_text("promotion_decision", promotion_decision)
    _require_text("promotion_rationale", promotion_rationale)
    _require_text("generated_at", generated_at)
    _require_text("decided_at", decided_at)
    _require_text("reviewed_at", reviewed_at)

    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    operator_artifact_path = _write_operator_loop(loop_path, output_root, generated_at)

    bundle = build_asset_profile_test_package(
        operator_artifact_path=operator_artifact_path,
        asset_profile_seed=load_asset_profile_seed(Path(asset_profile_seed_path)),
        generated_at=generated_at,
        project_materials_path=project_materials_path,
        character_reference_image_path=character_reference_image_path,
    )
    write_asset_profile_test_package(bundle, output_root)

    asset_profiles = _read_json(output_root / "asset_profiles.json")
    readiness = _read_json(output_root / "asset_profile_readiness.json")
    feedback_event = build_asset_feedback_event(
        asset_profiles=asset_profiles,
        asset_profile_readiness=readiness,
        feedback_fixture=load_asset_feedback_fixture(Path(feedback_json_path)),
        generated_at=generated_at,
    )
    write_asset_feedback_event(feedback_event, output_root)

    candidate = build_asset_profile_update_candidate(feedback_event, generated_at=generated_at)
    write_asset_profile_update_candidate(candidate, output_root)

    decision, version = build_asset_profile_promotion_review(
        asset_profiles=asset_profiles,
        update_candidate=candidate,
        decision=promotion_decision,
        rationale=promotion_rationale,
        reviewer_role=reviewer_role,
        decided_at=decided_at,
    )
    write_asset_profile_promotion_review(decision, version, output_root)

    projection: dict[str, Any] | None = None
    review: dict[str, Any] | None = None
    if version is not None:
        projection = build_asset_profile_context_projection(
            asset_profile_versions=[version],
            generated_at=decided_at,
        )
        write_asset_profile_context_projection(projection, output_root)
        review = build_asset_consistency_review(
            asset_profile_context_projection=projection,
            consistency_fixture=load_asset_consistency_review_fixture(Path(consistency_review_json_path)),
            reviewed_at=reviewed_at,
        )
        write_asset_consistency_review(review, output_root)

    report = build_real_asset_test_report(
        output_root=output_root,
        bundle=bundle,
        feedback_event=feedback_event,
        candidate=candidate,
        promotion_decision_payload=decision,
        profile_version=version,
        context_projection=projection,
        consistency_review=review,
        project_materials_path=project_materials_path,
        character_reference_image_path=character_reference_image_path,
    )
    write_json(output_root / "real_asset_test_report.json", report)
    (output_root / "real_asset_test_report.md").write_text(render_real_asset_test_report_markdown(report), encoding="utf-8")
    write_json(output_root / "review_screen_selected_files.json", build_review_screen_selected_files(report))
    return report


def _write_operator_loop(loop_path: Path, output_root: Path, generated_at: str) -> Path:
    loop = load_production_memory_loop(Path(loop_path))
    operator_result = build_production_memory_operator_loop_run(
        loop,
        generated_at=generated_at,
        source_kb_status="restructuring_or_unknown",
        draft_next_pass_result=True,
    )
    operator_dir = output_root / "operator_loop"
    write_production_memory_operator_loop_run(
        operator_result,
        operator_dir,
        write_run_package=True,
        write_run_package_check=True,
    )
    return operator_dir / "production_memory_operator_loop_run.json"


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name} must be a JSON object")
    return payload


def _require_text(label: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} is required")


__all__ = (
    "REAL_ASSET_TEST_HARNESS_KIND",
    "REVIEW_SCREEN_SELECTED_FILES_KIND",
    "build_real_asset_test_report",
    "build_review_screen_selected_files",
    "render_real_asset_test_report_markdown",
    "run_real_asset_test_harness",
)
