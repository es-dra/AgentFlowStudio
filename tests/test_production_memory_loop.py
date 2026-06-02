from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

from agentflow.memory.production_loop import (
    KIND,
    SCHEMA_VERSION,
    build_production_memory_loop_run,
    validate_production_memory_loop,
)


EXAMPLE_PATH = Path("examples/agentflow/production_memory_loop.example.json")


def load_example() -> dict:
    return json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))


def test_example_validates_and_builds_ready_no_provider_bundle() -> None:
    payload = load_example()

    assert payload["kind"] == "agentflow_production_memory_loop"
    assert payload["schema_version"] == "production-memory-loop/v1"
    assert KIND == payload["kind"]
    assert SCHEMA_VERSION == payload["schema_version"]

    validation = validate_production_memory_loop(payload)
    run = build_production_memory_loop_run(payload)

    assert validation["overall_status"] == "passed"
    assert run["provider_calls_started"] is False
    assert run["writes_long_term_memory"] is False
    assert run["context_bundle"]["included_refs"]
    assert isinstance(run["context_bundle"]["blocked_refs"], list)
    assert run["pass_readiness"]["ready"] is True
    assert run["pass_readiness"]["provider_mode"] == "no-provider"
    assert run["next_pass_bundle"]["execution_status"] == "planned"
    assert run["next_pass_bundle"]["provider_calls_started"] is False
    assert run["next_pass_bundle"]["context_bundle_id"] == run["context_bundle"]["bundle_id"]


def test_rejected_artifact_is_blocked_from_next_context() -> None:
    run = build_production_memory_loop_run(load_example())

    included_ids = {ref["ref_id"] for ref in run["context_bundle"]["included_refs"]}
    blocked = {ref["ref_id"]: ref["reason"] for ref in run["context_bundle"]["blocked_refs"]}

    assert "artifact:draft_storyboard:v1" not in included_ids
    assert blocked["artifact:draft_storyboard:v1"] == "artifact_status_rejected"


def test_pending_memory_candidate_is_blocked_from_next_context() -> None:
    run = build_production_memory_loop_run(load_example())

    included_ids = {ref["ref_id"] for ref in run["context_bundle"]["included_refs"]}
    blocked = {ref["ref_id"]: ref["reason"] for ref in run["context_bundle"]["blocked_refs"]}

    assert "memory:candidate:pending-tone:v1" not in included_ids
    assert blocked["memory:candidate:pending-tone:v1"] == "memory_candidate_pending"


def test_missing_reference_fails_validation() -> None:
    payload = load_example()
    payload["feedback_events"][0]["target_ref"] = "artifact:missing"

    validation = validate_production_memory_loop(payload)

    assert validation["overall_status"] == "failed"
    failed_ids = {check["check_id"] for check in validation["checks"] if check["status"] == "failed"}
    assert "references_resolve" in failed_ids


def test_no_provider_readiness_passes_without_remote_provider() -> None:
    run = build_production_memory_loop_run(load_example())

    assert run["pass_readiness"]["ready"] is True
    assert run["pass_readiness"]["provider_mode"] == "no-provider"
    assert run["pass_readiness"]["provider_calls_started"] is False
    assert {check["check_id"] for check in run["pass_readiness"]["checks"]} >= {
        "validation_passed",
        "provider_mode_no_provider",
        "context_bundle_has_included_refs",
    }


def test_next_pass_bundle_uses_only_included_refs() -> None:
    run = build_production_memory_loop_run(load_example())
    included_ids = {ref["ref_id"] for ref in run["context_bundle"]["included_refs"]}
    blocked_ids = {ref["ref_id"] for ref in run["context_bundle"]["blocked_refs"]}
    next_pass_ids = {ref["ref_id"] for ref in run["next_pass_bundle"]["context_refs"]}

    assert next_pass_ids == included_ids
    assert not (next_pass_ids & blocked_ids)
    assert run["next_pass_bundle"]["blocked_ref_count"] == len(blocked_ids)
    assert run["next_pass_bundle"]["does_not_execute"] is True
    assert run["next_pass_bundle"]["writes_long_term_memory"] is False


def test_feedback_does_not_auto_promote_memory() -> None:
    run = build_production_memory_loop_run(load_example())

    included = {ref["ref_id"]: ref for ref in run["context_bundle"]["included_refs"]}
    blocked = {ref["ref_id"]: ref["reason"] for ref in run["context_bundle"]["blocked_refs"]}

    assert "feedback:storyboard_approval:v1" not in included
    assert blocked["feedback:storyboard_approval:v1"] == "feedback_is_not_memory"
    promoted = included["memory:candidate:approved-style:v1"]
    assert promoted["decision_id"] == "promotion:approved-style:v1"
    assert promoted["source_record_type"] == "memory_candidate"


def test_promoted_memory_requires_explicit_promotion_decision() -> None:
    payload = load_example()
    payload["promotion_decisions"] = []
    payload["memory_candidates"][0]["status"] = "promoted"

    validation = validate_production_memory_loop(payload)
    run = build_production_memory_loop_run(payload)

    assert validation["overall_status"] == "failed"
    failed_ids = {check["check_id"] for check in validation["checks"] if check["status"] == "failed"}
    assert "promoted_memory_has_decision" in failed_ids
    assert "memory:candidate:approved-style:v1" not in {
        ref["ref_id"] for ref in run["context_bundle"]["included_refs"]
    }


def test_cli_validate_and_run_no_provider_write_auditable_outputs(tmp_path: Path) -> None:
    output_dir = tmp_path / "no_provider"

    validate_result = subprocess.run(
        [sys.executable, "-m", "apps.cli.main", "production-memory-loop-validate", str(EXAMPLE_PATH)],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "Production memory loop validation: passed" in validate_result.stdout
    assert "Provider calls: not started" in validate_result.stdout

    run_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "production-memory-loop-run-no-provider",
            str(EXAMPLE_PATH),
            "--output",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Production memory loop no-provider run: ready" in run_result.stdout
    run_payload = json.loads((output_dir / "production_memory_loop_run.json").read_text(encoding="utf-8"))
    bundle = json.loads((output_dir / "context_bundle.json").read_text(encoding="utf-8"))
    readiness = json.loads((output_dir / "pass_readiness.json").read_text(encoding="utf-8"))
    next_pass = json.loads((output_dir / "next_pass_bundle.json").read_text(encoding="utf-8"))
    assert run_payload["provider_calls_started"] is False
    assert bundle["included_refs"]
    assert isinstance(bundle["blocked_refs"], list)
    assert readiness["ready"] is True
    assert next_pass["execution_status"] == "planned"
    assert next_pass["context_refs"] == bundle["included_refs"]


def test_validation_does_not_mutate_input_payload() -> None:
    payload = load_example()
    before = deepcopy(payload)

    validate_production_memory_loop(payload)
    build_production_memory_loop_run(payload)

    assert payload == before
