from __future__ import annotations

from pathlib import Path
from typing import Any

from agentflow.harness.constants import FAILED, PASSED
from agentflow.memory.production_next_context import NEXT_CONTEXT_HANDOFF_KIND
from narratocut.utils import write_json

NEXT_TASK_PACKET_KIND = "agentflow_production_memory_next_task_packet"


def build_next_task_packet(handoff: dict[str, Any], *, generated_at: str) -> dict[str, Any]:
    """Build a no-provider task packet from a verified next-context handoff."""
    _validate_handoff(handoff)
    if not isinstance(generated_at, str) or not generated_at.strip():
        raise ValueError("generated_at is required")

    included_refs = _list(handoff.get("next_context_refs"))
    blocked_refs = _list(handoff.get("blocked_refs"))
    ready = _is_ready_handoff(handoff, included_refs, blocked_refs)
    allowed_refs = included_refs if ready else []
    effective_blocked_refs = blocked_refs if ready else _blocked_handoff_refs(handoff, blocked_refs)

    return {
        "kind": NEXT_TASK_PACKET_KIND,
        "artifact_type": NEXT_TASK_PACKET_KIND,
        "schema_version": handoff.get("schema_version", "production-memory-loop/v1"),
        "task_packet_id": f"next-task:{handoff.get('handoff_id', 'unknown')}",
        "generated_at": generated_at,
        "source_handoff_id": handoff.get("handoff_id", "unknown"),
        "handoff_status": handoff.get("handoff_status", "unknown"),
        "packet_status": "ready" if ready else "blocked",
        "project_id": handoff.get("project_id", "unknown"),
        "task_id": handoff.get("task_id", "next-pass:unassigned"),
        "provider_mode": "no-provider",
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "allowed_context_refs": allowed_refs,
        "blocked_refs": effective_blocked_refs,
        "blocked_ref_count": len(effective_blocked_refs),
        "task_prompt": handoff.get("task_prompt", ""),
        "task_instructions": _task_instructions(handoff, allowed_refs, effective_blocked_refs, ready),
        "controls": _controls(handoff, included_refs, blocked_refs, ready),
        "non_claims": _non_claims(handoff),
        "claim_boundaries": handoff.get("claim_boundaries", {}),
    }


def write_next_task_packet(packet: dict[str, Any], output_dir: str | Path) -> list[Path]:
    output_root = Path(output_dir)
    json_path = write_json(output_root / "next_task_packet.json", packet)
    md_path = output_root / "next_task_packet.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_next_task_packet_markdown(packet), encoding="utf-8")
    return [json_path, md_path]


def render_next_task_packet_markdown(packet: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Next Task Packet",
            "",
            f"Status: {packet.get('packet_status', 'unknown')}",
            f"Project: {packet.get('project_id', 'unknown')}",
            f"Task: {packet.get('task_id', 'unknown')}",
            f"Source handoff: {packet.get('source_handoff_id', 'unknown')}",
            "",
            "No-provider: true",
            "Provider calls: not started",
            "Durable memory write: disabled",
            "Company KB write: disabled",
            "",
            "## Task Instructions",
            "",
            str(packet.get("task_instructions", "")),
            "",
            "## Allowed context refs",
            "",
            _refs_table(packet.get("allowed_context_refs")),
            "",
            "## Blocked refs",
            "",
            _refs_table(packet.get("blocked_refs"), reason=True),
            "",
            "## Non-claims",
            "",
            "\n".join(f"- {item}" for item in _list(packet.get("non_claims"))),
            "",
        ]
    )


def _validate_handoff(handoff: dict[str, Any]) -> None:
    if not isinstance(handoff, dict):
        raise ValueError("next context handoff must be a JSON object")
    if handoff.get("kind") != NEXT_CONTEXT_HANDOFF_KIND:
        raise ValueError("next context handoff kind is required")


def _is_ready_handoff(
    handoff: dict[str, Any],
    included_refs: list[dict[str, Any]],
    blocked_refs: list[dict[str, Any]],
) -> bool:
    return (
        handoff.get("handoff_status") == "ready"
        and handoff.get("provider_mode") == "no-provider"
        and handoff.get("provider_calls_started") is False
        and handoff.get("writes_long_term_memory") is False
        and handoff.get("writes_company_kb") is False
        and bool(included_refs)
        and _blocked_refs_excluded(included_refs, blocked_refs)
    )


def _task_instructions(
    handoff: dict[str, Any],
    allowed_refs: list[dict[str, Any]],
    blocked_refs: list[dict[str, Any]],
    ready: bool,
) -> str:
    if not ready:
        return (
            "Resolve handoff blockers before the next AI task. "
            f"Do not use {len(blocked_refs)} blocked refs as context."
        )
    return (
        "Use only allowed_context_refs for the next AI task. "
        "Do not use blocked_refs, feedback is not memory, and memory candidate is not promoted memory. "
        f"Allowed refs: {len(allowed_refs)}. Blocked refs: {len(blocked_refs)}. "
        f"Prompt: {handoff.get('task_prompt', '')}"
    )


def _controls(
    handoff: dict[str, Any],
    included_refs: list[dict[str, Any]],
    blocked_refs: list[dict[str, Any]],
    ready: bool,
) -> list[dict[str, str]]:
    return [
        _control("handoff_ready", handoff.get("handoff_status") == "ready"),
        _control("next_context_refs_present", bool(included_refs)),
        _control("blocked_refs_excluded", _blocked_refs_excluded(included_refs, blocked_refs)),
        _control("no_provider_mode", handoff.get("provider_mode") == "no-provider"),
        _control("provider_calls_not_started", handoff.get("provider_calls_started") is False),
        _control("long_term_memory_write_disabled", handoff.get("writes_long_term_memory") is False),
        _control("company_kb_write_disabled", handoff.get("writes_company_kb") is False),
        _control("next_task_packet_ready", ready),
    ]


def _blocked_refs_excluded(included_refs: list[dict[str, Any]], blocked_refs: list[dict[str, Any]]) -> bool:
    included_ids = {str(ref.get("ref_id")) for ref in included_refs}
    blocked_ids = {str(ref.get("ref_id")) for ref in blocked_refs}
    return not (included_ids & blocked_ids)


def _blocked_handoff_refs(handoff: dict[str, Any], blocked_refs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        *blocked_refs,
        {
            "ref_id": "handoff:blocked",
            "status": handoff.get("handoff_status", "blocked"),
            "reason": "source handoff is not ready for next AI task context",
        },
    ]


def _non_claims(handoff: dict[str, Any]) -> list[str]:
    claims = list(_list(handoff.get("non_claims")))
    for claim in [
        "not next-pass execution",
        "not human acceptance",
        "not business validation",
        "not durable Memory OS",
        "not provider success",
        "not Company KB promotion",
    ]:
        if claim not in claims:
            claims.append(claim)
    return claims


def _refs_table(value: Any, *, reason: bool = False) -> str:
    refs = _list(value)
    if not refs:
        return "- none"
    lines = []
    for ref in refs:
        ref_id = ref.get("ref_id", "unknown")
        detail = ref.get("reason", ref.get("status", "blocked")) if reason else ref.get("summary", ref.get("title", "included"))
        lines.append(f"- {ref_id}: {detail}")
    return "\n".join(lines)


def _control(control_id: str, passed: bool) -> dict[str, str]:
    return {"control_id": control_id, "status": PASSED if passed else FAILED}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


__all__ = (
    "NEXT_TASK_PACKET_KIND",
    "build_next_task_packet",
    "render_next_task_packet_markdown",
    "write_next_task_packet",
)
