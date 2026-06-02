from __future__ import annotations

from pathlib import Path
from typing import Any

from agentflow_studio.utils import write_json


def write_next_operator_start_event_report(event: dict[str, Any], output_dir: str | Path) -> list[Path]:
    output_root = Path(output_dir)
    json_path = write_json(output_root / "next_operator_start_event.json", event)
    markdown_path = output_root / "next_operator_start_event.md"
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(render_next_operator_start_event_markdown(event), encoding="utf-8")
    return [json_path, markdown_path]


def render_next_operator_start_event_markdown(event: dict[str, Any]) -> str:
    boundaries = _dict(event.get("claim_boundaries"))
    return "\n".join(
        [
            "# Production Memory Next Operator Start Event",
            "",
            f"Status: {event.get('event_status', 'unknown')}",
            f"Decision: {event.get('start_decision', 'unknown')}",
            f"Project: {event.get('source_project_id', 'unknown')}",
            f"Operator loop: {event.get('source_operator_loop_id', 'unknown')}",
            f"Source start packet: {event.get('source_start_packet_status', 'unknown')}",
            f"Ready for next operator: {_bool_label(event.get('source_ready_for_next_operator'))}",
            f"Next operator action: {event.get('source_next_operator_action', 'unknown')}",
            "",
            "Provider calls: not started",
            "Writes long-term memory: false",
            "Writes Company KB: false",
            f"Human acceptance: {boundaries.get('human_acceptance', 'not_claimed')}",
            f"Next-pass execution: {boundaries.get('next_pass_execution', 'not_claimed')}",
            "",
            "## Summary",
            str(event.get("summary", "")),
            "",
            "## Operator Prompt Excerpt",
            str(event.get("operator_prompt_excerpt", "")),
            "",
            "## Start Requirements",
            "\n".join(f"- {item}" for item in _list(event.get("start_requirements"))) or "- none",
            "",
            "## Non-claims",
            "\n".join(f"- {item}" for item in _list(event.get("non_claims"))) or "- none",
            "",
        ]
    )


def _bool_label(value: Any) -> str:
    return "true" if value is True else "false"


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


__all__ = (
    "render_next_operator_start_event_markdown",
    "write_next_operator_start_event_report",
)
