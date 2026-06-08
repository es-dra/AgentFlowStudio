from __future__ import annotations

from pathlib import Path
from typing import Any

from agentflow.harness.constants import FAILED, PASSED
from agentflow.memory.production_loop import SCHEMA_VERSION
from agentflow.memory.production_operator_acceptance_feedback_candidate_handoff import (
    acceptance_feedback_candidate_promotion_markdown,
    acceptance_feedback_candidate_promotion_prompt,
)
from agentflow.memory.production_operator_manifest_check import OPERATOR_MANIFEST_CHECK_KIND
from agentflow.memory.production_operator_outputs import OPERATOR_LOOP_KIND
from agentflow.harness.json_io import write_json

OPERATOR_HANDOFF_PACKET_KIND = "agentflow_production_memory_operator_handoff_packet"


def build_operator_handoff_packet(
    manifest: dict[str, Any],
    *,
    manifest_check: dict[str, Any] | None = None,
    generated_at: str,
) -> dict[str, Any]:
    """Build a no-provider handoff packet for the next operator or agent."""
    _validate_manifest(manifest)
    _validate_check(manifest_check)
    if not isinstance(generated_at, str) or not generated_at.strip():
        raise ValueError("generated_at is required")

    blocked_items = _blocked_items(manifest, manifest_check)
    ready = not blocked_items
    check_status = manifest_check.get("check_status", "unknown") if manifest_check else "not_supplied"
    output_artifacts = _list(manifest.get("output_artifacts"))
    packet = {
        "kind": OPERATOR_HANDOFF_PACKET_KIND,
        "artifact_type": OPERATOR_HANDOFF_PACKET_KIND,
        "schema_version": manifest.get("schema_version", SCHEMA_VERSION),
        "handoff_id": f"operator-handoff:{manifest.get('loop_id', 'unknown')}",
        "generated_at": generated_at,
        "source_operator_loop_id": manifest.get("loop_id", "unknown"),
        "project_id": manifest.get("project_id", "unknown"),
        "handoff_status": "ready" if ready else "blocked",
        "manifest_chain_status": manifest.get("chain_status", "unknown"),
        "manifest_check_status": check_status,
        "checked_ref_count": manifest_check.get("checked_ref_count", 0) if manifest_check else 0,
        "output_artifact_count": len(output_artifacts),
        "context_summary": _dict(manifest.get("context_summary")),
        "next_task_packet": _dict(manifest.get("next_task_packet")),
        "next_operator_action": _next_operator_action(manifest, manifest_check, blocked_items),
        "provider_mode": "no-provider",
        "provider_calls_started": manifest.get("provider_calls_started") is True,
        "writes_long_term_memory": manifest.get("writes_long_term_memory") is True,
        "writes_company_kb": manifest.get("writes_company_kb") is True,
        "artifact_refs": _artifact_refs(output_artifacts),
        "blocked_items": blocked_items,
        "handoff_prompt": _handoff_prompt(manifest, ready),
        "controls": _controls(manifest, manifest_check, ready),
        "non_claims": _non_claims(),
        "claim_boundaries": _claim_boundaries(manifest, manifest_check),
    }
    acceptance_feedback_promotion = _dict(manifest.get("acceptance_feedback_candidate_promotion"))
    if acceptance_feedback_promotion:
        packet["acceptance_feedback_candidate_promotion"] = acceptance_feedback_promotion
    return packet


def write_operator_handoff_packet(packet: dict[str, Any], output_dir: str | Path) -> list[Path]:
    output_root = Path(output_dir)
    json_path = write_json(output_root / "operator_handoff_packet.json", packet)
    md_path = output_root / "operator_handoff_packet.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_operator_handoff_packet_markdown(packet), encoding="utf-8")
    return [json_path, md_path]


def render_operator_handoff_packet_markdown(packet: dict[str, Any]) -> str:
    action = _dict(packet.get("next_operator_action"))
    return "\n".join(
        [
            "# Production Memory Operator Handoff Packet",
            "",
            f"Status: {packet.get('handoff_status', 'unknown')}",
            f"Project: {packet.get('project_id', 'unknown')}",
            f"Operator loop: {packet.get('source_operator_loop_id', 'unknown')}",
            f"Manifest check: {packet.get('manifest_check_status', 'unknown')}",
            f"Next operator action: {action.get('action', 'unknown')}",
            "",
            f"Provider calls: {_started_label(packet.get('provider_calls_started'))}",
            f"Durable memory write: {_enabled_label(packet.get('writes_long_term_memory'))}",
            f"Company KB write: {_enabled_label(packet.get('writes_company_kb'))}",
            "",
            "## Handoff Prompt",
            "",
            str(packet.get("handoff_prompt", "")),
            "",
            acceptance_feedback_candidate_promotion_markdown(
                packet.get("acceptance_feedback_candidate_promotion")
            ),
            "",
            "## Artifact Refs",
            "",
            _artifact_table(packet.get("artifact_refs")),
            "",
            "## Blocked Items",
            "",
            _blocked_table(packet.get("blocked_items")),
            "",
            "## Non-claims",
            "",
            "\n".join(f"- {item}" for item in _list(packet.get("non_claims"))),
            "",
        ]
    )


