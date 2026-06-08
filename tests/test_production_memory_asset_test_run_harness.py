from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from agentflow.memory.production_asset_test_run_harness import run_real_asset_test_harness

EXAMPLE_LOOP = Path("examples/agentflow/production_memory_loop.example.json")
EXAMPLE_SEED = Path("examples/agentflow/production_memory_asset_profile_seed.example.json")
EXAMPLE_FEEDBACK = Path("examples/agentflow/production_memory_asset_feedback.example.json")
EXAMPLE_CONSISTENCY_REVIEW = Path("examples/agentflow/production_memory_asset_consistency_review.example.json")
GENERATED_AT = "2026-06-04T00:00:00+08:00"
DECIDED_AT = "2026-06-04T00:20:00+08:00"
REVIEWED_AT = "2026-06-04T00:30:00+08:00"


def test_real_asset_test_run_harness_writes_reviewable_package(tmp_path: Path) -> None:
    output_dir = tmp_path / "asset_loop_round_1"

    result = run_real_asset_test_harness(
        loop_path=EXAMPLE_LOOP,
        asset_profile_seed_path=EXAMPLE_SEED,
        feedback_json_path=EXAMPLE_FEEDBACK,
        consistency_review_json_path=EXAMPLE_CONSISTENCY_REVIEW,
        output_dir=output_dir,
        promotion_decision="promoted",
        promotion_rationale="Operator explicitly approved this profile version for round two context projection.",
        generated_at=GENERATED_AT,
        decided_at=DECIDED_AT,
        reviewed_at=REVIEWED_AT,
    )

    assert result["artifact_type"] == "agentflow_real_asset_test_run_harness"
    assert result["run_status"] == "completed_with_blocks"
    assert {item["block_id"] for item in result["blocks"]} == {"project_materials_missing"}
    assert result["promotion"]["decision"] == "promoted"
    assert result["context_projection"]["status"] == "ready"
    assert result["consistency_review"]["status"] == "ready_for_operator_review"
    assert result["provider_calls_started"] is False
    assert result["writes_long_term_memory"] is False
    assert result["writes_company_kb"] is False
    assert "not human acceptance" in result["non_claims"]
    assert "not business validation" in result["non_claims"]
    assert "not durable memory" in result["non_claims"]

    for name in _required_output_files():
        assert (output_dir / name).exists(), name

    selected = _read_json(output_dir / "review_screen_selected_files.json")
    assert selected["artifact_type"] == "agentflow_web_review_screen_selected_files"
    assert "asset_profile_context_projection.json" in selected["selected_files"]
    assert "asset_consistency_review.json" in selected["selected_files"]
    assert selected["provider_calls_started"] is False
    assert selected["writes_company_kb"] is False


def test_real_asset_test_run_harness_rejects_missing_explicit_decision(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="promotion_decision"):
        run_real_asset_test_harness(
            loop_path=EXAMPLE_LOOP,
            asset_profile_seed_path=EXAMPLE_SEED,
            feedback_json_path=EXAMPLE_FEEDBACK,
            consistency_review_json_path=EXAMPLE_CONSISTENCY_REVIEW,
            output_dir=tmp_path / "asset_loop_round_1",
            promotion_decision="",
            promotion_rationale="Operator explicitly approved this profile version for round two context projection.",
            generated_at=GENERATED_AT,
            decided_at=DECIDED_AT,
            reviewed_at=REVIEWED_AT,
        )


def test_real_asset_test_run_harness_cli_smoke(tmp_path: Path) -> None:
    output_dir = tmp_path / "asset_loop_round_1"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "asset-test-run-harness",
            "--asset-profile-seed",
            str(EXAMPLE_SEED),
            "--feedback-json",
            str(EXAMPLE_FEEDBACK),
            "--consistency-review-json",
            str(EXAMPLE_CONSISTENCY_REVIEW),
            "--promotion-decision",
            "promoted",
            "--promotion-rationale",
            "Operator explicitly approved this profile version for round two context projection.",
            "--generated-at",
            GENERATED_AT,
            "--decided-at",
            DECIDED_AT,
            "--reviewed-at",
            REVIEWED_AT,
            "--output",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Real asset test run harness: completed_with_blocks" in result.stdout
    assert "Provider calls: not started" in result.stdout
    assert "Writes long-term memory: false" in result.stdout
    assert "Writes Company KB: false" in result.stdout
    assert (output_dir / "real_asset_test_report.md").exists()


def _required_output_files() -> tuple[str, ...]:
    return (
        "operator_loop/production_memory_operator_loop_run.json",
        "asset_profiles.json",
        "asset_profile_readiness.json",
        "asset_test_package.json",
        "asset_test_package.md",
        "asset_feedback_event.json",
        "asset_profile_update_candidate.json",
        "asset_profile_promotion_decision.json",
        "asset_profile_version.json",
        "asset_profile_context_projection.json",
        "asset_consistency_review.json",
        "real_asset_test_report.md",
        "review_screen_selected_files.json",
    )


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
