from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from agentflow.memory.production_asset_consistency_review import (
    ASSET_CONSISTENCY_REVIEW_FIXTURE_KIND,
    ASSET_CONSISTENCY_REVIEW_KIND,
    build_asset_consistency_review,
    load_asset_consistency_review_fixture,
    write_asset_consistency_review,
)
from agentflow.memory.production_asset_profile_context_projection import build_asset_profile_context_projection
from agentflow.memory.production_asset_profile_promotion import build_asset_profile_promotion_review
from agentflow_studio.utils import write_json
from tests.production_memory_asset_profile_promotion_helpers import (
    GENERATED_AT,
    asset_profiles_and_candidate,
)

EXAMPLE_CONSISTENCY_FIXTURE = Path("examples/agentflow/production_memory_asset_consistency_review.example.json")


def test_asset_consistency_review_happy_path_keeps_character_anchor(tmp_path: Path) -> None:
    projection = _projection(tmp_path)
    fixture = _fixture(projection)

    review = build_asset_consistency_review(
        asset_profile_context_projection=projection,
        consistency_fixture=fixture,
        reviewed_at="2026-06-03T01:00:00+08:00",
    )

    assert review["kind"] == ASSET_CONSISTENCY_REVIEW_KIND
    assert review["review_status"] == "ready_for_operator_review"
    assert review["overall_consistency_result"] == "kept"
    assert review["consistency_findings"][0]["profile_ref"] == "asset-profile:character:lead:v2"
    assert review["consistency_findings"][0]["review_result_effect"] == "positive_signal"
    assert review["included_profile_refs"] == projection["included_refs"]
    assert review["blocked_profile_refs"] == projection["blocked_refs"]
    assert review["creates_asset_feedback_event"] is False
    assert review["creates_profile_update_candidate"] is False
    assert review["creates_promotion_decision"] is False
    assert review["writes_long_term_memory"] is False
    assert review["writes_company_kb"] is False


def test_asset_consistency_review_blocks_unknown_profile_ref(tmp_path: Path) -> None:
    projection = _projection(tmp_path)
    fixture = _fixture(projection)
    fixture["review_items"][0]["profile_ref"] = "asset-profile:character:unknown"

    review = build_asset_consistency_review(
        asset_profile_context_projection=projection,
        consistency_fixture=fixture,
        reviewed_at="2026-06-03T01:00:00+08:00",
    )

    assert review["review_status"] == "blocked"
    assert review["consistency_findings"] == []
    assert review["blocked_findings"][0]["reason"] == "unknown_profile_ref"
    assert review["blocked_findings"][0]["profile_ref"] == "asset-profile:character:unknown"


def test_asset_consistency_review_blocks_superseded_profile_ref(tmp_path: Path) -> None:
    projection = _projection(tmp_path)
    fixture = _fixture(projection)
    fixture["review_items"][0]["profile_ref"] = "asset-profile:character:lead:v1"

    review = build_asset_consistency_review(
        asset_profile_context_projection=projection,
        consistency_fixture=fixture,
        reviewed_at="2026-06-03T01:00:00+08:00",
    )

    assert review["review_status"] == "blocked"
    assert review["consistency_findings"] == []
    assert review["blocked_findings"][0]["reason"] == "blocked_profile_ref"
    assert review["blocked_findings"][0]["source_block_reason"] == "superseded_by_profile_version"


def test_asset_consistency_review_cannot_judge_is_neutral(tmp_path: Path) -> None:
    projection = _projection(tmp_path)
    fixture = _fixture(projection)
    fixture["review_items"][0]["review_result"] = "cannot_judge"
    fixture["review_items"][0]["failure_attribution"] = "unknown"
    fixture["review_items"][0]["suggested_next_state"] = "cannot_judge"

    review = build_asset_consistency_review(
        asset_profile_context_projection=projection,
        consistency_fixture=fixture,
        reviewed_at="2026-06-03T01:00:00+08:00",
    )

    assert review["overall_consistency_result"] == "cannot_judge"
    assert review["consistency_findings"][0]["review_result_effect"] == "neutral"
    assert review["creates_asset_feedback_event"] is False


