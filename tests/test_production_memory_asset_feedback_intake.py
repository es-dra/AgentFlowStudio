from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from agentflow.memory.production_asset_feedback import (
    ASSET_FEEDBACK_EVENT_KIND,
    build_asset_feedback_event,
    load_asset_feedback_fixture,
    write_asset_feedback_event,
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


EXAMPLE_LOOP = Path("examples/agentflow/production_memory_loop.example.json")
EXAMPLE_SEED = Path("examples/agentflow/production_memory_asset_profile_seed.example.json")
EXAMPLE_FEEDBACK = Path("examples/agentflow/production_memory_asset_feedback.example.json")
GENERATED_AT = "2026-06-02T00:00:00+08:00"


def test_asset_feedback_event_records_tester_feedback_without_memory_or_promotion(tmp_path: Path) -> None:
    package_dir = _write_asset_package(tmp_path)
    fixture = _feedback_fixture()

    event = build_asset_feedback_event(
        asset_profiles=json.loads((package_dir / "asset_profiles.json").read_text(encoding="utf-8")),
        asset_profile_readiness=json.loads((package_dir / "asset_profile_readiness.json").read_text(encoding="utf-8")),
        feedback_fixture=fixture,
        generated_at=GENERATED_AT,
    )

    assert event["kind"] == ASSET_FEEDBACK_EVENT_KIND
    assert event["feedback_event_id"] == "asset-feedback-asset-profile-character-lead-v1-character-identity-2026-06-02t00-00-00-08-00"
    assert event["source_test_package_ref"] == "asset_test_package.json"
    assert event["source_readiness_ref"] == "asset_profile_readiness.json"
    assert event["source_feedback_input_type"] == "json_fixture"
    assert event["parse_status"] == "parsed"
    assert event["profile_id"] == "asset-profile:character:lead:v1"
    assert event["profile_kind"] == "character"
    assert event["review_dimension"] == "character_identity"
    assert event["review_result"] == "partially_kept"
    assert event["review_result_effect"] == "needs_review"
    assert event["feedback_is_memory"] is False
    assert event["creates_memory_candidate"] is False
    assert event["creates_promotion_decision"] is False
    assert event["writes_long_term_memory"] is False
    assert event["writes_company_kb"] is False
    assert event["redaction_checks"]["status"] == "passed"


def test_asset_feedback_unknown_profile_ref_fails(tmp_path: Path) -> None:
    package_dir = _write_asset_package(tmp_path)
    fixture = _feedback_fixture()
    fixture["profile_id"] = "asset-profile:character:missing:v1"

    with pytest.raises(ValueError, match="profile_id does not exist"):
        build_asset_feedback_event(
            asset_profiles=json.loads((package_dir / "asset_profiles.json").read_text(encoding="utf-8")),
            asset_profile_readiness=json.loads((package_dir / "asset_profile_readiness.json").read_text(encoding="utf-8")),
            feedback_fixture=fixture,
            generated_at=GENERATED_AT,
        )


def test_asset_feedback_cannot_judge_stays_neutral(tmp_path: Path) -> None:
    package_dir = _write_asset_package(tmp_path)
    fixture = _feedback_fixture()
    fixture["review_result"] = "cannot_judge"
    fixture["suggested_next_state"] = "cannot_judge"

    event = build_asset_feedback_event(
        asset_profiles=json.loads((package_dir / "asset_profiles.json").read_text(encoding="utf-8")),
        asset_profile_readiness=json.loads((package_dir / "asset_profile_readiness.json").read_text(encoding="utf-8")),
        feedback_fixture=fixture,
        generated_at=GENERATED_AT,
    )

    assert event["review_result"] == "cannot_judge"
    assert event["review_result_effect"] == "neutral"
    assert event["creates_memory_candidate"] is False
    assert event["creates_promotion_decision"] is False


def test_asset_feedback_rejects_private_paths_and_provider_secrets(tmp_path: Path) -> None:
    fixture_path = tmp_path / "feedback.json"
    fixture = _feedback_fixture()
    fixture["drift_observations"] = [r"Reference leaked from D:\private\character.png"]
    fixture_path.write_text(json.dumps(fixture), encoding="utf-8")

    with pytest.raises(ValueError, match="private fragments"):
        load_asset_feedback_fixture(fixture_path)


def test_asset_feedback_records_markdown_derived_fixture_type(tmp_path: Path) -> None:
    package_dir = _write_asset_package(tmp_path)
    fixture = _feedback_fixture()
    fixture["source_feedback_input_type"] = "markdown_derived_fixture"

    event = build_asset_feedback_event(
        asset_profiles=json.loads((package_dir / "asset_profiles.json").read_text(encoding="utf-8")),
        asset_profile_readiness=json.loads((package_dir / "asset_profile_readiness.json").read_text(encoding="utf-8")),
        feedback_fixture=fixture,
        generated_at=GENERATED_AT,
    )

    assert event["source_feedback_input_type"] == "markdown_derived_fixture"
    assert event["parse_status"] == "parsed"


def test_asset_feedback_blocked_profile_does_not_open_next_context(tmp_path: Path) -> None:
    package_dir = _write_asset_package(tmp_path)
    asset_profiles = json.loads((package_dir / "asset_profiles.json").read_text(encoding="utf-8"))
    asset_profiles["profiles"][0]["profile_status"] = "blocked"
    asset_profiles["profiles"][0]["context_eligibility"] = "blocked"
    asset_profiles["profiles"][0]["usable_for_next_context"] = False
    fixture = _feedback_fixture()

    event = build_asset_feedback_event(
        asset_profiles=asset_profiles,
        asset_profile_readiness=json.loads((package_dir / "asset_profile_readiness.json").read_text(encoding="utf-8")),
        feedback_fixture=fixture,
        generated_at=GENERATED_AT,
    )

    assert event["target_profile_status"] == "blocked"
    assert event["target_profile_context_eligible"] is False
    assert event["target_profile_next_context_unlocked"] is False


def test_asset_feedback_retired_profile_does_not_open_next_context(tmp_path: Path) -> None:
    package_dir = _write_asset_package(tmp_path)
    asset_profiles = json.loads((package_dir / "asset_profiles.json").read_text(encoding="utf-8"))
    asset_profiles["profiles"][0]["profile_status"] = "retired"
    asset_profiles["profiles"][0]["context_eligibility"] = "blocked"
    asset_profiles["profiles"][0]["usable_for_next_context"] = False

    event = build_asset_feedback_event(
        asset_profiles=asset_profiles,
        asset_profile_readiness=json.loads((package_dir / "asset_profile_readiness.json").read_text(encoding="utf-8")),
        feedback_fixture=_feedback_fixture(),
        generated_at=GENERATED_AT,
    )

    assert event["target_profile_status"] == "retired"
    assert event["target_profile_context_eligible"] is False
    assert event["target_profile_next_context_unlocked"] is False


def test_asset_feedback_rejects_unsupported_input_type(tmp_path: Path) -> None:
    fixture_path = tmp_path / "feedback.json"
    fixture = _feedback_fixture()
    fixture["source_feedback_input_type"] = "freeform_markdown"
    fixture_path.write_text(json.dumps(fixture), encoding="utf-8")

    with pytest.raises(ValueError, match="source_feedback_input_type is unsupported"):
        load_asset_feedback_fixture(fixture_path)


def test_asset_feedback_cli_writes_event_and_markdown(tmp_path: Path) -> None:
    package_dir = _write_asset_package(tmp_path / "package")
    output_dir = tmp_path / "feedback"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "production-memory-loop-record-asset-feedback",
            "--asset-profiles",
            str(package_dir / "asset_profiles.json"),
            "--asset-profile-readiness",
            str(package_dir / "asset_profile_readiness.json"),
            "--feedback-json",
            str(EXAMPLE_FEEDBACK),
            "--output",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Asset feedback event: parsed" in result.stdout
    assert "Feedback is memory: false" in result.stdout
    assert "Creates promotion decision: false" in result.stdout
    assert (output_dir / "asset_feedback_event.json").exists()
    assert (output_dir / "asset_feedback_event.md").exists()
    event = json.loads((output_dir / "asset_feedback_event.json").read_text(encoding="utf-8"))
    assert event["kind"] == ASSET_FEEDBACK_EVENT_KIND
    assert event["redaction_checks"]["status"] == "passed"


def test_asset_feedback_writer_keeps_output_safe(tmp_path: Path) -> None:
    package_dir = _write_asset_package(tmp_path)
    event = build_asset_feedback_event(
        asset_profiles=json.loads((package_dir / "asset_profiles.json").read_text(encoding="utf-8")),
        asset_profile_readiness=json.loads((package_dir / "asset_profile_readiness.json").read_text(encoding="utf-8")),
        feedback_fixture=_feedback_fixture(),
        generated_at=GENERATED_AT,
    )

    written = write_asset_feedback_event(event, tmp_path / "feedback")
    serialized = "\n".join(path.read_text(encoding="utf-8") for path in written)

    assert "D:\\private" not in serialized
    assert "api_key" not in serialized.lower()
    assert "signed_url" not in serialized.lower()


def _write_asset_package(tmp_path: Path) -> Path:
    loop = load_production_memory_loop(EXAMPLE_LOOP)
    operator_result = build_production_memory_operator_loop_run(
        loop,
        generated_at=GENERATED_AT,
        source_kb_status="restructuring_or_unknown",
        draft_next_pass_result=True,
    )
    operator_dir = tmp_path / "operator_loop"
    write_production_memory_operator_loop_run(result=operator_result, output_dir=operator_dir, write_run_package=True, write_run_package_check=True)
    bundle = build_asset_profile_test_package(
        operator_artifact_path=operator_dir / "production_memory_operator_loop_run.json",
        asset_profile_seed=load_asset_profile_seed(EXAMPLE_SEED),
        generated_at=GENERATED_AT,
    )
    package_dir = tmp_path / "asset_test_package"
    write_asset_profile_test_package(bundle, package_dir)
    return package_dir


def _feedback_fixture() -> dict:
    return {
        "kind": "agentflow_production_memory_asset_feedback_fixture",
        "schema_version": "production-memory-loop/v1",
        "feedback_event_id": "asset-feedback:lead-character:identity:v1",
        "project_id": "project:generic-content-loop",
        "source_test_package_ref": "asset_test_package.json",
        "source_readiness_ref": "asset_profile_readiness.json",
        "source_feedback_input_type": "json_fixture",
        "profile_id": "asset-profile:character:lead:v1",
        "profile_kind": "character",
        "review_dimension": "character_identity",
        "review_result": "partially_kept",
        "drift_observations": ["The face shape stayed close, but age impression was softer in the second pass."],
        "violated_constraints": ["do not change age impression"],
        "failure_attribution": "character_inconsistency",
        "suggested_next_state": "candidate",
        "evidence_refs": ["asset-profile:character:lead:v1", "asset-profile-readiness:asset-profile-seed:generic-production-loop:v1"],
        "reviewer_role": "tester",
    }
