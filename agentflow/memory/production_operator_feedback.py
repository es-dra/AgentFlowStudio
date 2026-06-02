from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentflow.harness.constants import AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS
from agentflow.memory.production_loop import SCHEMA_VERSION
from agentflow.memory.production_operator_outputs import OPERATOR_LOOP_KIND
from narratocut.utils import write_json

OPERATOR_FEEDBACK_EVENT_KIND = "agentflow_production_memory_operator_feedback_event"
SUPPORTED_OPERATOR_FEEDBACK_DECISIONS = frozenset({"accepted", "rejected", "needs_revision", "note"})
UNSAFE_EXTRA_FRAGMENTS = (
    "http://",
    "https://",
    "file://",
    "data:image/",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
)


def load_production_memory_operator_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("production memory operator manifest must be a JSON object")
    return payload


def build_production_memory_operator_feedback_event(
    manifest: dict[str, Any],
    *,
    target_node_id: str,
    decision: str,
    summary: str,
    reviewer_role: str,
    reviewed_at: str,
) -> dict[str, Any]:
    """Capture operator feedback about one manifest node without promoting it."""
    _validate_manifest(manifest)
    _validate_inputs(target_node_id, decision, summary, reviewer_role, reviewed_at)
    target = _node_by_id(manifest, target_node_id)
    if target is None:
        raise ValueError(f"target_node_id does not exist in operator_loop_nodes: {target_node_id}")

    event = {
        "kind": OPERATOR_FEEDBACK_EVENT_KIND,
        "artifact_type": OPERATOR_FEEDBACK_EVENT_KIND,
        "schema_version": manifest.get("schema_version", SCHEMA_VERSION),
        "feedback_id": _safe_id("operator-feedback", manifest.get("loop_id", "unknown"), target_node_id, reviewed_at),
        "feedback_scope": "operator_loop_node",
        "status": "evidence_only",
        "source_operator_loop_id": manifest.get("loop_id", "unknown"),
        "source_project_id": manifest.get("project_id", "unknown"),
        "source_chain_status": manifest.get("chain_status", "unknown"),
        "target_node_id": target_node_id,
        "target_node_status": target.get("status", "unknown"),
        "target_artifact_type": target.get("artifact_type", "operator_loop_node"),
        "target_detail": target.get("detail", ""),
        "decision": decision,
        "summary": summary,
        "reviewer_role": reviewer_role,
        "reviewed_at": reviewed_at,
        "provider_mode": "no-provider",
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "feedback_is_memory": False,
        "creates_memory_candidate": False,
        "creates_promotion_decision": False,
        "claim_boundaries": _claim_boundaries(),
        "non_claims": _non_claims(),
    }
    _reject_unsafe(event)
    return event


def write_production_memory_operator_feedback_event(event: dict[str, Any], output_dir: str | Path) -> list[Path]:
    output_root = Path(output_dir)
    json_path = write_json(output_root / "operator_feedback_event.json", event)
    md_path = output_root / "operator_feedback_event.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_operator_feedback_markdown(event), encoding="utf-8")
    return [json_path, md_path]


def render_operator_feedback_markdown(event: dict[str, Any]) -> str:
    boundaries = _dict(event.get("claim_boundaries"))
    return "\n".join(
        [
            "# Production Memory Operator Feedback Event",
            "",
            f"Status: {event.get('status', 'unknown')}",
            f"Target node: {event.get('target_node_id', 'unknown')}",
            f"Decision: {event.get('decision', 'unknown')}",
            "Provider calls: not started",
            "Writes long-term memory: false",
            "Writes Company KB: false",
            f"Human acceptance: {boundaries.get('human_acceptance', 'not_claimed')}",
            f"Business validation: {boundaries.get('business_validation', 'not_validated')}",
            "",
            "## Summary",
            str(event.get("summary", "")),
            "",
        ]
    )


def _validate_manifest(manifest: dict[str, Any]) -> None:
    if manifest.get("kind") != OPERATOR_LOOP_KIND:
        raise ValueError(f"operator feedback requires kind {OPERATOR_LOOP_KIND}")
    if manifest.get("provider_mode") != "no-provider":
        raise ValueError("operator feedback requires no-provider operator loop manifest")
    if manifest.get("provider_calls_started") is not False:
        raise ValueError("operator feedback requires provider_calls_started false")
    if manifest.get("writes_long_term_memory") is not False:
        raise ValueError("operator feedback requires writes_long_term_memory false")
    if manifest.get("writes_company_kb") is not False:
        raise ValueError("operator feedback requires writes_company_kb false")
    if not isinstance(manifest.get("operator_loop_nodes"), list):
        raise ValueError("operator feedback requires operator_loop_nodes")
    _reject_unsafe(manifest)


def _validate_inputs(
    target_node_id: str,
    decision: str,
    summary: str,
    reviewer_role: str,
    reviewed_at: str,
) -> None:
    for label, value in {
        "target_node_id": target_node_id,
        "summary": summary,
        "reviewer_role": reviewer_role,
        "reviewed_at": reviewed_at,
    }.items():
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{label} is required")
    if decision not in SUPPORTED_OPERATOR_FEEDBACK_DECISIONS:
        raise ValueError(f"unsupported operator feedback decision: {decision}")
    _reject_unsafe(
        {
            "target_node_id": target_node_id,
            "summary": summary,
            "reviewer_role": reviewer_role,
        }
    )


def _node_by_id(manifest: dict[str, Any], target_node_id: str) -> dict[str, Any] | None:
    for node in _list(manifest.get("operator_loop_nodes")):
        if _dict(node).get("node_id") == target_node_id:
            return _dict(node)
    return None


def _claim_boundaries() -> dict[str, str]:
    return {
        "human_acceptance": "not_claimed",
        "business_validation": "not_validated",
        "provider_success": "not_attempted",
        "durable_memory_runtime": "not_implemented",
        "company_kb_promotion": "not_performed",
    }


def _non_claims() -> list[str]:
    return [
        "not human acceptance",
        "not business validation",
        "not durable memory",
        "not provider success",
        "not Company KB promotion",
        "not memory promotion",
    ]


def _safe_id(*parts: str) -> str:
    raw = ":".join(parts)
    safe = "".join(char.lower() if char.isalnum() else "-" for char in raw).strip("-")
    while "--" in safe:
        safe = safe.replace("--", "-")
    return safe


def _reject_unsafe(value: Any) -> None:
    raw = json.dumps(value, ensure_ascii=False).lower()
    fragments = AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS + UNSAFE_EXTRA_FRAGMENTS
    if any(fragment.lower() in raw for fragment in fragments):
        raise ValueError("production memory operator feedback contains unsafe path, media reference, provider URL, or secret")


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


__all__ = (
    "OPERATOR_FEEDBACK_EVENT_KIND",
    "SUPPORTED_OPERATOR_FEEDBACK_DECISIONS",
    "build_production_memory_operator_feedback_event",
    "load_production_memory_operator_manifest",
    "render_operator_feedback_markdown",
    "write_production_memory_operator_feedback_event",
)