def test_asset_consistency_review_rejects_projection_mismatch(tmp_path: Path) -> None:
    projection = _projection(tmp_path)
    fixture = _fixture(projection)
    fixture["source_context_projection_ref"] = "asset-profile-context-projection:other"

    with pytest.raises(ValueError, match="source_context_projection_ref"):
        build_asset_consistency_review(
            asset_profile_context_projection=projection,
            consistency_fixture=fixture,
            reviewed_at="2026-06-03T01:00:00+08:00",
        )


def test_asset_consistency_review_rejects_private_or_provider_fragments(tmp_path: Path) -> None:
    projection = _projection(tmp_path)
    fixture = _fixture(projection)
    fixture["review_items"][0]["evidence_refs"] = ["provider result URL: signed_url"]

    with pytest.raises(ValueError, match="unsafe"):
        build_asset_consistency_review(
            asset_profile_context_projection=projection,
            consistency_fixture=fixture,
            reviewed_at="2026-06-03T01:00:00+08:00",
        )


def test_asset_consistency_review_cli_smoke(tmp_path: Path) -> None:
    projection = _projection(tmp_path)
    fixture = _fixture(projection)
    projection_path = write_json(tmp_path / "asset_profile_context_projection.json", projection)
    fixture_path = write_json(tmp_path / "asset_consistency_review_fixture.json", fixture)
    output_dir = tmp_path / "review"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "production-memory-loop-review-asset-consistency",
            "--asset-profile-context-projection",
            str(projection_path),
            "--consistency-review-json",
            str(fixture_path),
            "--reviewed-at",
            "2026-06-03T01:00:00+08:00",
            "--output",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Asset consistency review: ready_for_operator_review" in result.stdout
    assert (output_dir / "asset_consistency_review.json").exists()
    assert (output_dir / "asset_consistency_review.md").exists()
    payload = json.loads((output_dir / "asset_consistency_review.json").read_text(encoding="utf-8"))
    assert payload["kind"] == ASSET_CONSISTENCY_REVIEW_KIND


def test_committed_asset_consistency_review_fixture_is_sanitized_and_builds(tmp_path: Path) -> None:
    projection = _projection(tmp_path)
    fixture = load_asset_consistency_review_fixture(EXAMPLE_CONSISTENCY_FIXTURE)

    review = build_asset_consistency_review(
        asset_profile_context_projection=projection,
        consistency_fixture=fixture,
        reviewed_at="2026-06-03T01:00:00+08:00",
    )

    raw = EXAMPLE_CONSISTENCY_FIXTURE.read_text(encoding="utf-8").lower()
    assert "d:\\" not in raw
    assert "c:\\" not in raw
    assert "signed_url" not in raw
    assert "api_key" not in raw
    assert ".png" not in raw
    assert ".mp4" not in raw
    assert review["review_status"] == "ready_for_operator_review"


def _projection(tmp_path: Path) -> dict:
    asset_profiles, candidate = asset_profiles_and_candidate(tmp_path)
    _decision, version = build_asset_profile_promotion_review(
        asset_profiles=asset_profiles,
        update_candidate=candidate,
        decision="promoted",
        rationale="Operator approved the structured profile patch for tester review continuity.",
        reviewer_role="operator",
        decided_at=GENERATED_AT,
    )
    assert version is not None
    return build_asset_profile_context_projection(
        asset_profile_versions=[version],
        generated_at="2026-06-03T00:30:00+08:00",
    )


def _fixture(projection: dict) -> dict:
    return {
        "kind": ASSET_CONSISTENCY_REVIEW_FIXTURE_KIND,
        "artifact_type": ASSET_CONSISTENCY_REVIEW_FIXTURE_KIND,
        "schema_version": projection["schema_version"],
        "fixture_id": "asset-consistency-fixture:character-lead-cross-scene-001",
        "project_id": projection["project_id"],
        "source_context_projection_ref": projection["projection_id"],
        "source_result_ref": "next-pass-result:sanitized-cross-scene-001",
        "source_feedback_input_type": "json_fixture",
        "comparison_scope": "cross_scene",
        "review_items": [
            {
                "profile_ref": "asset-profile:character:lead:v2",
                "profile_kind": "character",
                "output_refs": ["output:scene-001", "output:scene-002"],
                "review_dimension": "character_identity",
                "review_result": "kept",
                "failure_attribution": "unknown",
                "drift_observations": [],
                "violated_constraints": [],
                "evidence_refs": ["output:scene-001", "output:scene-002"],
                "suggested_next_state": "no_change",
            }
        ],
    }
