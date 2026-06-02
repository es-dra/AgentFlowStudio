from __future__ import annotations

from pathlib import Path
from typing import Any

from agentflow_studio.utils import write_json


def write_next_operator_start_packet_report(packet: dict[str, Any], output_dir: str | Path) -> list[Path]:
    output_root = Path(output_dir)
    json_path = write_json(output_root / "next_operator_start_packet.json", packet)
    markdown_path = output_root / "next_operator_start_packet.md"
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(render_next_operator_start_packet_markdown(packet), encoding="utf-8")
    return [json_path, markdown_path]


def render_next_operator_start_packet_markdown(packet: dict[str, Any]) -> str:
    action = _dict(packet.get("next_operator_action"))
    return "\n".join(
        [
            "# Production Memory Next Operator Start Packet",
            "",
            f"Status: {packet.get('start_packet_status', 'unknown')}",
            f"Project: {packet.get('project_id', 'unknown')}",
            f"Operator loop: {packet.get('source_operator_loop_id', 'unknown')}",
            f"Package check: {packet.get('package_check_status', 'unknown')}",
            f"Package status: {packet.get('package_status', 'unknown')}",
            f"Handoff status: {packet.get('handoff_status', 'unknown')}",
            f"Next operator action: {action.get('action', 'unknown')}",
            "",
            f"Provider calls: {_started_label(packet.get('provider_calls_started'))}",
            f"Durable memory write: {_enabled_label(packet.get('writes_long_term_memory'))}",
            f"Company KB write: {_enabled_label(packet.get('writes_company_kb'))}",
            "",
            "## Operator Prompt",
            "",
            str(packet.get("operator_prompt", "")),
            "",
            "## Checked Package Items",
            "",
            _checked_items_table(packet.get("checked_package_items")),
            "",
            "## Start Requirements",
            "",
            "\n".join(f"- {item}" for item in _list(packet.get("start_requirements"))),
            "",
            "## Non-claims",
            "",
            "\n".join(f"- {item}" for item in _list(packet.get("non_claims"))),
            "",
        ]
    )


def _checked_items_table(value: Any) -> str:
    items = _list(value)
    if not items:
        return "- none"
    return "\n".join(
        f"- {item.get('path', 'unknown')}: {item.get('artifact_type', 'unknown')} ({item.get('role', 'unknown')})"
        for item in items
    )


def _started_label(value: Any) -> str:
    return "started" if value is True else "not started"


def _enabled_label(value: Any) -> str:
    return "enabled" if value is True else "disabled"


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


__all__ = (
    "render_next_operator_start_packet_markdown",
    "write_next_operator_start_packet_report",
)