def _validate_manifest(manifest: dict[str, Any]) -> None:
    if not isinstance(manifest, dict):
        raise ValueError("operator handoff requires operator manifest JSON object")
    if manifest.get("kind") != OPERATOR_LOOP_KIND:
        raise ValueError(f"operator handoff requires kind {OPERATOR_LOOP_KIND}")


def _validate_check(manifest_check: dict[str, Any] | None) -> None:
    if manifest_check is None:
        return
    if not isinstance(manifest_check, dict):
        raise ValueError("operator manifest check must be a JSON object")
    if manifest_check.get("kind") != OPERATOR_MANIFEST_CHECK_KIND:
        raise ValueError(f"operator handoff manifest check requires kind {OPERATOR_MANIFEST_CHECK_KIND}")


def _blocked_items(manifest: dict[str, Any], manifest_check: dict[str, Any] | None) -> list[dict[str, str]]:
    blocked: list[dict[str, str]] = []
    if manifest.get("chain_status") != "ready":
        blocked.append({"ref": "operator_loop", "reason": "operator manifest chain is not ready"})
    if manifest.get("provider_calls_started") is True:
        blocked.append({"ref": "provider_calls", "reason": "provider calls started before no-provider handoff"})
    if manifest.get("writes_long_term_memory") is True:
        blocked.append({"ref": "long_term_memory", "reason": "handoff source writes durable memory"})
    if manifest.get("writes_company_kb") is True:
        blocked.append({"ref": "company_kb", "reason": "handoff source writes Company KB"})
    if manifest_check is None:
        blocked.append({"ref": "operator_manifest_check", "reason": "operator manifest check is required before handoff readiness"})
        return blocked
    if manifest_check.get("check_status") != "passed":
        blocked.append({"ref": "operator_manifest_check", "reason": "operator manifest check did not pass"})
    blocked.extend({"ref": str(item), "reason": "missing operator artifact ref"} for item in _list(manifest_check.get("missing_refs")))
    blocked.extend({"ref": str(_dict(item).get("path", "unknown")), "reason": "mismatched operator artifact type"} for item in _list(manifest_check.get("mismatched_refs")))
    blocked.extend({"ref": str(item), "reason": "unsafe operator artifact ref"} for item in _list(manifest_check.get("unsafe_refs")))
    blocked.extend({"ref": str(_dict(item).get("node_id", "unknown")), "reason": "operator node failed"} for item in _list(manifest_check.get("failed_nodes")))
    blocked.extend({"ref": str(_dict(item).get("control_id", "unknown")), "reason": "operator control failed"} for item in _list(manifest_check.get("failed_controls")))
    return blocked


def _next_operator_action(
    manifest: dict[str, Any],
    manifest_check: dict[str, Any] | None,
    blocked_items: list[dict[str, str]],
) -> dict[str, str]:
    if manifest_check is None:
        return _action("run_operator_manifest_check", "blocked", "Run the operator manifest check before handoff readiness.")
    if manifest_check.get("check_status") != "passed":
        return _action("resolve_operator_manifest_check_blockers", "blocked", f"{len(blocked_items)} blockers found.")
    if manifest.get("chain_status") != "ready":
        return _action("resolve_operator_loop_blockers", "blocked", "Operator manifest is not ready.")
    if manifest.get("next_pass_review") and not manifest.get("next_pass_promotion"):
        return _action("review_next_pass_feedback_candidates", "ready", "Explicit promotion decision is required.")
    if manifest.get("next_pass_result") and not manifest.get("next_pass_review"):
        return _action("review_or_complete_next_pass_result", "ready", "Review the scaffolded or explicit next-pass result.")
    acceptance_feedback_promotion = _dict(manifest.get("acceptance_feedback_candidate_promotion"))
    if acceptance_feedback_promotion.get("candidate_included_in_context") is True:
        return _action(
            "run_next_ai_task_with_acceptance_feedback_context",
            "ready",
            "Use the generated next-task packet with promoted acceptance feedback candidate context.",
        )
    if acceptance_feedback_promotion.get("candidate_blocked_from_context") is True:
        return _action(
            "run_next_ai_task_without_acceptance_feedback_candidate",
            "ready",
            "Use the generated next-task packet without blocked acceptance feedback candidate refs.",
        )
    return _action("run_next_ai_task_from_next_task_packet", "ready", "Use the generated next-task packet.")


