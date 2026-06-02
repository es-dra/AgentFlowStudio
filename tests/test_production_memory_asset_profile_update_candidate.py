from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from agentflow.memory.production_asset_feedback import build_asset_feedback_event
from agentflow.memory.production_asset_profile_update_candidate import (
    ASSET_PROFILE_UPDATE_CANDIDATE_KIND,
    build_asset_profile_update_candidate,
    load_asset_feedback_event,
    write_asset_profile_update_candidate,
)
from agentflow.memory.production_asset_profiles import (
    build_asset_profile_test_package,
    load_asset_profile_seed,
    write_asset_profile_test_package,
)
from agentflow.memory.production_loop import load_production_memory_loop
from agentflow.memory.production_operator_loop import (
    build_production_memory_operator_loop_run,
    write_production_memory_operator_loop_run,
)
from narratocut.utils import write_json


EXAMPLE_LOOP = Path("examples/agentflow/production_memory_loop.example.json")
EXAMPLE_SEED = Path("examples/agentflow/production_memory_asset_profile_seed.example.json")
EXAMPLE_FEEDBACK = Path("examples/agentflow/production_memory_asset_feedback.example.json")
GENERATED_AT = "2026-06-02T00:10:00+08:00"


def test_asset_profile_update_candidate_drafts_structured_patch_without_promotion(tmp_path: Path) -> None:
    event = _asset_feedback_event(tmp_path)

    candidate = build_asset_profile_update_candidate(event, generated_at=GENERATED_AT)

    assert candidate["kind"] == ASSET_PROFILE_UPDATE_CANDIDATE_KIND
    assert candidate["candidate_id"] == (
        "asset-profile-update-candidate-asset-profile-character-lead-v1-character-identity-2026-06-02t00-10-00-08-00"
    )
    assert candidate["candidate_generation_status"] == "candidate_only"
    assert candidate["source_feedback_event_id"] == event["feedback_event_id"]
    assert candidate["profile_id"] == "asset-profile:character:lead:v1"
    assert candidate["profile_kind"] == "character"
    assert candidate["review_dimension"] == "character_identity"
    assert candidate["review_result"] == "partially_kept"
    assert candidate["proposed_profile_patch"]["patch_strategy"] == "operator_review_required"
    assert candidate["candidate_is_promoted_profile"] is False
    assert candidate["applies_profile_version"] is False
    assert candidate["creates_promotion_decision"] is False
    assert candidate["writes_long_term_memory"] is False
    assert candidate["writes_company_kb"] is False
    assert candidate["target_profile_next_context_unlocked"] is False
    patch_ops = candidate["proposed_profile_patch"]["patch_ops"]
    assert {
        "op": "add_unique",
        "path": "/negative_constraints/-",
        "value": "do not change age impression",
        "rationale": "Tester reported this violated constraint.",
        "evidence_refs": [event["feedback_event_id"]],
    } in patch_ops
    assert {
        "op": "add_unique",
        "path": "/evidence_refs/-",
        "value": event["feedback_event_id"],
        "rationale": "Link profile update candidate to the tester feedback event.",
        "evidence_refs": [event["feedback_event_id"]],
    } in patch_ops


def test_asset_profile_update_candidate_cannot_judge_stays_blocked_without_patch(tmp_path: Path) -> None:
    event = _asset_feedback_event(tmp_path)
    event["review_result"] = "cannot_judge"
    event["review_result_effect"] = "neutral"
    event["suggested_next_state"] = "cannot_judge"
    event["violated_constraints"] = []

    candidate = build_asset_profile_update_candidate(event, generated_at=GENERATED_AT)

    assert candidate["candidate_generation_status"] == "blocked_cannot_judge"
    assert candidate["proposed_profile_patch"]["patch_ops"] == []
    assert candidate["candidate_is_promoted_profile"] is False
    assert candidate["creates_promotion_decision"] is False


def test_asset_profile_update_candidate_kept_no_change_has_no_patch(tmp_path: Path) -> None:
    event = _asset_feedback_event(tmp_path)
    event["review_result"] = "kept"
    event["review_result_effect"] = "positive_signal"
    event["suggested_next_state"] = "no_change"
    event["violated_constraints"] = []

    candidate = build_asset_profile_update_candidate(event, generated_at=GENERATED_AT)

    assert candidate["candidate_generation_status"] == "no_update_recommended"
    assert candidate["proposed_profile_patch"]["patch_ops"] == []
    assert candidate["non_claims"][0] == "not a profile version"


