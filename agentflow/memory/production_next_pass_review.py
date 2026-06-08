from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentflow.harness.constants import AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS, FAILED, PASSED
from agentflow.memory.production_loop import SCHEMA_VERSION
from agentflow.memory.production_next_pass_result import NEXT_PASS_RESULT_KIND
from agentflow.memory.production_next_pass_review_render import render_next_pass_review_markdown
from agentflow.memory.production_next_task import NEXT_TASK_PACKET_KIND
from agentflow.harness.json_io import write_json

NEXT_PASS_REVIEW_KIND = "agentflow_production_memory_next_pass_review"


def build_next_pass_review(
    next_task_packet: dict[str, Any],
    next_pass_result: dict[str, Any],
    *,
    reviewed_at: str,
) -> dict[str, Any]:
    """Review a supplied next-pass result against the allowed context packet."""
    _validate_packet(next_task_packet)
    _validate_result(next_pass_result, next_task_packet)
    if not isinstance(reviewed_at, str) or not reviewed_at.strip():
        raise ValueError("reviewed_at is required")

    allowed_refs = _list(next_task_packet.get("allowed_context_refs"))
    blocked_refs = _list(next_task_packet.get("blocked_refs"))
    output_artifacts = _list(next_pass_result.get("output_artifacts"))
    blocked_or_unknown = _blocked_or_unknown_refs(output_artifacts, allowed_refs, blocked_refs)
    used_allowed_refs = _used_allowed_refs(output_artifacts, allowed_refs)
    feedback_events = _list(next_pass_result.get("feedback_events"))
    feedback_candidates = [_feedback_candidate(event, next_task_packet) for event in feedback_events if _dict(event)]
    promotion_templates = [_promotion_template(candidate, reviewed_at) for candidate in feedback_candidates]
    controls = _controls(next_task_packet, next_pass_result, output_artifacts, blocked_or_unknown, feedback_candidates)
    ready = all(control["status"] == PASSED for control in controls)
    review = {
        "kind": NEXT_PASS_REVIEW_KIND,
        "artifact_type": NEXT_PASS_REVIEW_KIND,
        "schema_version": next_task_packet.get("schema_version", SCHEMA_VERSION),
        "review_id": f"next-pass-review:{next_task_packet.get('task_packet_id', 'unknown')}",
        "reviewed_at": reviewed_at,
        "source_task_packet_id": next_task_packet.get("task_packet_id", "unknown"),
        "source_result_id": next_pass_result.get("result_id", "next-pass-result:unassigned"),
        "review_status": "ready_for_operator_review" if ready else "blocked",
        "provider_mode": "no-provider",
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "output_artifacts": _output_summaries(output_artifacts),
        "used_allowed_refs": used_allowed_refs,
        "blocked_or_unknown_refs": blocked_or_unknown,
        "feedback_events": feedback_events,
        "feedback_candidates": feedback_candidates,
        "promotion_decision_templates": promotion_templates,
        "controls": controls,
        "non_claims": _non_claims(),
    }
    _reject_unsafe(review)
    return review


def write_next_pass_review(review: dict[str, Any], output_dir: str | Path) -> list[Path]:
    output_root = Path(output_dir)
    json_path = write_json(output_root / "next_pass_review.json", review)
    md_path = output_root / "next_pass_review.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_next_pass_review_markdown(review), encoding="utf-8")
    return [json_path, md_path]


def _validate_packet(packet: dict[str, Any]) -> None:
    if not isinstance(packet, dict):
        raise ValueError("next task packet must be a JSON object")
    if packet.get("kind") != NEXT_TASK_PACKET_KIND:
        raise ValueError(f"next task packet kind must be {NEXT_TASK_PACKET_KIND}")


def _validate_result(result: dict[str, Any], packet: dict[str, Any]) -> None:
    if not isinstance(result, dict):
        raise ValueError("next pass result must be a JSON object")
    if result.get("kind") != NEXT_PASS_RESULT_KIND:
        raise ValueError(f"next pass result kind must be {NEXT_PASS_RESULT_KIND}")
    if result.get("artifact_type") != NEXT_PASS_RESULT_KIND:
        raise ValueError("next pass result artifact_type must match kind")
    if result.get("schema_version") != packet.get("schema_version", SCHEMA_VERSION):
        raise ValueError("next pass result schema_version must match the task packet")
    if result.get("task_packet_id") != packet.get("task_packet_id"):
        raise ValueError("next pass result task_packet_id must match the task packet")
    if not isinstance(result.get("output_artifacts"), list):
        raise ValueError("next pass result output_artifacts must be a list")
    _reject_unsafe(result)


def _blocked_or_unknown_refs(
    output_artifacts: list[Any],
    allowed_refs: list[Any],
    blocked_refs: list[Any],
) -> list[dict[str, str]]:
    allowed_ids = {str(ref.get("ref_id")) for ref in allowed_refs if isinstance(ref, dict)}
    blocked_ids = {str(ref.get("ref_id")) for ref in blocked_refs if isinstance(ref, dict)}
    findings: list[dict[str, str]] = []
    for artifact in output_artifacts:
        artifact_obj = _dict(artifact)
        output_ref = str(artifact_obj.get("ref_id", "unknown"))
        for ref_id in _string_list(artifact_obj.get("used_context_refs")):
            if ref_id in blocked_ids:
                findings.append({"ref_id": ref_id, "output_ref": output_ref, "reason": "blocked_ref_used"})
            elif ref_id not in allowed_ids:
                findings.append({"ref_id": ref_id, "output_ref": output_ref, "reason": "unknown_ref_used"})
    return findings


