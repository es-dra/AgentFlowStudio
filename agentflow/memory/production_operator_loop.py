from __future__ import annotations

from pathlib import Path
from typing import Any

from agentflow.harness.constants import FAILED, PASSED
from agentflow.memory.company_kb_feedback import (
    COMPANY_KB_FEEDBACK_PACKET_KIND,
    build_company_kb_feedback_candidate_packet,
    write_company_kb_feedback_candidate_packet,
)
from agentflow.memory.production_loop import (
    CONTEXT_BUNDLE_KIND,
    PASS_READINESS_KIND,
    RUN_KIND,
    SCHEMA_VERSION,
    build_production_memory_loop_run,
    write_production_memory_loop_run,
)
from agentflow.memory.production_next_pass import NEXT_PASS_BUNDLE_KIND
from agentflow.memory.production_session import (
    SESSION_REPORT_KIND,
    build_production_memory_session_report,
    write_production_memory_session_report,
)
from narratocut.utils import write_json

OPERATOR_LOOP_KIND = "agentflow_production_memory_operator_loop_run"


def build_production_memory_operator_loop_run(
    loop: dict[str, Any],
    *,
    generated_at: str,
    source_kb_status: str = "restructuring_or_unknown",
) -> dict[str, Any]:
    """Build an auditable no-provider operator loop from source loop to feedback packet."""
    if not isinstance(generated_at, str) or not generated_at.strip():
        raise ValueError("generated_at is required")
    run = build_production_memory_loop_run(loop)
    report = build_production_memory_session_report(run, generated_at=generated_at)
    packet = build_company_kb_feedback_candidate_packet(
        report,
        generated_at=generated_at,
        source_kb_status=source_kb_status,
    )
    manifest = _build_manifest(loop, run, report, packet, generated_at=generated_at)
    return {
        "manifest": manifest,
        "run": run,
        "session_report": report,
        "company_kb_feedback_candidate_packet": packet,
    }


def write_production_memory_operator_loop_run(result: dict[str, Any], output_dir: str | Path) -> list[Path]:
    output_root = Path(output_dir)
    written_paths: list[Path] = []
    written_paths.extend(write_production_memory_loop_run(result["run"], output_root / "run"))
    written_paths.extend(write_production_memory_session_report(result["session_report"], output_root / "session_report"))
    written_paths.extend(
        write_company_kb_feedback_candidate_packet(
            result["company_kb_feedback_candidate_packet"],
            output_root / "company_kb_candidates",
        )
    )
    manifest = {
        **result["manifest"],
        "output_artifacts": _output_artifacts(),
    }
    written_paths.append(write_json(output_root / "production_memory_operator_loop_run.json", manifest))
    result["manifest"] = manifest
    return written_paths


def _build_manifest(
    loop: dict[str, Any],
    run: dict[str, Any],
    report: dict[str, Any],
    packet: dict[str, Any],
    *,
    generated_at: str,
) -> dict[str, Any]:
    readiness = run["pass_readiness"]
    context = run["context_bundle"]
    ready = readiness.get("ready") is True and report.get("session_status") == "ready"
    return {
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
        "operator_loop_nodes": _operator_loop_nodes(loop, run, report, packet),
        "context_summary": {
            "context_bundle_id": context.get("bundle_id", "unknown"),
            "included_ref_count": len(context.get("included_refs", [])),
            "blocked_ref_count": len(context.get("blocked_refs", [])),
        },
        "session_report": {
            "session_id": report.get("session_id", "unknown"),
            "session_status": report.get("session_status", "unknown"),
            "next_operator_action": report.get("next_operator_action", {}).get("action", "unknown"),
        },
        "company_kb_feedback": {
            "packet_id": packet.get("packet_id", "unknown"),
            "promotion_status": packet.get("promotion_status", "unknown"),
            "candidate_item_count": len(packet.get("candidate_items", [])),
            "requires_human_review": packet.get("requires_human_review") is True,
            "writes_company_kb": packet.get("writes_company_kb") is True,
        },
        "controls": _controls(run, packet),
        "non_claim_boundaries": report.get("claim_boundaries", {}),
        "output_artifacts": [],
    }


