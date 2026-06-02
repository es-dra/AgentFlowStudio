from __future__ import annotations

from typing import Any

from agentflow.harness.constants import FAILED, PASSED
from agentflow.memory.company_kb_feedback import COMPANY_KB_FEEDBACK_PACKET_KIND
from agentflow.memory.production_loop import CONTEXT_BUNDLE_KIND, PASS_READINESS_KIND, SCHEMA_VERSION
from agentflow.memory.production_next_context import NEXT_CONTEXT_HANDOFF_KIND
from agentflow.memory.production_next_pass import NEXT_PASS_BUNDLE_KIND
from agentflow.memory.production_next_task import NEXT_TASK_PACKET_KIND
from agentflow.memory.production_operator_feedback_candidate_manifest import (
    operator_feedback_candidate_promotion_controls,
    operator_feedback_candidate_promotion_nodes,
    operator_feedback_candidate_promotion_ready,
    operator_feedback_candidate_promotion_summary,
)
from agentflow.memory.production_operator_next_pass_manifest import (
    next_pass_nodes,
    next_pass_promotion_controls,
    next_pass_promotion_ready,
    next_pass_promotion_summary,
    next_pass_result_ready,
    next_pass_result_summary,
    next_pass_review_ready,
    next_pass_review_summary,
)
from agentflow.memory.production_operator_outputs import OPERATOR_LOOP_KIND, operator_output_artifacts
from agentflow.memory.production_session import SESSION_REPORT_KIND


def build_operator_manifest(
    loop: dict[str, Any],
    run: dict[str, Any],
    handoff: dict[str, Any],
    next_task_packet: dict[str, Any],
    next_pass_result: dict[str, Any] | None,
    next_pass_review: dict[str, Any] | None,
    next_pass_promotion: dict[str, Any] | None,
    operator_feedback_candidate_promotion: dict[str, Any] | None,
    report: dict[str, Any],
    packet: dict[str, Any],
    *,
    generated_at: str,
) -> dict[str, Any]:
    readiness = run["pass_readiness"]
    context = run["context_bundle"]
    ready = (
        readiness.get("ready") is True
        and next_task_packet.get("packet_status") == "ready"
        and next_pass_result_ready(next_pass_result)
        and next_pass_review_ready(next_pass_review)
        and next_pass_promotion_ready(next_pass_promotion)
        and operator_feedback_candidate_promotion_ready(operator_feedback_candidate_promotion)
        and report.get("session_status") == "ready"
    )
    manifest = {
        "kind": OPERATOR_LOOP_KIND,
        "artifact_type": OPERATOR_LOOP_KIND,
        "schema_version": SCHEMA_VERSION,
        "loop_id": run.get("loop_id", "unknown"),
        "project_id": run.get("project_id", "unknown"),
        "generated_at": generated_at,
        "provider_mode": "no-provider",
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "chain_status": "ready" if ready else "blocked",
        "operator_loop_nodes": _operator_loop_nodes(
            loop,
            run,
            next_task_packet,
            next_pass_result,
            next_pass_review,
            next_pass_promotion,
            operator_feedback_candidate_promotion,
            report,
            packet,
        ),
        "context_summary": {
            "context_bundle_id": context.get("bundle_id", "unknown"),
            "included_ref_count": len(context.get("included_refs", [])),
            "blocked_ref_count": len(context.get("blocked_refs", [])),
        },
        "session_report": _session_report_summary(report),
        "next_context_handoff": _handoff_summary(handoff),
        "next_task_packet": _next_task_packet_summary(next_task_packet),
        "company_kb_feedback": _company_kb_summary(packet),
        "controls": _controls(run, packet, next_pass_promotion, operator_feedback_candidate_promotion),
        "non_claim_boundaries": report.get("claim_boundaries", {}),
        "output_artifacts": operator_output_artifacts(
            include_next_pass_result=next_pass_result is not None,
            include_next_pass_review=next_pass_review is not None,
            include_next_pass_promotion=next_pass_promotion is not None,
            include_operator_feedback_candidate_promotion=operator_feedback_candidate_promotion is not None,
        ),
    }
    if next_pass_result is not None:
        manifest["next_pass_result"] = next_pass_result_summary(next_pass_result)
    if next_pass_review is not None:
        manifest["next_pass_review"] = next_pass_review_summary(next_pass_review)
    if next_pass_promotion is not None:
        manifest["next_pass_promotion"] = next_pass_promotion_summary(next_pass_promotion)
    if operator_feedback_candidate_promotion is not None:
        manifest["operator_feedback_candidate_promotion"] = operator_feedback_candidate_promotion_summary(
            operator_feedback_candidate_promotion
        )
    return manifest


