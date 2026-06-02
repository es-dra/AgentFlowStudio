from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentflow.harness.constants import AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS
from agentflow.memory.production_session import SESSION_REPORT_KIND
from narratocut.utils import write_json

COMPANY_KB_FEEDBACK_PACKET_KIND = "agentflow_company_kb_feedback_candidate_packet"
COMPANY_KB_FEEDBACK_PACKET_SCHEMA_VERSION = "company-kb-feedback-candidate-packet/v1"


def load_company_kb_feedback_source_report(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("company KB feedback source session report must be a JSON object")
    return payload


def build_company_kb_feedback_candidate_packet(
    report: dict[str, Any],
    *,
    generated_at: str,
    source_kb_status: str = "restructuring_or_unknown",
) -> dict[str, Any]:
    """Build a candidate-only Company KB feedback packet from one session report."""
    _validate_report(report)
    if not isinstance(generated_at, str) or not generated_at.strip():
        raise ValueError("generated_at is required")
    if not isinstance(source_kb_status, str) or not source_kb_status.strip():
        raise ValueError("source_kb_status is required")

    context_summary = _dict(report.get("context_summary"))
    boundaries = _dict(report.get("claim_boundaries"))
    packet = {
        "kind": COMPANY_KB_FEEDBACK_PACKET_KIND,
        "artifact_type": COMPANY_KB_FEEDBACK_PACKET_KIND,
        "schema_version": COMPANY_KB_FEEDBACK_PACKET_SCHEMA_VERSION,
        "packet_id": f"company-kb-feedback:{report.get('session_id', 'unknown')}",
        "generated_at": generated_at,
        "source_kb_status": source_kb_status,
        "promotion_status": "candidate_only",
        "requires_human_review": True,
        "writes_company_kb": False,
        "writes_long_term_memory": False,
        "provider_calls_started": False,
        "source_report": _source_report(report),
        "target": {
            "system": "local_company_knowledge_base",
            "write_status": "not_written",
            "promotion_required": "explicit_human_review",
        },
        "context_signal": {
            "context_bundle_id": context_summary.get("context_bundle_id", "unknown"),
            "included_ref_count": int(context_summary.get("included_ref_count") or 0),
            "blocked_ref_count": int(context_summary.get("blocked_ref_count") or 0),
            "next_operator_action": _dict(report.get("next_operator_action")).get("action", "unknown"),
        },
        "non_claim_boundaries": {
            "human_acceptance": str(boundaries.get("human_acceptance", "not_reviewed")),
            "business_validation": str(boundaries.get("business_validation", "not_validated")),
            "provider_success": str(boundaries.get("provider_success", "not_attempted")),
            "durable_memory_runtime": str(boundaries.get("durable_memory_runtime", "not_implemented")),
        },
        "candidate_items": _candidate_items(report),
        "explicit_non_promotions": [
            "does_not_write_company_kb",
            "does_not_promote_company_memory",
            "does_not_claim_human_acceptance",
            "does_not_claim_business_validation",
            "does_not_authorize_provider_calls",
        ],
    }
    _reject_unsafe(packet)
    return packet


def write_company_kb_feedback_candidate_packet(packet: dict[str, Any], output_dir: str | Path) -> list[Path]:
    output_root = Path(output_dir)
    return [
        write_json(output_root / "company_kb_feedback_candidate_packet.json", packet),
        _write_text(
            output_root / "company_kb_feedback_candidate_packet.md",
            render_company_kb_feedback_candidate_markdown(packet),
        ),
    ]


def render_company_kb_feedback_candidate_markdown(packet: dict[str, Any]) -> str:
    lines = [
        "# Company KB Feedback Candidate Packet",
        "",
        "Status: candidate only. Do not auto-promote.",
        f"Writes Company KB: {str(packet.get('writes_company_kb') is True).lower()}",
        f"Requires human review: {str(packet.get('requires_human_review') is True).lower()}",
        f"Source KB status: {packet.get('source_kb_status', 'unknown')}",
        "",
        "## Candidate Items",
    ]
    for item in _list(packet.get("candidate_items")):
        lines.extend(
            [
                f"- {item.get('candidate_id')}",
                f"  - summary: {item.get('summary')}",
                f"  - promotion boundary: {item.get('promotion_boundary')}",
            ]
        )
    lines.extend(
        [
            "",
            "## Explicit Non-Promotions",
            *[f"- {item}" for item in _list(packet.get("explicit_non_promotions"))],
            "",
        ]
    )
    return "\n".join(lines)


def _validate_report(report: dict[str, Any]) -> None:
    if report.get("kind") != SESSION_REPORT_KIND:
        raise ValueError(f"company KB feedback requires session report kind {SESSION_REPORT_KIND}")
    if report.get("provider_mode") != "no-provider":
        raise ValueError("company KB feedback requires no-provider session report")
    if report.get("provider_calls_started") is not False:
        raise ValueError("company KB feedback requires provider_calls_started false")
    if report.get("writes_long_term_memory") is not False:
        raise ValueError("company KB feedback requires writes_long_term_memory false")
    if not isinstance(report.get("context_summary"), dict):
        raise ValueError("company KB feedback requires context_summary")
    _reject_unsafe(report)


def _source_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "session_id": report.get("session_id", "unknown"),
        "loop_id": report.get("loop_id", "unknown"),
        "project_id": report.get("project_id", "unknown"),
        "session_status": report.get("session_status", "unknown"),
        "generated_at": report.get("generated_at", "unknown"),
    }


