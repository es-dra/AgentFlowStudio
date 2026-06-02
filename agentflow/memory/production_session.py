from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentflow.harness.constants import AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS
from agentflow.memory.production_loop import RUN_KIND, SCHEMA_VERSION
from agentflow_studio.utils import write_json

SESSION_REPORT_KIND = "agentflow_production_memory_session_report"


def load_production_memory_run(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("production memory loop run must be a JSON object")
    return payload


def build_production_memory_session_report(
    run: dict[str, Any],
    *,
    generated_at: str,
    feedback_capture: dict[str, Any] | None = None,
    promotion_decision: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a read-only operator report from a no-provider production-memory run."""
    _validate_run(run)
    if not isinstance(generated_at, str) or not generated_at.strip():
        raise ValueError("generated_at is required")

    context_bundle = _dict(run.get("context_bundle"))
    pass_readiness = _dict(run.get("pass_readiness"))
    next_pass_bundle = _dict(run.get("next_pass_bundle"))
    included_refs = _ref_list(context_bundle.get("included_refs"))
    blocked_refs = _ref_list(context_bundle.get("blocked_refs"))
    ready = pass_readiness.get("ready") is True
    report = {
        "kind": SESSION_REPORT_KIND,
        "artifact_type": SESSION_REPORT_KIND,
        "schema_version": SCHEMA_VERSION,
        "session_id": f"session:{run.get('loop_id', 'production-memory-loop')}:no-provider",
        "loop_id": run.get("loop_id", "unknown"),
        "project_id": run.get("project_id", "unknown"),
        "generated_at": generated_at,
        "session_status": "ready" if ready else "blocked",
        "provider_mode": "no-provider",
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "context_summary": {
            "context_bundle_id": context_bundle.get("bundle_id", "unknown"),
            "included_ref_count": len(included_refs),
            "blocked_ref_count": len(blocked_refs),
            "included_refs": included_refs,
            "blocked_refs": blocked_refs,
        },
        "feedback_capture": _feedback_summary(feedback_capture),
        "promotion_decision": _promotion_summary(promotion_decision),
        "readiness": {
            "ready": ready,
            "overall_status": pass_readiness.get("overall_status", "failed"),
            "checks": _ref_list(pass_readiness.get("checks")),
        },
        "next_context_refs": _ref_list(next_pass_bundle.get("context_refs")),
        "next_operator_action": _next_operator_action(ready, blocked_refs, feedback_capture, promotion_decision),
        "claim_boundaries": _claim_boundaries(next_pass_bundle),
    }
    _reject_unsafe(report)
    return report


def write_production_memory_session_report(report: dict[str, Any], output_dir: str | Path) -> list[Path]:
    output_root = Path(output_dir)
    return [
        write_json(output_root / "production_memory_session_report.json", report),
        _write_text(output_root / "production_memory_session_report.md", render_production_memory_session_markdown(report)),
    ]


def render_production_memory_session_markdown(report: dict[str, Any]) -> str:
    included = _dict(report.get("context_summary")).get("included_refs", [])
    blocked = _dict(report.get("context_summary")).get("blocked_refs", [])
    action = _dict(report.get("next_operator_action"))
    boundaries = _dict(report.get("claim_boundaries"))
    lines = [
        "# Production Memory Session Report",
        "",
        f"Session status: {report.get('session_status', 'unknown')}",
        "Provider calls: not started",
        "Writes long-term memory: false",
        f"Human acceptance: {boundaries.get('human_acceptance', 'not_reviewed')}",
        f"Business validation: {boundaries.get('business_validation', 'not_validated')}",
        "",
        "## Included Refs",
        *[f"- {ref.get('ref_id')} ({ref.get('source_record_type', 'unknown')})" for ref in included],
        "",
        "## Blocked Refs",
        *[f"- {ref.get('ref_id')}: {ref.get('reason', 'unknown')}" for ref in blocked],
        "",
        "## Next Operator Action",
        f"{action.get('action', 'unknown')}: {action.get('reason', '')}",
        "",
    ]
    return "\n".join(lines)


def _validate_run(run: dict[str, Any]) -> None:
    if run.get("kind") != RUN_KIND:
        raise ValueError(f"session report requires production memory loop run kind {RUN_KIND}")
    if run.get("provider_mode") != "no-provider":
        raise ValueError("session report only supports no-provider production memory runs")
    if run.get("provider_calls_started") is not False:
        raise ValueError("session report requires provider_calls_started false")
    if run.get("writes_long_term_memory") is not False:
        raise ValueError("session report requires writes_long_term_memory false")
    context_bundle = _dict(run.get("context_bundle"))
    next_pass_bundle = _dict(run.get("next_pass_bundle"))
    if not isinstance(context_bundle.get("included_refs"), list) or not isinstance(context_bundle.get("blocked_refs"), list):
        raise ValueError("session report requires context bundle included_refs and blocked_refs")
    if not isinstance(next_pass_bundle.get("context_refs"), list):
        raise ValueError("session report requires next pass context_refs")
    _reject_unsafe(run)


def _feedback_summary(feedback_capture: dict[str, Any] | None) -> dict[str, Any]:
    if not feedback_capture:
        return {"status": "not_provided"}
    feedback = _dict(feedback_capture.get("feedback_event"))
    candidate = _dict(feedback_capture.get("memory_candidate"))
    return {
        "status": feedback_capture.get("execution_status", "draft"),
        "target_ref": feedback_capture.get("target_ref", feedback.get("target_ref")),
        "feedback_id": feedback.get("feedback_id"),
        "decision": feedback.get("decision"),
        "candidate_id": candidate.get("candidate_id"),
        "candidate_status": candidate.get("status"),
        "writes_long_term_memory": False,
    }


def _promotion_summary(promotion_decision: dict[str, Any] | None) -> dict[str, Any]:
    if not promotion_decision:
        return {"status": "not_provided"}
    return {
        "status": "reviewed",
        "decision_id": promotion_decision.get("decision_id"),
        "candidate_id": promotion_decision.get("candidate_id"),
        "decision": promotion_decision.get("decision"),
        "review_mode": promotion_decision.get("review_mode"),
        "writes_long_term_memory": False,
    }


def _next_operator_action(
    ready: bool,
    blocked_refs: list[dict[str, Any]],
    feedback_capture: dict[str, Any] | None,
    promotion_decision: dict[str, Any] | None,
) -> dict[str, str]:
    if any(ref.get("reason") == "promotion_decision_rejected" for ref in blocked_refs):
        return {"action": "resolve_blocked_refs", "reason": "a reviewed promotion decision rejected a candidate"}
    if feedback_capture and not promotion_decision:
        return {"action": "review_promotion_decision", "reason": "feedback capture has no reviewed promotion decision"}
    if not ready:
        return {"action": "resolve_blocked_refs", "reason": "pass readiness is blocked"}
    return {"action": "prepare_next_pass", "reason": "use included refs only and keep blocked refs out"}


def _claim_boundaries(next_pass_bundle: dict[str, Any]) -> dict[str, str]:
    boundaries = _dict(next_pass_bundle.get("claim_boundaries"))
    return {
        "human_acceptance": str(boundaries.get("human_acceptance", "not_reviewed")),
        "business_validation": str(boundaries.get("business_validation", "not_validated")),
        "provider_success": str(boundaries.get("provider_success", "not_attempted")),
        "durable_memory_runtime": str(boundaries.get("durable_memory_runtime", "not_implemented")),
    }


def _write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _reject_unsafe(value: Any) -> None:
    raw = json.dumps(value, ensure_ascii=False).lower()
    if any(fragment.lower() in raw for fragment in AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS):
        raise ValueError("production memory session report contains unsafe path, generated artifact path, or secret")


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _ref_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


__all__ = (
    "SESSION_REPORT_KIND",
    "build_production_memory_session_report",
    "load_production_memory_run",
    "render_production_memory_session_markdown",
    "write_production_memory_session_report",
)
