from __future__ import annotations

import copy
import json
from pathlib import Path

from agentflow.harness.agentflow_router import validate_router_decision_dry_run


ROUTER_DECISION_EXAMPLE = Path("examples/agentflow/router_decision.example.json")
ROUTER_CONTRACT = Path("docs/agentflow_router_contract.md")
KNOWN_SKILL_IDS = {
    "agentflow_studio.production.production_handoff",
    "agentflow_studio.short_highlight_package",
    "agentflow_studio.video_script_highlight_package",
}


def _router_decision() -> dict:
    return json.loads(ROUTER_DECISION_EXAMPLE.read_text(encoding="utf-8"))


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_router_dry_run_validator_accepts_current_example_without_execution() -> None:
    result = validate_router_decision_dry_run(_router_decision(), known_skill_ids=KNOWN_SKILL_IDS)

    assert result["schema_version"] == "0.1.0"
    assert result["artifact_type"] == "agentflow_router_dry_run_validation"
    assert result["validation_scope"] == "router_decision_dry_run"
    assert result["runtime_status"] == "not_implemented"
    assert result["does_not_execute"] is True
    assert result["overall_status"] == "passed"
    assert all(check["status"] == "passed" for check in result["checks"])


def test_router_dry_run_validator_rejects_execution_claims() -> None:
    decision = _router_decision()
    decision["execution_status"] = "succeeded"
    decision["executes_skill"] = True

    result = validate_router_decision_dry_run(decision, known_skill_ids=KNOWN_SKILL_IDS)

    assert result["overall_status"] == "failed"
    failed_check_ids = {check["check_id"] for check in result["checks"] if check["status"] == "failed"}
    assert {"decision_only_status", "does_not_execute_skill"} <= failed_check_ids


def test_router_dry_run_validator_requires_known_selected_skill() -> None:
    decision = _router_decision()
    decision["selected_skill_id"] = "unknown.future_skill"

    result = validate_router_decision_dry_run(decision, known_skill_ids=KNOWN_SKILL_IDS)

    assert result["overall_status"] == "failed"
    failed_check_ids = {check["check_id"] for check in result["checks"] if check["status"] == "failed"}
    assert "selected_skill_known" in failed_check_ids


def test_router_dry_run_validator_requires_rejected_candidate_reasons() -> None:
    decision = _router_decision()
    broken_candidate = copy.deepcopy(decision["rejected_candidate_skills"][0])
    broken_candidate["reason"] = ""
    decision["rejected_candidate_skills"] = [broken_candidate]

    result = validate_router_decision_dry_run(decision, known_skill_ids=KNOWN_SKILL_IDS)

    assert result["overall_status"] == "failed"
    failed_check_ids = {check["check_id"] for check in result["checks"] if check["status"] == "failed"}
    assert "rejected_candidates_have_reasons" in failed_check_ids


def test_router_dry_run_validator_requires_request_summary() -> None:
    decision = _router_decision()
    decision["request_summary"] = ""

    result = validate_router_decision_dry_run(decision, known_skill_ids=KNOWN_SKILL_IDS)

    assert result["overall_status"] == "failed"
    failed_check_ids = {check["check_id"] for check in result["checks"] if check["status"] == "failed"}
    assert "request_summary_declared" in failed_check_ids


def test_router_dry_run_validator_rejects_selected_skill_in_rejected_candidates() -> None:
    decision = _router_decision()
    decision["rejected_candidate_skills"].append(
        {
            "skill_id": decision["selected_skill_id"],
            "reason": "Accidentally rejected the selected skill.",
        }
    )

    result = validate_router_decision_dry_run(decision, known_skill_ids=KNOWN_SKILL_IDS)

    assert result["overall_status"] == "failed"
    failed_check_ids = {check["check_id"] for check in result["checks"] if check["status"] == "failed"}
    assert "selected_skill_not_rejected" in failed_check_ids


def test_router_dry_run_validator_rejects_private_paths_and_secrets() -> None:
    decision = _router_decision()
    decision["request_summary"] = "Route D:\\private\\project with api_key=abc123"

    result = validate_router_decision_dry_run(decision, known_skill_ids=KNOWN_SKILL_IDS)

    assert result["overall_status"] == "failed"
    failed_check_ids = {check["check_id"] for check in result["checks"] if check["status"] == "failed"}
    assert "no_private_paths_or_secrets" in failed_check_ids


def test_router_dry_run_validator_is_documented_as_non_runtime() -> None:
    router_contract = _text(ROUTER_CONTRACT)

    assert "agentflow_router_dry_run_validation" in router_contract
    assert "does not implement Router runtime" in router_contract
