from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from agentflow_studio.production.vertical_slice import (
    CHECKPOINT_CHAIN_INPUT_FIELDS,
    CHECKPOINT_INTEGRITY_FIELDS,
    CHECKPOINT_STATE_FIELDS,
    CHECKPOINT_STATE_SEAL_FIELDS,
    CreatorDecision,
    DeterministicProductionSlice,
    ProjectIP,
    QualityReview,
)


EXAMPLE_DIR = Path("examples/deterministic_vertical_slice")


def _load_model(name: str, model):
    return model.model_validate(json.loads((EXAMPLE_DIR / name).read_text(encoding="utf-8")))


def _run_to_quality_gate(output_dir: Path) -> tuple[ProjectIP, DeterministicProductionSlice]:
    project = _load_model("project.example.json", ProjectIP)
    run = DeterministicProductionSlice(project, output_dir)
    run.advance_to_candidates()
    run.record_creator_decision(_load_model("creator_decision.example.json", CreatorDecision))
    run.record_quality_review(_load_model("quality_review.example.json", QualityReview))
    return project, run


def _leaf_paths(value, path=()):
    if isinstance(value, dict):
        for key in sorted(value):
            yield from _leaf_paths(value[key], (*path, key))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _leaf_paths(item, (*path, index))
    else:
        yield path


def _set_path(value, path, replacement) -> None:
    target = value
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = replacement


def _mutated_scalar(value):
    if isinstance(value, bool):
        return not value
    if isinstance(value, int):
        return value + 1
    if isinstance(value, str):
        return f"{value}__tampered"
    if value is None:
        return "tampered"
    raise AssertionError(f"unsupported checkpoint scalar in mutation matrix: {type(value).__name__}")


def _value_at_path(value, path):
    for part in path:
        value = value[part]
    return value


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


def test_fresh_checkpoint_can_reopen_before_the_first_advance(tmp_path: Path) -> None:
    project = _load_model("project.example.json", ProjectIP)
    first = DeterministicProductionSlice(project, tmp_path)
    initial = json.loads((tmp_path / "production_state.json").read_text(encoding="utf-8"))
    initial_integrity = initial["checkpoint_integrity"]

    assert first.state == initial
    assert initial["stage"] == "initialized"
    assert initial["recovery_count"] == 0
    assert initial_integrity["algorithm"] == "sha256"
    assert initial_integrity["sequence"] == 0
    assert initial_integrity["previous_chain_digest"] is None
    assert len(initial_integrity["state_digest"]) == 64
    assert len(initial_integrity["chain_digest"]) == 64
    reference = DeterministicProductionSlice(project, tmp_path / "reference")
    assert reference.state == initial

    recovered = DeterministicProductionSlice(project, tmp_path)
    persisted = json.loads((tmp_path / "production_state.json").read_text(encoding="utf-8"))

    assert recovered.state == persisted
    assert recovered.state["stage"] == "initialized"
    assert recovered.state["recovery_count"] == 1
    assert recovered.state["checkpoint_integrity"]["sequence"] == 1
    assert (
        recovered.state["checkpoint_integrity"]["previous_chain_digest"]
        == initial_integrity["chain_digest"]
    )


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


def test_checkpoint_security_inventory_covers_state_and_every_integrity_field(tmp_path: Path) -> None:
    _, run = _run_to_quality_gate(tmp_path)
    checkpoint = json.loads((tmp_path / "production_state.json").read_text(encoding="utf-8"))

    assert set(checkpoint) == CHECKPOINT_STATE_FIELDS
    assert set(checkpoint["checkpoint_integrity"]) == CHECKPOINT_INTEGRITY_FIELDS
    assert CHECKPOINT_STATE_SEAL_FIELDS == CHECKPOINT_STATE_FIELDS - {"checkpoint_integrity"}
    assert CHECKPOINT_CHAIN_INPUT_FIELDS == CHECKPOINT_INTEGRITY_FIELDS - {"chain_digest"}
    assert {
        "schema_version",
        "checkpoint_model_version",
        "run_id",
        "project_fingerprint",
        "stage",
        "recovery_count",
        "artifacts",
        "lineage",
    } <= CHECKPOINT_STATE_SEAL_FIELDS

    checkpoint["checkpoint_integrity"]["future_unsealed_field"] = "must fail closed"
    (tmp_path / "production_state.json").write_text(json.dumps(checkpoint), encoding="utf-8")
    with pytest.raises(ValueError, match="checkpoint integrity field inventory is invalid"):
        run.export()


