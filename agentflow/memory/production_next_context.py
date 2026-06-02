from __future__ import annotations

from pathlib import Path
from typing import Any

from agentflow.harness.constants import FAILED, PASSED
from agentflow.memory.production_loop import SCHEMA_VERSION
from agentflow_studio.utils import write_json

NEXT_CONTEXT_HANDOFF_KIND = "agentflow_production_memory_next_context_handoff"


def build_next_context_handoff(run: dict[str, Any], *, generated_at: str) -> dict[str, Any]:
    """Build a no-provider handoff for the next AI task from an assembled context bundle."""
    if not isinstance(generated_at, str) or not generated_at.strip():
        raise ValueError("generated_at is required")
    context = _dict(run.get("context_bundle"))
    readiness = _dict(run.get("pass_readiness"))
    next_pass = _dict(run.get("next_pass_bundle"))
    included_refs = list(context.get("included_refs", []))
    blocked_refs = list(context.get("blocked_refs", []))
    ready = readiness.get("ready") is True and next_pass.get("execution_status") == "planned"
    return {
        "kind": NEXT_CONTEXT_HANDOFF_KIND,
        "artifact_type": NEXT_CONTEXT_HANDOFF_KIND,
        "schema_version": run.get("schema_version", SCHEMA_VERSION),
        "handoff_id": f"next-context:{run.get('loop_id', 'production-memory-loop')}",
        "generated_at": generated_at,
        "handoff_status": "ready" if ready else "blocked",
        "project_id": run.get("project_id", context.get("project_id", "unknown")),
        "loop_id": run.get("loop_id", "unknown"),
        "task_id": next_pass.get("task_id", "next-pass:unassigned"),
        "context_bundle_id": context.get("bundle_id", "unknown"),
        "provider_mode": "no-provider",
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "next_context_refs": included_refs,
        "blocked_refs": blocked_refs,
        "task_prompt": _task_prompt(next_pass, included_refs, blocked_refs, ready),
        "controls": _controls(run, readiness, included_refs, blocked_refs),
        "non_claims": [
            "not human acceptance",
            "not business validation",
            "not durable Memory OS",
            "not provider success",
            "not Company KB promotion",
        ],
        "claim_boundaries": next_pass.get("claim_boundaries", {}),
    }


def write_next_context_handoff(handoff: dict[str, Any], output_dir: str | Path) -> list[Path]:
    output_root = Path(output_dir)
    json_path = write_json(output_root / "next_context_handoff.json", handoff)
    md_path = output_root / "next_context_handoff.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_next_context_handoff_markdown(handoff), encoding="utf-8")
    return [json_path, md_path]


def render_next_context_handoff_markdown(handoff: dict[str, Any]) -> str:
    included = _refs_table(handoff.get("next_context_refs"))
    blocked = _refs_table(handoff.get("blocked_refs"), reason=True)
    return "\n".join(
        [
            "# Next Context Handoff",
            "",
            f"Status: {handoff.get('handoff_status', 'unknown')}",
            f"Project: {handoff.get('project_id', 'unknown')}",
            f"Task: {handoff.get('task_id', 'unknown')}",
            "",
            "No-provider: true",
            "Provider calls: not started",
            "Durable memory write: disabled",
            "Company KB write: disabled",
            "",
            "## Task Prompt",
            "",
            str(handoff.get("task_prompt", "")),
            "",
            "## Included refs",
            "",
            included,
            "",
            "## Blocked refs",
            "",
            blocked,
            "",
            "## Non-claims",
            "",
            "\n".join(f"- {item}" for item in _list(handoff.get("non_claims"))),
            "",
        ]
    )


def _task_prompt(
    next_pass: dict[str, Any],
    included_refs: list[dict[str, Any]],
    blocked_refs: list[dict[str, Any]],
    ready: bool,
) -> str:
    instruction = str(next_pass.get("operator_instruction", "Prepare the next production pass."))
    if not ready:
        return f"Resolve blockers before preparing the next AI task. {instruction}"
    return (
        "Use only the listed next_context_refs for the next AI task. "
        "Do not use blocked_refs, feedback events as memory, or unpromoted candidates. "
        f"{instruction}"
    )


def _controls(
    run: dict[str, Any],
    readiness: dict[str, Any],
    included_refs: list[dict[str, Any]],
    blocked_refs: list[dict[str, Any]],
) -> list[dict[str, str]]:
    included_ids = {str(ref.get("ref_id")) for ref in included_refs}
    blocked_ids = {str(ref.get("ref_id")) for ref in blocked_refs}
    return [
        _control("pass_readiness_ready", readiness.get("ready") is True),
        _control("next_context_refs_present", bool(included_refs)),
        _control("blocked_refs_excluded", not (included_ids & blocked_ids)),
        _control("provider_calls_not_started", run.get("provider_calls_started") is False),
        _control("long_term_memory_write_disabled", run.get("writes_long_term_memory") is False),
        _control("company_kb_write_disabled", True),
    ]


def _refs_table(value: Any, *, reason: bool = False) -> str:
    refs = _list(value)
    if not refs:
        return "- none"
    lines = []
    for ref in refs:
        ref_id = ref.get("ref_id", "unknown")
        if reason:
            lines.append(f"- {ref_id}: {ref.get('reason', ref.get('status', 'blocked'))}")
        else:
            lines.append(f"- {ref_id}: {ref.get('summary', ref.get('title', 'included'))}")
    return "\n".join(lines)


def _control(control_id: str, passed: bool) -> dict[str, str]:
    return {"control_id": control_id, "status": PASSED if passed else FAILED}


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


__all__ = (
    "NEXT_CONTEXT_HANDOFF_KIND",
    "build_next_context_handoff",
    "render_next_context_handoff_markdown",
    "write_next_context_handoff",
)