def _operator_loop_nodes(
    loop: dict[str, Any],
    run: dict[str, Any],
    report: dict[str, Any],
    packet: dict[str, Any],
) -> list[dict[str, Any]]:
    context = run["context_bundle"]
    readiness = run["pass_readiness"]
    return [
        _node("project_input", "ready", loop.get("project_input", {}).get("project_id", "unknown")),
        _node("artifact_ledger", "ready", f"{len(loop.get('artifact_ledger', []))} records"),
        _node("feedback_events", "evidence_only", f"{len(loop.get('feedback_events', []))} events"),
        _node("memory_candidates", "candidate_or_promoted", f"{len(loop.get('memory_candidates', []))} candidates"),
        _node("promotion_decisions", "explicit_decisions", f"{len(loop.get('promotion_decisions', []))} decisions"),
        _node("context_bundle", "ready", context.get("bundle_id", "unknown"), CONTEXT_BUNDLE_KIND),
        _node("pass_readiness", "ready" if readiness.get("ready") else "blocked", readiness.get("overall_status", FAILED), PASS_READINESS_KIND),
        _node("next_pass_bundle", "planned", "no-provider execution remains planned", NEXT_PASS_BUNDLE_KIND),
        _node("session_report", report.get("session_status", "unknown"), report.get("session_id", "unknown"), SESSION_REPORT_KIND),
        _node(
            "company_kb_feedback_candidate_packet",
            packet.get("promotion_status", "unknown"),
            packet.get("packet_id", "unknown"),
            COMPANY_KB_FEEDBACK_PACKET_KIND,
        ),
    ]


def _controls(run: dict[str, Any], packet: dict[str, Any]) -> list[dict[str, str]]:
    return [
        _control("no_provider_mode", run.get("provider_mode") == "no-provider"),
        _control("provider_calls_not_started", run.get("provider_calls_started") is False),
        _control("long_term_memory_write_disabled", run.get("writes_long_term_memory") is False),
        _control("company_kb_write_disabled", packet.get("writes_company_kb") is False),
        _control("company_feedback_candidate_only", packet.get("promotion_status") == "candidate_only"),
        _control("human_review_required_for_company_feedback", packet.get("requires_human_review") is True),
    ]


def _output_artifacts() -> list[dict[str, Any]]:
    return [
        _artifact(RUN_KIND, "run/production_memory_loop_run.json"),
        _artifact(CONTEXT_BUNDLE_KIND, "run/context_bundle.json"),
        _artifact(PASS_READINESS_KIND, "run/pass_readiness.json"),
        _artifact(NEXT_PASS_BUNDLE_KIND, "run/next_pass_bundle.json"),
        _artifact(SESSION_REPORT_KIND, "session_report/production_memory_session_report.json"),
        _artifact("markdown_report", "session_report/production_memory_session_report.md"),
        _artifact(COMPANY_KB_FEEDBACK_PACKET_KIND, "company_kb_candidates/company_kb_feedback_candidate_packet.json"),
        _artifact("markdown_report", "company_kb_candidates/company_kb_feedback_candidate_packet.md"),
        _artifact(OPERATOR_LOOP_KIND, "production_memory_operator_loop_run.json"),
    ]


def _node(node_id: str, status: str, detail: Any, artifact_type: str | None = None) -> dict[str, str]:
    node = {"node_id": node_id, "status": str(status), "detail": str(detail)}
    if artifact_type:
        node["artifact_type"] = artifact_type
    return node


def _control(control_id: str, passed: bool) -> dict[str, str]:
    return {"control_id": control_id, "status": PASSED if passed else FAILED}


def _artifact(artifact_type: str, path: str) -> dict[str, Any]:
    return {"artifact_type": artifact_type, "path": path, "required": True}


__all__ = (
    "OPERATOR_LOOP_KIND",
    "build_production_memory_operator_loop_run",
    "write_production_memory_operator_loop_run",
)