def _used_allowed_refs(output_artifacts: list[Any], allowed_refs: list[Any]) -> list[dict[str, Any]]:
    allowed_by_id = {str(ref.get("ref_id")): ref for ref in allowed_refs if isinstance(ref, dict)}
    usage_counts: dict[str, int] = {}
    for artifact in output_artifacts:
        for ref_id in _string_list(_dict(artifact).get("used_context_refs")):
            if ref_id in allowed_by_id:
                usage_counts[ref_id] = usage_counts.get(ref_id, 0) + 1
    return [
        {
            "ref_id": ref_id,
            "usage_count": count,
            "source_record_type": allowed_by_id[ref_id].get("source_record_type", "unknown"),
            "summary": allowed_by_id[ref_id].get("summary", allowed_by_id[ref_id].get("title", "")),
        }
        for ref_id, count in sorted(usage_counts.items())
    ]


def _output_summaries(output_artifacts: list[Any]) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for artifact in output_artifacts:
        artifact_obj = _dict(artifact)
        summaries.append(
            {
                "ref_id": str(artifact_obj.get("ref_id", "unknown")),
                "title": str(artifact_obj.get("title", artifact_obj.get("ref_id", "unknown"))),
                "status": str(artifact_obj.get("status", "unknown")),
                "used_context_refs": _string_list(artifact_obj.get("used_context_refs")),
            }
        )
    return summaries


def _feedback_candidate(event: Any, packet: dict[str, Any]) -> dict[str, Any]:
    feedback = _dict(event)
    feedback_id = str(feedback.get("feedback_id", "feedback:unassigned"))
    decision = str(feedback.get("decision", "note"))
    return {
        "candidate_id": _safe_id("memory:candidate", feedback_id),
        "source_feedback_id": feedback_id,
        "source_task_packet_id": packet.get("task_packet_id", "unknown"),
        "target_ref": str(feedback.get("target_ref", "unknown")),
        "status": "blocked" if decision == "rejected" else "candidate",
        "decision": decision,
        "summary": str(feedback.get("summary", "")),
        "candidate_is_promoted_memory": False,
        "requires_promotion_decision": True,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
    }


def _promotion_template(candidate: dict[str, Any], reviewed_at: str) -> dict[str, Any]:
    return {
        "decision_id": _safe_id("promotion:template", candidate["candidate_id"], reviewed_at),
        "candidate_id": candidate["candidate_id"],
        "source_feedback_ids": [candidate["source_feedback_id"]],
        "decision": "pending",
        "review_mode": "explicit_operator_decision_required",
        "template_only": True,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
    }


def _controls(
    packet: dict[str, Any],
    result: dict[str, Any],
    output_artifacts: list[Any],
    blocked_or_unknown: list[dict[str, str]],
    feedback_candidates: list[dict[str, Any]],
) -> list[dict[str, str]]:
    return [
        _control("source_packet_ready", packet.get("packet_status") == "ready"),
        _control("result_no_provider_mode", result.get("provider_mode") == "no-provider"),
        _control("provider_calls_not_started", result.get("provider_calls_started") is False),
        _control("long_term_memory_write_disabled", result.get("writes_long_term_memory") is False),
        _control("company_kb_write_disabled", result.get("writes_company_kb") is False),
        _control("output_artifacts_present", bool(output_artifacts)),
        _control("no_blocked_or_unknown_context_refs_used", not blocked_or_unknown),
        _control("feedback_candidate_only", _feedback_candidate_only(feedback_candidates)),
    ]


def _feedback_candidate_only(candidates: list[dict[str, Any]]) -> bool:
    return all(
        candidate.get("candidate_is_promoted_memory") is False
        and candidate.get("requires_promotion_decision") is True
        and candidate.get("writes_long_term_memory") is False
        for candidate in candidates
    )


def _non_claims() -> list[str]:
    return [
        "not next-pass execution",
        "not human acceptance",
        "not business validation",
        "not durable memory",
        "not durable Memory OS",
        "not provider success",
        "not Company KB promotion",
    ]


def _safe_id(*parts: str) -> str:
    raw = ":".join(parts)
    safe = "".join(char.lower() if char.isalnum() else "-" for char in raw).strip("-")
    while "--" in safe:
        safe = safe.replace("--", "-")
    return safe


def _reject_unsafe(value: Any) -> None:
    raw = json.dumps(value, ensure_ascii=False).lower()
    if any(fragment.lower() in raw for fragment in AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS):
        raise ValueError("production memory next pass review contains unsafe path, generated artifact path, or secret")


def _control(control_id: str, passed: bool) -> dict[str, str]:
    return {"control_id": control_id, "status": PASSED if passed else FAILED}


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _string_list(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


__all__ = (
    "NEXT_PASS_RESULT_KIND",
    "NEXT_PASS_REVIEW_KIND",
    "build_next_pass_review",
    "render_next_pass_review_markdown",
    "write_next_pass_review",
)
