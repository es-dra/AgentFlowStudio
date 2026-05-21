from __future__ import annotations

from typing import Any


SCHEMA_VERSION = "0.1.0"
PASSED = "passed"
FAILED = "failed"
FORBIDDEN_REPLAY_FRAGMENTS = (
    "D:\\",
    "C:\\",
    "data/processed/runs",
    "data/raw/",
    ".mp4",
    ".mov",
    "api_key",
    "access_token",
    "refresh_token",
    "secret_key",
    "client_secret",
    "authorization:",
    "bearer ",
    "cookie=",
    "signed_url",
)


def validate_skill_invocation_result_replay(
    invocation: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    """Validate a skill invocation/result pair without executing the skill."""
    checks = [
        _check(
            "invocation_schema_version_0_1_0",
            invocation.get("schema_version") == SCHEMA_VERSION,
            "skill invocation uses schema_version 0.1.0",
        ),
        _check(
            "result_schema_version_0_1_0",
            result.get("schema_version") == SCHEMA_VERSION,
            "skill result uses schema_version 0.1.0",
        ),
        _check(
            "invocation_artifact_type",
            invocation.get("artifact_type") == "agentflow_skill_invocation",
            "invocation artifact_type is agentflow_skill_invocation",
        ),
        _check(
            "result_artifact_type",
            result.get("artifact_type") == "agentflow_skill_result",
            "result artifact_type is agentflow_skill_result",
        ),
        _check(
            "invocation_id_matches",
            _non_empty_str(invocation.get("invocation_id"))
            and invocation.get("invocation_id") == result.get("invocation_id"),
            "result invocation_id matches the planned invocation",
        ),
        _check(
            "project_id_matches",
            _non_empty_str(invocation.get("project_id")) and invocation.get("project_id") == result.get("project_id"),
            "result project_id matches the planned invocation",
        ),
        _check(
            "skill_id_matches",
            _non_empty_str(invocation.get("skill_id")) and invocation.get("skill_id") == result.get("skill_id"),
            "result skill_id matches the planned invocation",
        ),
        _check(
            "invocation_is_planned",
            invocation.get("execution_status") == "planned",
            "skill invocation remains a planned call",
        ),
        _check(
            "result_status_valid",
            result.get("execution_status") in {"succeeded", "failed", "blocked"},
            "skill result declares a valid execution_status",
        ),
        _check(
            "expected_outputs_emitted",
            _expected_outputs_emitted(invocation.get("expected_output_artifacts"), result.get("output_artifacts")),
            "result output_artifacts include expected_output_artifacts",
        ),
        _check(
            "quality_gates_declared",
            _quality_gates_declared(invocation.get("quality_gates"), result.get("quality_gate_status")),
            "result quality_gate_status covers invocation quality_gates",
        ),
        _check(
            "quality_gates_passed",
            _quality_gates_passed(invocation.get("quality_gates"), result.get("quality_gate_status")),
            "required quality gates passed",
        ),
        _check(
            "review_artifacts_declared",
            isinstance(result.get("review_artifacts"), list) and len(result.get("review_artifacts")) > 0,
            "result declares review artifacts",
        ),
        _check(
            "does_not_write_long_term_memory",
            result.get("writes_long_term_memory") is False,
            "skill replay does not write long-term memory",
        ),
        _check(
            "no_private_paths_or_secrets",
            _contains_no_forbidden_fragments(invocation, result),
            "skill replay artifacts do not include private paths, generated media, run outputs, or secrets",
        ),
    ]

    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "agentflow_skill_replay_validation",
        "validation_scope": "skill_invocation_result_replay",
        "runtime_status": "not_implemented",
        "does_not_execute": True,
        "invocation_id": invocation.get("invocation_id"),
        "result_id": result.get("result_id"),
        "skill_id": invocation.get("skill_id"),
        "overall_status": "failed" if any(check["status"] == FAILED for check in checks) else "passed",
        "checks": checks,
    }


def _non_empty_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value)


def _expected_outputs_emitted(expected: Any, actual: Any) -> bool:
    if not isinstance(expected, list) or not expected or not isinstance(actual, list):
        return False
    if not _all_non_empty_strings(expected) or not _all_non_empty_strings(actual):
        return False
    return set(expected) <= set(actual)


def _quality_gates_declared(quality_gates: Any, gate_status: Any) -> bool:
    if not isinstance(quality_gates, list) or not quality_gates or not isinstance(gate_status, dict):
        return False
    if not _all_non_empty_strings(quality_gates):
        return False
    return all(_gate_key(gate) in gate_status for gate in quality_gates)


def _quality_gates_passed(quality_gates: Any, gate_status: Any) -> bool:
    if not _quality_gates_declared(quality_gates, gate_status):
        return False
    return all(gate_status[_gate_key(gate)] == PASSED for gate in quality_gates if isinstance(gate, str))


def _gate_key(gate: str) -> str:
    return gate.replace("-", "_")


def _all_non_empty_strings(values: list[Any]) -> bool:
    return all(_non_empty_str(value) for value in values)


def _contains_no_forbidden_fragments(*payloads: Any) -> bool:
    raw_text = " ".join(str(payload).lower() for payload in payloads)
    return not any(fragment.lower() in raw_text for fragment in FORBIDDEN_REPLAY_FRAGMENTS)


def _check(check_id: str, passed: bool, message: str) -> dict[str, str]:
    return {"check_id": check_id, "status": PASSED if passed else FAILED, "message": message}
