from __future__ import annotations

from pathlib import Path
from typing import Any

from agentflow_studio.utils import write_json


def render_next_operator_action_result_markdown(result: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Next Operator Action Result",
            "",
            f"Status: {result.get('result_status', 'unknown')}",
            f"Decision: {result.get('action_decision', 'unknown')}",
            f"Source start event: {result.get('source_start_event_id', 'unknown')}",
            f"Recorded action: {result.get('source_next_operator_action', 'unknown')}",
            f"Summary: {result.get('summary', '')}",
            "",
            "No-provider: true",
            "Provider calls: not started",
            "Durable memory write: disabled",
            "Company KB write: disabled",
            "",
            "## Result refs",
            "",
            _refs_table(result.get("result_refs")),
            "",
            "## Controls",
            "",
            _controls_table(result.get("controls")),
            "",
            "## Non-claims",
            "",
            "\n".join(f"- {item}" for item in _list(result.get("non_claims"))),
            "",
        ]
    )


def write_next_operator_action_result_report(result: dict[str, Any], output_dir: str | Path) -> list[Path]:
    output_root = Path(output_dir)
    json_path = write_json(output_root / "next_operator_action_result.json", result)
    md_path = output_root / "next_operator_action_result.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_next_operator_action_result_markdown(result), encoding="utf-8")
    return [json_path, md_path]


def _refs_table(value: Any) -> str:
    refs = _list(value)
    if not refs:
        return "- none"
    return "\n".join(f"- {ref}" for ref in refs)


def _controls_table(value: Any) -> str:
    controls = _list(value)
    if not controls:
        return "- none"
    return "\n".join(
        f"- {item.get('control_id', 'unknown')}: {item.get('status', 'unknown')}"
        for item in controls
        if isinstance(item, dict)
    )


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


__all__ = (
    "render_next_operator_action_result_markdown",
    "write_next_operator_action_result_report",
)