def test_each_checkpoint_integrity_field_mutation_blocks_reopen_and_export(tmp_path: Path) -> None:
    project, run = _run_to_quality_gate(tmp_path)
    checkpoint_path = tmp_path / "production_state.json"
    original = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    mutations = {
        "algorithm": "sha512",
        "sequence": -100,
        "previous_chain_digest": "0" * 64,
        "state_digest": "0" * 64,
        "chain_digest": "0" * 64,
    }

    assert set(mutations) == CHECKPOINT_INTEGRITY_FIELDS
    assert original["stage"] == "quality_gate"
    assert original["checkpoint_integrity"]["sequence"] == 5
    for field, replacement in mutations.items():
        mutated = copy.deepcopy(original)
        mutated["checkpoint_integrity"][field] = replacement
        checkpoint_path.write_text(json.dumps(mutated), encoding="utf-8")

        with pytest.raises(ValueError):
            run.export()
        assert not (tmp_path / "production_delivery.json").exists()
        assert not (tmp_path / "evidence.json").exists()
        with pytest.raises(ValueError):
            DeterministicProductionSlice(project, tmp_path)
        checkpoint_path.write_text(json.dumps(original), encoding="utf-8")


@pytest.mark.parametrize(
    ("replacement", "message"),
    [
        (-1, "must be a nonnegative integer"),
        (True, "must be a nonnegative integer"),
        ("5", "must be a nonnegative integer"),
        (5.0, "must be a nonnegative integer"),
        (4, "precedes stage and recovery count"),
        (6, "checkpoint chain integrity validation failed"),
    ],
)
def test_checkpoint_sequence_type_range_and_monotonic_consistency_fail_closed(
    tmp_path: Path, replacement, message: str
) -> None:
    project, _ = _run_to_quality_gate(tmp_path)
    checkpoint_path = tmp_path / "production_state.json"
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    checkpoint["checkpoint_integrity"]["sequence"] = replacement
    checkpoint_path.write_text(json.dumps(checkpoint), encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        DeterministicProductionSlice(project, tmp_path)


def test_checkpoint_previous_link_semantics_fail_closed(tmp_path: Path) -> None:
    project = _load_model("project.example.json", ProjectIP)
    DeterministicProductionSlice(project, tmp_path)
    checkpoint_path = tmp_path / "production_state.json"
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    checkpoint["checkpoint_integrity"]["previous_chain_digest"] = "0" * 64
    checkpoint_path.write_text(json.dumps(checkpoint), encoding="utf-8")

    with pytest.raises(ValueError, match="initial checkpoint cannot reference"):
        DeterministicProductionSlice(project, tmp_path)


def test_in_memory_sequence_tamper_cannot_be_resealed_on_advance(tmp_path: Path) -> None:
    project = _load_model("project.example.json", ProjectIP)
    run = DeterministicProductionSlice(project, tmp_path)
    checkpoint_path = tmp_path / "production_state.json"
    original = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    run.state["checkpoint_integrity"]["sequence"] = 10

    with pytest.raises(ValueError, match="previous checkpoint"):
        run.advance_to_candidates()
    assert json.loads(checkpoint_path.read_text(encoding="utf-8")) == original


def test_each_quality_gate_checkpoint_leaf_mutation_blocks_reopen_and_export(tmp_path: Path) -> None:
    project, run = _run_to_quality_gate(tmp_path)
    checkpoint_path = tmp_path / "production_state.json"
    original = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    sealed_state = {key: original[key] for key in CHECKPOINT_STATE_SEAL_FIELDS}
    paths = list(_leaf_paths(sealed_state))

    assert len(paths) > 100
    assert {path[0] for path in paths} == CHECKPOINT_STATE_SEAL_FIELDS
    for path in paths:
        mutated = copy.deepcopy(original)
        replacement = _mutated_scalar(_value_at_path(mutated, path))
        _set_path(mutated, path, replacement)
        checkpoint_path.write_text(json.dumps(mutated), encoding="utf-8")

        with pytest.raises(ValueError):
            run.export()
        assert not (tmp_path / "production_delivery.json").exists(), path
        assert not (tmp_path / "evidence.json").exists(), path
        with pytest.raises(ValueError):
            DeterministicProductionSlice(project, tmp_path)
        checkpoint_path.write_text(json.dumps(original), encoding="utf-8")


def test_each_exported_checkpoint_leaf_mutation_blocks_reopen(tmp_path: Path) -> None:
    project, run = _run_to_quality_gate(tmp_path)
    run.export()
    checkpoint_path = tmp_path / "production_state.json"
    original = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    sealed_state = {key: original[key] for key in CHECKPOINT_STATE_SEAL_FIELDS}
    paths = list(_leaf_paths(sealed_state))

    assert original["stage"] == "exported"
    assert {"delivery_ref", "delivery_sha256", "evidence_ref", "evidence_sha256", "source_state_chain_digest"} == set(
        original["artifacts"]["export"]
    )
    for path in paths:
        mutated = copy.deepcopy(original)
        replacement = _mutated_scalar(_value_at_path(mutated, path))
        _set_path(mutated, path, replacement)
        checkpoint_path.write_text(json.dumps(mutated), encoding="utf-8")

        with pytest.raises(ValueError):
            DeterministicProductionSlice(project, tmp_path)
        checkpoint_path.write_text(json.dumps(original), encoding="utf-8")


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
