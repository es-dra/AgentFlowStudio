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
    assert evidence["quality_gate"]["verified_acceptance_artifact"] is None
    assert evidence["non_claims"]["provider_smoke"] is False
    assert evidence["non_claims"]["generated_media_quality"] is False
    assert evidence["non_claims"]["human_acceptance"] is False
    assert evidence["non_claims"]["business_validation"] is False
    assert len(evidence["delivery_sha256"]) == 64
    assert any(edge["relation"] == "creator_selected_and_revised" for edge in evidence["lineage"])
    relations = {edge["relation"] for edge in evidence["lineage"]}
    assert {
        "project_to_character_asset",
        "script_to_storyboard",
        "character_asset_to_shot",
        "creator_decision_reviewed",
        "revision_included_in_delivery",
        "quality_review_approved_delivery",
    } <= relations
    lineage = {
        (edge["source_ref"], edge["target_ref"], edge["relation"])
        for edge in evidence["lineage"]
    }
    project_id = delivery["project"]["project_id"]
    script_id = delivery["script"]["script_id"]
    storyboard_id = delivery["storyboard"]["storyboard_id"]
    delivery_id = delivery["delivery_id"]
    for asset in delivery["character_assets"]:
        assert (project_id, asset["asset_id"], "project_to_character_asset") in lineage
        for shot in delivery["shots"]:
            assert (asset["asset_id"], shot["shot_id"], "character_asset_to_shot") in lineage
    assert (script_id, storyboard_id, "script_to_storyboard") in lineage
    for revision in delivery["selected_revisions"]:
        assert (revision["revision_id"], delivery_id, "revision_included_in_delivery") in lineage
    assert (
        delivery["quality_review_ref"],
        delivery_id,
        "quality_review_approved_delivery",
    ) in lineage
    state = json.loads(paths["state"].read_text(encoding="utf-8"))
    assert delivery["source_state_chain_digest"] == evidence["source_state_chain_digest"]
    assert state["artifacts"]["export"]["source_state_chain_digest"] == evidence["source_state_chain_digest"]
    assert state["artifacts"]["export"]["delivery_sha256"] == evidence["delivery_sha256"]
    assert len(state["artifacts"]["export"]["evidence_sha256"]) == 64


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


def test_checkpoint_can_reopen_repeatedly_without_an_intervening_advance(tmp_path: Path) -> None:
    project = _load_model("project.example.json", ProjectIP)
    first = DeterministicProductionSlice(project, tmp_path)
    first.advance_to_candidates(fail_after_stage=None)
    initial_sequence = first.state["checkpoint_integrity"]["sequence"]

    recovered_once = DeterministicProductionSlice(project, tmp_path)
    first_recovery_digest = recovered_once.state["checkpoint_integrity"]["chain_digest"]
    recovered_twice = DeterministicProductionSlice(project, tmp_path)

    assert recovered_once.state["recovery_count"] == 1
    assert recovered_once.state["checkpoint_integrity"]["sequence"] == initial_sequence + 1
    assert recovered_twice.state["recovery_count"] == 2
    assert recovered_twice.state["checkpoint_integrity"]["sequence"] == initial_sequence + 2
    assert recovered_twice.state["checkpoint_integrity"]["previous_chain_digest"] == first_recovery_digest


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


def test_untrusted_human_review_fields_cannot_claim_human_acceptance(tmp_path: Path) -> None:
    project = _load_model("project.example.json", ProjectIP)
    run = DeterministicProductionSlice(project, tmp_path)
    run.advance_to_candidates()
    run.record_creator_decision(_load_model("creator_decision.example.json", CreatorDecision))
    review = _load_model("quality_review.example.json", QualityReview).model_copy(
        update={"reviewer_id": "attacker_claims_owner", "review_mode": "human"}
    )
    run.record_quality_review(review)

    paths = run.export()
    evidence = json.loads(paths["evidence"].read_text(encoding="utf-8"))
    assert evidence["quality_gate"]["human_acceptance_claimed"] is False
    assert evidence["quality_gate"]["verified_acceptance_artifact"] is None
    assert evidence["non_claims"]["human_acceptance"] is False


