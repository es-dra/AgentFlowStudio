from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from agentflow.harness.constants import (
    AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS,
    AGENTFLOW_VALIDATION_SCHEMA_VERSION,
    FAILED,
    PASSED,
)

SCHEMA_VERSION = AGENTFLOW_VALIDATION_SCHEMA_VERSION
FORBIDDEN_DECISION_FRAGMENTS = AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS


def validate_router_decision_dry_run(
    decision: dict[str, Any],
    *,
    known_skill_ids: Iterable[str],
) -> dict[str, Any]:
    """Validate a router decision artifact without executing the selected skill."""
    known_skills = set(known_skill_ids)
    rejected_candidates = decision.get("rejected_candidate_skills")
    checks = [
        _check(
            "schema_version_0_1_0",
            decision.get("schema_version") == SCHEMA_VERSION,
            "router decision uses schema_version 0.1.0",
        ),
        _check(
            "artifact_type_router_decision",
            decision.get("artifact_type") == "agentflow_router_decision",
            "artifact_type is agentflow_router_decision",
        ),
        _check(
            "selected_skill_declared",
            isinstance(decision.get("selected_skill_id"), str) and bool(decision.get("selected_skill_id")),
            "selected_skill_id is declared",
        ),
        _check(
            "selected_skill_known",
            decision.get("selected_skill_id") in known_skills,
            "selected_skill_id matches a known skill contract",
        ),
        _check(
            "request_summary_declared",
            isinstance(decision.get("request_summary"), str) and bool(decision.get("request_summary")),
            "request_summary is declared",
        ),
        _check(
            "selection_reason_declared",
            isinstance(decision.get("selection_reason"), str) and bool(decision.get("selection_reason")),
            "selection_reason is declared",
        ),
        _check(
            "rejected_candidates_declared",
            isinstance(rejected_candidates, list) and len(rejected_candidates) > 0,
            "rejected_candidate_skills is a non-empty list",
        ),
        _check(
            "rejected_candidates_have_reasons",
            _rejected_candidates_have_reasons(rejected_candidates),
            "each rejected candidate declares skill_id and reason",
        ),
        _check(
            "rejected_candidates_known",
            _rejected_candidates_are_known(rejected_candidates, known_skills),
            "rejected candidate skills match known skill contracts",
        ),
        _check(
            "selected_skill_not_rejected",
            _selected_skill_is_not_rejected(decision.get("selected_skill_id"), rejected_candidates),
            "selected_skill_id is not also listed as a rejected candidate",
        ),
        _check(
            "decision_only_status",
            decision.get("execution_status") == "decision_only",
            "execution_status remains decision_only",
        ),
        _check(
            "does_not_execute_skill",
            decision.get("executes_skill") is False,
            "router decision does not execute the selected skill",
        ),
        _check(
            "no_private_paths_or_secrets",
            _contains_no_forbidden_fragments(decision),
            "router decision does not include private paths, generated media, run outputs, or secrets",
        ),
    ]

    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": "agentflow_router_dry_run_validation",
        "validation_scope": "router_decision_dry_run",
        "runtime_status": "not_implemented",
        "does_not_execute": True,
        "decision_id": decision.get("decision_id"),
        "selected_skill_id": decision.get("selected_skill_id"),
        "overall_status": "failed" if any(check["status"] == FAILED for check in checks) else "passed",
        "checks": checks,
    }


def _rejected_candidates_have_reasons(candidates: Any) -> bool:
    if not isinstance(candidates, list) or not candidates:
        return False
    return all(
        isinstance(candidate, dict)
        and isinstance(candidate.get("skill_id"), str)
        and bool(candidate.get("skill_id"))
        and isinstance(candidate.get("reason"), str)
        and bool(candidate.get("reason"))
        for candidate in candidates
    )


def _rejected_candidates_are_known(candidates: Any, known_skill_ids: set[str]) -> bool:
    if not isinstance(candidates, list) or not candidates:
        return False
    return all(isinstance(candidate, dict) and candidate.get("skill_id") in known_skill_ids for candidate in candidates)


def _selected_skill_is_not_rejected(selected_skill_id: Any, candidates: Any) -> bool:
    if not isinstance(selected_skill_id, str) or not isinstance(candidates, list):
        return False
    return all(not isinstance(candidate, dict) or candidate.get("skill_id") != selected_skill_id for candidate in candidates)


def _contains_no_forbidden_fragments(payload: Any) -> bool:
    raw_text = str(payload).lower()
    return not any(fragment.lower() in raw_text for fragment in FORBIDDEN_DECISION_FRAGMENTS)


def _check(check_id: str, passed: bool, message: str) -> dict[str, str]:
    return {"check_id": check_id, "status": PASSED if passed else FAILED, "message": message}