def test_asset_profile_update_candidate_negative_feedback_without_patch_is_blocked(tmp_path: Path) -> None:
    event = _asset_feedback_event(tmp_path)
    event["review_result"] = "not_kept"
    event["review_result_effect"] = "needs_review"
    event["violated_constraints"] = []

    candidate = build_asset_profile_update_candidate(event, generated_at=GENERATED_AT)

    assert candidate["candidate_generation_status"] == "blocked_missing_patch_ops"
    assert candidate["proposed_profile_patch"]["patch_ops"] == []
    assert candidate["creates_promotion_decision"] is False


def test_asset_profile_update_candidate_rejects_wrong_kind(tmp_path: Path) -> None:
    event = _asset_feedback_event(tmp_path)
    event["kind"] = "agentflow_wrong_kind"

    with pytest.raises(ValueError, match="asset profile update candidate requires kind"):
        build_asset_profile_update_candidate(event, generated_at=GENERATED_AT)


def test_asset_profile_update_candidate_rejects_feedback_that_created_promotion(tmp_path: Path) -> None:
    event = _asset_feedback_event(tmp_path)
    event["creates_promotion_decision"] = True

    with pytest.raises(ValueError, match="source feedback to create no promotion decision"):
        build_asset_profile_update_candidate(event, generated_at=GENERATED_AT)


def test_asset_profile_update_candidate_rejects_private_fragments(tmp_path: Path) -> None:
    event_path = tmp_path / "asset_feedback_event.json"
    event = _asset_feedback_event(tmp_path)
    event["drift_observations"] = [r"Leaked reference from D:\private\character.png"]
    event_path.write_text(json.dumps(event), encoding="utf-8")

    with pytest.raises(ValueError, match="private fragments"):
        load_asset_feedback_event(event_path)


def test_asset_profile_update_candidate_does_not_mutate_source_event(tmp_path: Path) -> None:
    event = _asset_feedback_event(tmp_path)
    before = deepcopy(event)

    build_asset_profile_update_candidate(event, generated_at=GENERATED_AT)

    assert event == before


def test_asset_profile_update_candidate_cli_writes_json_and_markdown(tmp_path: Path) -> None:
    event_path = write_json(tmp_path / "asset_feedback_event.json", _asset_feedback_event(tmp_path / "source"))
    output_dir = tmp_path / "candidate"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "production-memory-loop-draft-asset-profile-update-candidate",
            "--asset-feedback-event",
            str(event_path),
            "--generated-at",
            GENERATED_AT,
            "--output",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Asset profile update candidate: candidate_only" in result.stdout
    assert "Creates promotion decision: false" in result.stdout
    assert "Applies profile version: false" in result.stdout
    candidate = json.loads((output_dir / "asset_profile_update_candidate.json").read_text(encoding="utf-8"))
    assert candidate["kind"] == ASSET_PROFILE_UPDATE_CANDIDATE_KIND
    assert candidate["candidate_is_promoted_profile"] is False
    assert (output_dir / "asset_profile_update_candidate.md").exists()


def test_asset_profile_update_candidate_writer_keeps_output_safe(tmp_path: Path) -> None:
    candidate = build_asset_profile_update_candidate(_asset_feedback_event(tmp_path), generated_at=GENERATED_AT)

    written = write_asset_profile_update_candidate(candidate, tmp_path / "candidate")
    serialized = "\n".join(path.read_text(encoding="utf-8") for path in written)

    assert "D:\\private" not in serialized
    assert "api_key" not in serialized.lower()
    assert "signed_url" not in serialized.lower()


def _asset_feedback_event(tmp_path: Path) -> dict:
    package_dir = _write_asset_package(tmp_path)
    return build_asset_feedback_event(
        asset_profiles=json.loads((package_dir / "asset_profiles.json").read_text(encoding="utf-8")),
        asset_profile_readiness=json.loads((package_dir / "asset_profile_readiness.json").read_text(encoding="utf-8")),
        feedback_fixture=json.loads(EXAMPLE_FEEDBACK.read_text(encoding="utf-8")),
        generated_at="2026-06-02T00:00:00+08:00",
    )


def _write_asset_package(tmp_path: Path) -> Path:
    loop = load_production_memory_loop(EXAMPLE_LOOP)
    operator_result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-02T00:00:00+08:00",
        source_kb_status="restructuring_or_unknown",
        draft_next_pass_result=True,
    )
    operator_dir = tmp_path / "operator_loop"
    write_production_memory_operator_loop_run(
        result=operator_result,
        output_dir=operator_dir,
        write_run_package=True,
        write_run_package_check=True,
    )
    bundle = build_asset_profile_test_package(
        operator_artifact_path=operator_dir / "production_memory_operator_loop_run.json",
        asset_profile_seed=load_asset_profile_seed(EXAMPLE_SEED),
        generated_at="2026-06-02T00:00:00+08:00",
    )
    package_dir = tmp_path / "asset_test_package"
    write_asset_profile_test_package(bundle, package_dir)
    return package_dir