def _candidate_items(report: dict[str, Any]) -> list[dict[str, Any]]:
    items = [
        _candidate_item(
            "company-kb:candidate:context-bundle-audit:v1",
            "Keep included and blocked refs together when handing off next-context evidence.",
            "Candidate only until compared against other AFS production loops.",
            report,
        ),
        _candidate_item(
            "company-kb:candidate:claim-boundary-discipline:v1",
            "Carry human acceptance, business validation, provider success, and durable memory as explicit non-claims.",
            "Candidate only; Company memory promotion requires human review.",
            report,
        ),
        _candidate_item(
            "company-kb:candidate:company-feedback-queue:v1",
            "Treat project-to-Company feedback as a candidate queue while the source KB is being restructured.",
            "Candidate only; do not write the source Company KB from AFS without explicit instruction.",
            report,
        ),
    ]
    if _dict(report.get("promotion_decision")).get("status") == "reviewed":
        items.append(
            _candidate_item(
                "company-kb:candidate:promotion-decision-overlay:v1",
                "Use reviewed promotion decisions as overlays before rebuilding next context.",
                "Candidate only; not durable Memory OS behavior until reviewed across more loops.",
                report,
            )
        )
    return items


def _candidate_item(
    candidate_id: str,
    summary: str,
    promotion_boundary: str,
    report: dict[str, Any],
) -> dict[str, Any]:
    context_summary = _dict(report.get("context_summary"))
    return {
        "candidate_id": candidate_id,
        "status": "candidate",
        "summary": summary,
        "promotion_boundary": promotion_boundary,
        "requires_human_review": True,
        "writes_company_kb": False,
        "source_session_id": report.get("session_id", "unknown"),
        "source_refs": [
            f"session:{report.get('session_id', 'unknown')}",
            f"context_bundle:{context_summary.get('context_bundle_id', 'unknown')}",
        ],
    }


def _write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _reject_unsafe(value: Any) -> None:
    raw = json.dumps(value, ensure_ascii=False).lower()
    if any(fragment.lower() in raw for fragment in AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS):
        raise ValueError("company KB feedback candidate packet contains unsafe path, generated artifact path, or secret")


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


__all__ = (
    "COMPANY_KB_FEEDBACK_PACKET_KIND",
    "COMPANY_KB_FEEDBACK_PACKET_SCHEMA_VERSION",
    "build_company_kb_feedback_candidate_packet",
    "load_company_kb_feedback_source_report",
    "render_company_kb_feedback_candidate_markdown",
    "write_company_kb_feedback_candidate_packet",
)