def _handoff_prompt(manifest: dict[str, Any], ready: bool) -> str:
    packet = _dict(manifest.get("next_task_packet"))
    prefix = "Use the generated next_task_packet for the next AI task." if ready else "Resolve blocked_items before the next AI task."
    acceptance_feedback_clause = acceptance_feedback_candidate_promotion_prompt(
        manifest.get("acceptance_feedback_candidate_promotion")
    )
    return (
        f"{prefix} Task packet: {packet.get('task_packet_id', 'unknown')}. "
        f"{acceptance_feedback_clause}"
        "Do not use blocked refs, unpromoted candidates, or feedback events as memory. "
        "Do not call remote providers without an explicit provider gate. "
        "Do not write Company KB or durable memory from this handoff."
    )


def _controls(manifest: dict[str, Any], manifest_check: dict[str, Any] | None, ready: bool) -> list[dict[str, str]]:
    return [
        _control("manifest_chain_ready", manifest.get("chain_status") == "ready"),
        _control("operator_manifest_check_supplied", manifest_check is not None),
        _control("operator_manifest_check_passed", manifest_check is not None and manifest_check.get("check_status") == "passed"),
        _control("provider_calls_not_started", manifest.get("provider_calls_started") is False),
        _control("long_term_memory_write_disabled", manifest.get("writes_long_term_memory") is False),
        _control("company_kb_write_disabled", manifest.get("writes_company_kb") is False),
        _control("operator_handoff_ready", ready),
    ]


def _artifact_refs(output_artifacts: list[Any]) -> list[dict[str, str]]:
    refs = []
    for item in output_artifacts:
        artifact = _dict(item)
        refs.append(
            {
                "path": str(artifact.get("path", "unknown")),
                "artifact_type": str(artifact.get("artifact_type", "unknown")),
                "required": str(artifact.get("required", True)).lower(),
            }
        )
    return refs


def _claim_boundaries(manifest: dict[str, Any], manifest_check: dict[str, Any] | None) -> dict[str, str]:
    boundaries = dict(_dict(manifest.get("non_claim_boundaries")))
    boundaries.update(
        {
            "structure_verification": "machine_checked" if manifest_check else "operator_manifest_check_required",
            "runtime_verification": "artifact_refs_checked" if manifest_check and manifest_check.get("check_status") == "passed" else "not_ready",
            "human_acceptance": boundaries.get("human_acceptance", "not_claimed"),
            "business_validation": boundaries.get("business_validation", "not_claimed"),
            "durable_memory": "not_written",
            "company_kb_write": "not_written",
        }
    )
    return boundaries


def _non_claims() -> list[str]:
    return [
        "not next-pass execution",
        "not human acceptance",
        "not business validation",
        "not durable memory",
        "not Company KB promotion",
        "not provider success",
    ]


def _artifact_table(value: Any) -> str:
    refs = _list(value)
    if not refs:
        return "- none"
    return "\n".join(f"- {ref.get('path', 'unknown')}: {ref.get('artifact_type', 'unknown')}" for ref in refs)


def _blocked_table(value: Any) -> str:
    items = _list(value)
    if not items:
        return "- none"
    return "\n".join(f"- {item.get('ref', 'unknown')}: {item.get('reason', 'blocked')}" for item in items)


def _action(action: str, status: str, detail: str) -> dict[str, str]:
    return {"action": action, "status": status, "detail": detail}


def _control(control_id: str, passed: bool) -> dict[str, str]:
    return {"control_id": control_id, "status": PASSED if passed else FAILED}


def _started_label(value: Any) -> str:
    return "started" if value is True else "not started"


def _enabled_label(value: Any) -> str:
    return "enabled" if value is True else "disabled"


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


__all__ = (
    "OPERATOR_HANDOFF_PACKET_KIND",
    "build_operator_handoff_packet",
    "render_operator_handoff_packet_markdown",
    "write_operator_handoff_packet",
)
