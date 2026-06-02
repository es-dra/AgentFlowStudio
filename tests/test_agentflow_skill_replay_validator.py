from __future__ import annotations

import json
from pathlib import Path

from agentflow.harness.agentflow_skill import validate_skill_invocation_result_replay


SKILL_INVOCATION_EXAMPLE = Path("examples/agentflow/skill_invocation.example.json")
SKILL_RESULT_EXAMPLE = Path("examples/agentflow/skill_result.example.json")
SKILL_CONTRACT = Path("docs/agentflow_skill_contract.md")
RUNTIME_READINESS = Path("docs/agentflow_runtime_readiness.md")
PHASE15_ROADMAP = Path("docs/agentflow_phase15_roadmap.md")


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _valid_replay_result() -> dict:
    return validate_skill_invocation_result_replay(
        _json(SKILL_INVOCATION_EXAMPLE),
        _json(SKILL_RESULT_EXAMPLE),
    )


def test_skill_replay_validator_accepts_current_examples_without_execution() -> None:
    validation = _valid_replay_result()

    assert validation["schema_version"] == "0.1.0"
    assert validation["artifact_type"] == "agentflow_skill_replay_validation"
    assert validation["validation_scope"] == "skill_invocation_result_replay"
    assert validation["runtime_status"] == "not_implemented"
    assert validation["does_not_execute"] is True
    assert validation["overall_status"] == "passed"
    assert all(check["status"] == "passed" for check in validation["checks"])


def test_skill_replay_validator_rejects_invocation_id_mismatch() -> None:
    invocation = _json(SKILL_INVOCATION_EXAMPLE)
    result = _json(SKILL_RESULT_EXAMPLE)
    result["invocation_id"] = "different_invocation"

    validation = validate_skill_invocation_result_replay(invocation, result)

    assert validation["overall_status"] == "failed"
    assert _failed_check_ids(validation) >= {"invocation_id_matches"}


def test_skill_replay_validator_rejects_skill_id_mismatch() -> None:
    invocation = _json(SKILL_INVOCATION_EXAMPLE)
    result = _json(SKILL_RESULT_EXAMPLE)
    result["skill_id"] = "agentflow_studio.short_highlight_package"

    validation = validate_skill_invocation_result_replay(invocation, result)

    assert validation["overall_status"] == "failed"
    assert _failed_check_ids(validation) >= {"skill_id_matches"}


def test_skill_replay_validator_requires_expected_outputs() -> None:
    invocation = _json(SKILL_INVOCATION_EXAMPLE)
    result = _json(SKILL_RESULT_EXAMPLE)
    result["output_artifacts"] = ["production_handoff.json"]

    validation = validate_skill_invocation_result_replay(invocation, result)

    assert validation["overall_status"] == "failed"
    assert _failed_check_ids(validation) >= {"expected_outputs_emitted"}


def test_skill_replay_validator_requires_quality_gates_to_pass() -> None:
    invocation = _json(SKILL_INVOCATION_EXAMPLE)
    result = _json(SKILL_RESULT_EXAMPLE)
    result["quality_gate_status"]["review_run"] = "failed"

    validation = validate_skill_invocation_result_replay(invocation, result)

    assert validation["overall_status"] == "failed"
    assert _failed_check_ids(validation) >= {"quality_gates_passed"}


def test_skill_replay_validator_rejects_malformed_expected_outputs_and_gates() -> None:
    invocation = _json(SKILL_INVOCATION_EXAMPLE)
    result = _json(SKILL_RESULT_EXAMPLE)
    invocation["expected_output_artifacts"] = ["production_handoff.json", ""]
    invocation["quality_gates"] = ["inspect-run", None]

    validation = validate_skill_invocation_result_replay(invocation, result)

    assert validation["overall_status"] == "failed"
    assert _failed_check_ids(validation) >= {
        "expected_outputs_emitted",
        "quality_gates_declared",
        "quality_gates_passed",
    }


def test_skill_replay_validator_blocks_long_term_memory_writes() -> None:
    invocation = _json(SKILL_INVOCATION_EXAMPLE)
    result = _json(SKILL_RESULT_EXAMPLE)
    result["writes_long_term_memory"] = True

    validation = validate_skill_invocation_result_replay(invocation, result)

    assert validation["overall_status"] == "failed"
    assert _failed_check_ids(validation) >= {"does_not_write_long_term_memory"}


def test_skill_replay_validator_rejects_private_paths_and_secrets() -> None:
    invocation = _json(SKILL_INVOCATION_EXAMPLE)
    result = _json(SKILL_RESULT_EXAMPLE)
    result["output_artifacts"].append("D:\\private\\result.mp4?api_key=abc123")

    validation = validate_skill_invocation_result_replay(invocation, result)

    assert validation["overall_status"] == "failed"
    assert _failed_check_ids(validation) >= {"no_private_paths_or_secrets"}


def test_skill_replay_validator_is_documented_as_non_runtime() -> None:
    skill_contract = _text(SKILL_CONTRACT)
    runtime_readiness = _text(RUNTIME_READINESS)
    phase15 = _text(PHASE15_ROADMAP)

    assert "agentflow_skill_replay_validation" in skill_contract
    assert "does not implement a skill runtime" in skill_contract
    assert "skill invocation/result replay" in runtime_readiness
    assert "Phase 15.12" in phase15
    assert "Skill Invocation / Result Replay Validator" in phase15


def _failed_check_ids(validation: dict) -> set[str]:
    return {check["check_id"] for check in validation["checks"] if check["status"] == "failed"}
