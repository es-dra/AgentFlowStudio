from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentflow.harness.constants import AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS, FAILED, PASSED
from agentflow.memory.production_loop import SCHEMA_VERSION
from agentflow.memory.production_next_task import NEXT_TASK_PACKET_KIND
from narratocut.utils import write_json

NEXT_PASS_RESULT_KIND = "agentflow_production_memory_next_pass_result"


def build_next_pass_result_scaffold(
    next_task_packet: dict[str, Any],
    *,
    generated_at: str,
    result_id: str | None = None,
    output_ref: str = "next-pass:artifact:scaffold-001",
    title: str = "Next pass operator scaffold",
    summary: str = "No-provider scaffold for an operator-supplied next pass result.",
    used_context_refs: list[str] | None = None,
) -> dict[str, Any]:
    """Draft a no-provider next-pass result envelope from a ready task packet."""
    _validate_packet(next_task_packet)
    _validate_text("generated_at", generated_at)
    _validate_text("output_ref", output_ref)
    _validate_text("title", title)
    _validate_text("summary", summary)
    selected_refs = _selected_context_refs(next_task_packet, used_context_refs)
    controls = _controls(next_task_packet, selected_refs)
    result = {
        "kind": NEXT_PASS_RESULT_KIND,
        "artifact_type": NEXT_PASS_RESULT_KIND,
        "schema_version": next_task_packet.get("schema_version", SCHEMA_VERSION),
        "result_id": result_id or f"next-pass-result:{next_task_packet.get('task_packet_id', 'unknown')}",
        "generated_at": generated_at,
        "task_packet_id": next_task_packet.get("task_packet_id", "unknown"),
        "source_handoff_id": next_task_packet.get("source_handoff_id", "unknown"),
        "project_id": next_task_packet.get("project_id", "unknown"),
        "task_id": next_task_packet.get("task_id", "unknown"),
        "result_status": "scaffolded_for_operator_completion",
        "provider_mode": "no-provider",
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "output_artifacts": [
            {
                "ref_id": output_ref,
                "title": title,
                "status": "scaffolded",
                "summary": summary,
                "used_context_refs": selected_refs,
            }
        ],
        "feedback_events": [],
        "controls": controls,
        "non_claims": _non_claims(),
    }
    _reject_unsafe(result)
    return result


def write_next_pass_result_scaffold(result: dict[str, Any], output_dir: str | Path) -> list[Path]:
    output_root = Path(output_dir)
    json_path = write_json(output_root / "next_pass_result.json", result)
    md_path = output_root / "next_pass_result.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_next_pass_result_markdown(result), encoding="utf-8")
    return [json_path, md_path]


def render_next_pass_result_markdown(result: dict[str, Any]) -> str:
    artifact = _first_output(result)
    return "\n".join(
        [
            "# Next Pass Result Scaffold",
            "",
            f"Status: {result.get('result_status', 'unknown')}",
            f"Project: {result.get('project_id', 'unknown')}",
            f"Task: {result.get('task_id', 'unknown')}",
            f"Task packet: {result.get('task_packet_id', 'unknown')}",
            "",
            "No-provider: true",
            "Provider calls: not started",
            "Durable memory write: disabled",
            "Company KB write: disabled",
            "",
            "## Output artifact scaffold",
            "",
            f"- Ref: {artifact.get('ref_id', 'unknown')}",
            f"- Title: {artifact.get('title', 'unknown')}",
            f"- Status: {artifact.get('status', 'unknown')}",
            f"- Summary: {artifact.get('summary', '')}",
            "",
            "## Used context refs",
            "",
            _refs_table(artifact.get("used_context_refs")),
            "",
            "## Feedback events",
            "",
            "- none; feedback must be captured explicitly after operator review",
            "",
            "## Non-claims",
            "",
            "\n".join(f"- {item}" for item in _list(result.get("non_claims"))),
            "",
        ]
    )


def _validate_packet(packet: dict[str, Any]) -> None:
    if not isinstance(packet, dict):
        raise ValueError("next task packet must be a JSON object")
    if packet.get("kind") != NEXT_TASK_PACKET_KIND:
        raise ValueError(f"next task packet kind must be {NEXT_TASK_PACKET_KIND}")
    if packet.get("packet_status") != "ready":
        raise ValueError("next task packet must be ready")
    if packet.get("provider_mode") != "no-provider" or packet.get("provider_calls_started") is not False:
        raise ValueError("next task packet must be no-provider and must not have provider calls started")
    if packet.get("writes_long_term_memory") is not False or packet.get("writes_company_kb") is not False:
        raise ValueError("next task packet must not write memory or Company KB")


def _selected_context_refs(packet: dict[str, Any], requested_refs: list[str] | None) -> list[str]:
    allowed_refs = [str(ref.get("ref_id")) for ref in _list(packet.get("allowed_context_refs")) if isinstance(ref, dict)]
    if not allowed_refs:
        raise ValueError("next task packet has no allowed_context_refs")
    selected_refs = requested_refs if requested_refs is not None else allowed_refs
    selected_refs = [str(ref_id) for ref_id in selected_refs]
    if not selected_refs:
        raise ValueError("used_context_refs are required")
    unknown_refs = sorted(set(selected_refs) - set(allowed_refs))
    if unknown_refs:
        raise ValueError(f"used_context_refs must be allowed: {', '.join(unknown_refs)}")
    return selected_refs


def _controls(packet: dict[str, Any], selected_refs: list[str]) -> list[dict[str, str]]:
    allowed_ids = {str(ref.get("ref_id")) for ref in _list(packet.get("allowed_context_refs")) if isinstance(ref, dict)}
    return [
        _control("source_packet_ready", packet.get("packet_status") == "ready"),
        _control("allowed_context_refs_present", bool(allowed_ids)),
        _control("used_refs_allowed", bool(selected_refs) and set(selected_refs) <= allowed_ids),
        _control("result_no_provider_mode", True),
        _control("provider_calls_not_started", True),
        _control("long_term_memory_write_disabled", True),
        _control("company_kb_write_disabled", True),
        _control("feedback_not_auto_created", True),
    ]


def _non_claims() -> list[str]:
    return [
        "not next-pass execution",
        "not generated content",
        "not provider success",
        "not human acceptance",
        "not business validation",
        "not durable memory",
        "not durable Memory OS",
        "not Company KB promotion",
        "not feedback capture",
        "not memory promotion",
    ]


def _validate_text(label: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} is required")


def _reject_unsafe(value: Any) -> None:
    raw = json.dumps(value, ensure_ascii=False).lower()
    if any(fragment.lower() in raw for fragment in AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS):
        raise ValueError("production memory next pass result contains unsafe path, generated artifact path, or private credential material")


def _first_output(result: dict[str, Any]) -> dict[str, Any]:
    outputs = _list(result.get("output_artifacts"))
    return outputs[0] if outputs and isinstance(outputs[0], dict) else {}


def _refs_table(value: Any) -> str:
    refs = _list(value)
    if not refs:
        return "- none"
    return "\n".join(f"- {ref_id}" for ref_id in refs)


def _control(control_id: str, passed: bool) -> dict[str, str]:
    return {"control_id": control_id, "status": PASSED if passed else FAILED}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


__all__ = (
    "NEXT_PASS_RESULT_KIND",
    "build_next_pass_result_scaffold",
    "render_next_pass_result_markdown",
    "write_next_pass_result_scaffold",
)
