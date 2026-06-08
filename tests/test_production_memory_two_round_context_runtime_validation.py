from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from agentflow.memory.production_asset_test_run_harness import run_real_asset_test_harness
from agentflow.memory.production_asset_two_round_validation import run_two_round_context_runtime_validation

EXAMPLE_LOOP = Path("examples/agentflow/production_memory_loop.example.json")
EXAMPLE_SEED = Path("examples/agentflow/production_memory_asset_profile_seed.example.json")
EXAMPLE_FEEDBACK = Path("examples/agentflow/production_memory_asset_feedback.example.json")
EXAMPLE_CONSISTENCY_REVIEW = Path("examples/agentflow/production_memory_asset_consistency_review.example.json")
GENERATED_AT = "2026-06-04T00:00:00+08:00"
DECIDED_AT = "2026-06-04T00:20:00+08:00"
REVIEWED_AT = "2026-06-04T00:30:00+08:00"
ROUND_2_GENERATED_AT = "2026-06-04T01:00:00+08:00"
ROUND_2_REVIEWED_AT = "2026-06-04T01:30:00+08:00"


def test_two_round_context_runtime_report_traces_round_2_inclusions(tmp_path: Path) -> None:
    round_1_dir = _write_round_1(tmp_path)
    output_dir = tmp_path / "round_2"

    report = run_two_round_context_runtime_validation(
        round_1_dir=round_1_dir,
        output_dir=output_dir,
        consistency_review_json_path=EXAMPLE_CONSISTENCY_REVIEW,
        generated_at=ROUND_2_GENERATED_AT,
        reviewed_at=ROUND_2_REVIEWED_AT,
    )

    assert report["artifact_type"] == "agentflow_two_round_context_runtime_report"
    assert report["runtime_verification_status"] == "verified"
    assert report["improvement_assessment"] == "no_clear_improvement"
    assert report["reason_if_not_improved"] == "test_materials_insufficient"
    assert report["claim_boundaries"]["business_validation"] == "not_validated"
    assert report["claim_boundaries"]["human_acceptance"] == "not_claimed"
    assert report["provider_calls_started"] is False
    assert report["writes_long_term_memory"] is False
    assert report["writes_company_kb"] is False

    included = report["round_2_context_inclusions"]
    assert included
    assert included[0]["ref_id"] == "asset-profile:character:lead:v2"
    assert included[0]["profile_version"] == "v2"
    assert included[0]["source_profile_version_id"]
    assert included[0]["source_decision_id"]
    assert included[0]["evidence_refs"]

    blocked_ids = {item["ref_id"] for item in report["round_2_blocked_refs"]}
    included_ids = {item["ref_id"] for item in included}
    assert not (blocked_ids & included_ids)
    assert "asset-profile:character:lead:v1" in blocked_ids

    assert (output_dir / "asset_profile_context_projection.json").exists()
    assert (output_dir / "asset_consistency_review.json").exists()
    assert (output_dir / "two_round_context_runtime_report.json").exists()
    assert (output_dir / "two_round_context_runtime_report.md").exists()


def test_two_round_context_runtime_validation_cli_smoke(tmp_path: Path) -> None:
    round_1_dir = _write_round_1(tmp_path)
    output_dir = tmp_path / "round_2"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "asset-two-round-validate",
            "--round-1",
            str(round_1_dir),
            "--consistency-review-json",
            str(EXAMPLE_CONSISTENCY_REVIEW),
            "--generated-at",
            ROUND_2_GENERATED_AT,
            "--reviewed-at",
            ROUND_2_REVIEWED_AT,
            "--output",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Two-round context runtime validation: verified" in result.stdout
    assert "Business validation: not claimed" in result.stdout
    assert (output_dir / "two_round_context_runtime_report.md").exists()


def _write_round_1(tmp_path: Path) -> Path:
    round_1_dir = tmp_path / "round_1"
    run_real_asset_test_harness(
        loop_path=EXAMPLE_LOOP,
        asset_profile_seed_path=EXAMPLE_SEED,
        feedback_json_path=EXAMPLE_FEEDBACK,
        consistency_review_json_path=EXAMPLE_CONSISTENCY_REVIEW,
        output_dir=round_1_dir,
        promotion_decision="promoted",
        promotion_rationale="Operator explicitly approved this profile version for round two context projection.",
        generated_at=GENERATED_AT,
        decided_at=DECIDED_AT,
        reviewed_at=REVIEWED_AT,
    )
    return round_1_dir


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
