from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentflow_studio.production.vertical_slice import (
    CreatorDecision,
    DeterministicProductionSlice,
    ProjectIP,
    QualityReview,
)


EXAMPLE_DIR = Path("examples/deterministic_vertical_slice")


def _load_model(name: str, model):
    return model.model_validate(json.loads((EXAMPLE_DIR / name).read_text(encoding="utf-8")))


def test_deterministic_vertical_slice_exports_concrete_delivery_and_evidence(tmp_path: Path) -> None:
    paths = DeterministicProductionSlice.from_files(
        EXAMPLE_DIR / "project.example.json",
        EXAMPLE_DIR / "creator_decision.example.json",
        EXAMPLE_DIR / "quality_review.example.json",
        tmp_path,
    )

    delivery = json.loads(paths["delivery"].read_text(encoding="utf-8"))
    evidence = json.loads(paths["evidence"].read_text(encoding="utf-8"))
    expected_dir = EXAMPLE_DIR / "expected_export"
    assert delivery == json.loads((expected_dir / "production_delivery.json").read_text(encoding="utf-8"))
    assert evidence == json.loads((expected_dir / "evidence.json").read_text(encoding="utf-8"))
    assert delivery["artifact_type"] == "deterministic_storyboard_delivery"
    assert len(delivery["script"]["beats"]) == 3
    assert len(delivery["character_assets"]) == 1
    assert len(delivery["shots"]) == 3
    assert len(delivery["selected_revisions"]) == 3
    assert evidence["creator_in_loop"] == {
        "decision_ref": "fixture_creator_decision_001",
        "revision_count": 2,
        "selected_count": 3,
    }
    assert evidence["quality_gate"]["review_mode"] == "fixture"
    assert evidence["quality_gate"]["human_acceptance_claimed"] is False
    assert evidence["non_claims"]["provider_smoke"] is False
    assert evidence["non_claims"]["generated_media_quality"] is False
    assert evidence["non_claims"]["human_acceptance"] is False
    assert evidence["non_claims"]["business_validation"] is False
    assert len(evidence["delivery_sha256"]) == 64
    assert any(edge["relation"] == "creator_selected_and_revised" for edge in evidence["lineage"])


def test_export_is_blocked_until_creator_and_quality_gates_complete(tmp_path: Path) -> None:
    project = _load_model("project.example.json", ProjectIP)
    run = DeterministicProductionSlice(project, tmp_path)
    run.advance_to_candidates()

    with pytest.raises(ValueError, match="quality review is required"):
        run.export()

    run.record_creator_decision(_load_model("creator_decision.example.json", CreatorDecision))
    with pytest.raises(ValueError, match="quality review is required"):
        run.export()


def test_rejected_quality_gate_blocks_export(tmp_path: Path) -> None:
    project = _load_model("project.example.json", ProjectIP)
    run = DeterministicProductionSlice(project, tmp_path)
    run.advance_to_candidates()
    run.record_creator_decision(_load_model("creator_decision.example.json", CreatorDecision))
    review = _load_model("quality_review.example.json", QualityReview).model_copy(update={"decision": "reject"})
    run.record_quality_review(review)

    with pytest.raises(ValueError, match="rejected export"):
        run.export()


def test_checkpoint_recovery_resumes_without_rebuilding_completed_stages(tmp_path: Path) -> None:
    project = _load_model("project.example.json", ProjectIP)
    first = DeterministicProductionSlice(project, tmp_path)
    with pytest.raises(RuntimeError, match="after storyboard"):
        first.advance_to_candidates(fail_after_stage="storyboard")
    checkpoint = json.loads((tmp_path / "production_state.json").read_text(encoding="utf-8"))
    original_storyboard = checkpoint["artifacts"]["storyboard"]

    recovered = DeterministicProductionSlice(project, tmp_path)
    recovered.advance_to_candidates()
    assert recovered.state["recovery_count"] == 1
    assert recovered.state["artifacts"]["storyboard"] == original_storyboard
    assert recovered.state["stage"] == "candidates"


def test_completed_run_is_replayable_without_duplicate_lineage(tmp_path: Path) -> None:
    first = DeterministicProductionSlice.from_files(
        EXAMPLE_DIR / "project.example.json",
        EXAMPLE_DIR / "creator_decision.example.json",
        EXAMPLE_DIR / "quality_review.example.json",
        tmp_path,
    )
    first_evidence = json.loads(first["evidence"].read_text(encoding="utf-8"))

    second = DeterministicProductionSlice.from_files(
        EXAMPLE_DIR / "project.example.json",
        EXAMPLE_DIR / "creator_decision.example.json",
        EXAMPLE_DIR / "quality_review.example.json",
        tmp_path,
    )
    second_evidence = json.loads(second["evidence"].read_text(encoding="utf-8"))

    assert second_evidence["lineage"] == first_evidence["lineage"]
    assert second_evidence["recovery"]["recovery_count"] == 1


def test_creator_must_select_exactly_one_candidate_for_every_shot(tmp_path: Path) -> None:
    project = _load_model("project.example.json", ProjectIP)
    run = DeterministicProductionSlice(project, tmp_path)
    run.advance_to_candidates()
    incomplete = CreatorDecision(
        decision_id="incomplete",
        creator_id="fixture_creator",
        selected_candidate_ids=[run.state["artifacts"]["candidates"][0]["candidate_id"]],
    )

    with pytest.raises(ValueError, match="exactly one candidate for every shot"):
        run.record_creator_decision(incomplete)