def test_review_for_old_selection_fails_closed_after_creator_subject_changes(tmp_path: Path) -> None:
    project = _load_model("project.example.json", ProjectIP)
    run = DeterministicProductionSlice(project, tmp_path)
    run.advance_to_candidates()
    original = _load_model("creator_decision.example.json", CreatorDecision)
    changed_ids = list(original.selected_candidate_ids)
    changed_ids[0] = next(
        item["candidate_id"]
        for item in run.state["artifacts"]["candidates"]
        if item["shot_id"] == "shot_001" and item["candidate_id"] != changed_ids[0]
    )
    run.record_creator_decision(original.model_copy(update={"selected_candidate_ids": changed_ids}))

    stale_review = _load_model("quality_review.example.json", QualityReview)
    with pytest.raises(ValueError, match="subject digest does not match"):
        run.record_quality_review(stale_review)


@pytest.mark.parametrize("tamper_kind", ["state", "artifacts", "lineage"])
def test_tampered_checkpoint_contents_fail_integrity_validation(tmp_path: Path, tamper_kind: str) -> None:
    project = _load_model("project.example.json", ProjectIP)
    run = DeterministicProductionSlice(project, tmp_path)
    run.advance_to_candidates()
    checkpoint_path = tmp_path / "production_state.json"
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    if tamper_kind == "state":
        checkpoint["stage"] = "initialized"
    elif tamper_kind == "artifacts":
        checkpoint["artifacts"]["candidates"][0]["treatment"] = "silently tampered"
    else:
        checkpoint["lineage"].pop()
    checkpoint_path.write_text(json.dumps(checkpoint), encoding="utf-8")

    with pytest.raises(ValueError, match="checkpoint state integrity validation failed"):
        DeterministicProductionSlice(project, tmp_path)


@pytest.mark.parametrize("tamper_kind", ["state", "artifacts", "lineage"])
def test_persisted_checkpoint_mutation_after_quality_gate_blocks_export(tmp_path: Path, tamper_kind: str) -> None:
    project = _load_model("project.example.json", ProjectIP)
    run = DeterministicProductionSlice(project, tmp_path)
    run.advance_to_candidates()
    run.record_creator_decision(_load_model("creator_decision.example.json", CreatorDecision))
    run.record_quality_review(_load_model("quality_review.example.json", QualityReview))
    checkpoint_path = tmp_path / "production_state.json"
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    if tamper_kind == "state":
        checkpoint["stage"] = "exported"
    elif tamper_kind == "artifacts":
        checkpoint["artifacts"]["selected_revisions"][0]["revision_note"] = "post-gate mutation"
    else:
        checkpoint["lineage"].pop()
    checkpoint_path.write_text(json.dumps(checkpoint), encoding="utf-8")

    with pytest.raises(ValueError, match="checkpoint state integrity validation failed"):
        run.export()


@pytest.mark.parametrize("tamper_kind", ["state", "artifacts", "lineage"])
def test_in_memory_mutation_after_quality_gate_blocks_export(tmp_path: Path, tamper_kind: str) -> None:
    project = _load_model("project.example.json", ProjectIP)
    run = DeterministicProductionSlice(project, tmp_path)
    run.advance_to_candidates()
    run.record_creator_decision(_load_model("creator_decision.example.json", CreatorDecision))
    run.record_quality_review(_load_model("quality_review.example.json", QualityReview))
    if tamper_kind == "state":
        run.state["stage"] = "exported"
    elif tamper_kind == "artifacts":
        run.state["artifacts"]["selected_revisions"][0]["revision_note"] = "post-gate mutation"
    else:
        run.state["lineage"].pop()

    with pytest.raises(ValueError, match="checkpoint state integrity validation failed"):
        run.export()