def _operator_loop_nodes(
    loop: dict[str, Any],
    run: dict[str, Any],
    next_task_packet: dict[str, Any],
    next_pass_result: dict[str, Any] | None,
    next_pass_review: dict[str, Any] | None,
    next_pass_promotion: dict[str, Any] | None,
    operator_feedback_candidate_promotion: dict[str, Any] | None,
    report: dict[str, Any],
    packet: dict[str, Any],
) -> list[dict[str, Any]]:
    context = run["context_bundle"]
    readiness = run["pass_readiness"]
    nodes = [
        _node("project_input", "ready", loop.get("project_input", {}).get("project_id", "unknown")),
        _node("artifact_ledger", "ready", f"{len(loop.get('artifact_ledger', []))} records"),
        _node("feedback_events", "evidence_only", f"{len(loop.get('feedback_events', []))} events"),
        _node("memory_candidates", "candidate_or_promoted", f"{len(loop.get('memory_candidates', []))} candidates"),
        _node("promotion_decisions", "explicit_decisions", f"{len(loop.get('promotion_decisions', []))} decisions"),
        _node("context_bundle", "ready", context.get("bundle_id", "unknown"), CONTEXT_BUNDLE_KIND),
        _node(
            "pass_readiness",
            "ready" if readiness.get("ready") else "blocked",
            readiness.get("overall_status", FAILED),
            PASS_READINESS_KIND,
        ),
        _node("next_pass_bundle", "planned", "no-provider execution remains planned", NEXT_PASS_BUNDLE_KIND),
        _node("next_context_handoff", "ready", "next AI task context handoff", NEXT_CONTEXT_HANDOFF_KIND),
        _node(
            "next_task_packet",
            next_task_packet.get("packet_status", "unknown"),
            "next AI task packet",
            NEXT_TASK_PACKET_KIND,
        ),
    ]
    nodes.extend(next_pass_nodes(next_pass_result, next_pass_review, next_pass_promotion))
    if operator_feedback_candidate_promotion is not None:
        nodes.extend(operator_feedback_candidate_promotion_nodes(operator_feedback_candidate_promotion))
    nodes.extend(
        [
            _node("session_report", report.get("session_status", "unknown"), report.get("session_id", "unknown"), SESSION_REPORT_KIND),
            _node(
                "company_kb_feedback_candidate_packet",
                packet.get("promotion_status", "unknown"),
                packet.get("packet_id", "unknown"),
                COMPANY_KB_FEEDBACK_PACKET_KIND,
            ),
        ]
    )
    return nodes


def _controls(
    run: dict[str, Any],
    packet: dict[str, Any],
    next_pass_promotion: dict[str, Any] | None,
    operator_feedback_candidate_promotion: dict[str, Any] | None,
) -> list[dict[str, str]]:
    controls = [
        _control("no_provider_mode", run.get("provider_mode") == "no-provider"),
        _control("provider_calls_not_started", run.get("provider_calls_started") is False),
        _control("long_term_memory_write_disabled", run.get("writes_long_term_memory") is False),
        _control("company_kb_write_disabled", packet.get("writes_company_kb") is False),
        _control("company_feedback_candidate_only", packet.get("promotion_status") == "candidate_only"),
        _control("human_review_required_for_company_feedback", packet.get("requires_human_review") is True),
    ]
    if next_pass_promotion is not None:
        controls.extend(next_pass_promotion_controls(next_pass_promotion))
    if operator_feedback_candidate_promotion is not None:
        controls.extend(operator_feedback_candidate_promotion_controls(operator_feedback_candidate_promotion))
    return controls


def _session_report_summary(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "session_id": report.get("session_id", "unknown"),
        "session_status": report.get("session_status", "unknown"),
        "next_operator_action": report.get("next_operator_action", {}).get("action", "unknown"),
    }


def _handoff_summary(handoff: dict[str, Any]) -> dict[str, Any]:
    return {
        "handoff_id": handoff.get("handoff_id", "unknown"),
        "handoff_status": handoff.get("handoff_status", "unknown"),
        "next_context_ref_count": len(handoff.get("next_context_refs", [])),
        "blocked_ref_count": len(handoff.get("blocked_refs", [])),
    }


def _next_task_packet_summary(packet: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_packet_id": packet.get("task_packet_id", "unknown"),
        "packet_status": packet.get("packet_status", "unknown"),
        "allowed_ref_count": len(packet.get("allowed_context_refs", [])),
        "blocked_ref_count": len(packet.get("blocked_refs", [])),
    }


def _company_kb_summary(packet: dict[str, Any]) -> dict[str, Any]:
    return {
        "packet_id": packet.get("packet_id", "unknown"),
        "promotion_status": packet.get("promotion_status", "unknown"),
        "candidate_item_count": len(packet.get("candidate_items", [])),
        "requires_human_review": packet.get("requires_human_review") is True,
        "writes_company_kb": packet.get("writes_company_kb") is True,
    }


def _node(node_id: str, status: str, detail: Any, artifact_type: str | None = None) -> dict[str, str]:
    node = {"node_id": node_id, "status": str(status), "detail": str(detail)}
    if artifact_type:
        node["artifact_type"] = artifact_type
    return node


def _control(control_id: str, passed: bool) -> dict[str, str]:
    return {"control_id": control_id, "status": PASSED if passed else FAILED}


__all__ = ("build_operator_manifest",)
