from __future__ import annotations

from pathlib import Path
from typing import Any


def write_operator_run_package_check_markdown(check: dict[str, Any], output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_operator_run_package_check_markdown(check), encoding="utf-8")
    return path


def render_operator_run_package_check_markdown(check: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Production Memory Operator Run Package Check",
            "",
            f"Status: {check.get('check_status', 'unknown')}",
            f"Ready for handoff: {_bool_label(check.get('ready_for_handoff'))}",
            f"Project: {check.get('project_id', 'unknown')}",
            f"Operator loop: {check.get('source_operator_loop_id', 'unknown')}",
            f"Package status: {check.get('package_status', 'unknown')}",
            f"Manifest check: {check.get('manifest_check_status', 'unknown')}",
            f"Operator handoff: {check.get('handoff_status', 'unknown')}",
            "",
            f"Checked items: {check.get('checked_item_count', 0)}",
            f"Missing refs: {len(_list(check.get('missing_refs')))}",
            f"Mismatched refs: {len(_list(check.get('mismatched_refs')))}",
            f"Unsafe refs: {len(_list(check.get('unsafe_refs')))}",
            f"Blocked items: {len(_list(check.get('blocked_items')))}",
            f"Failed controls: {len(_list(check.get('failed_controls')))}",
            "",
            f"Provider calls: {_started_label(check.get('provider_calls_started'))}",
            f"Durable memory write: {_enabled_label(check.get('writes_long_term_memory'))}",
            f"Company KB write: {_enabled_label(check.get('writes_company_kb'))}",
            "",
            "## Checked Items",
            "",
            _checked_items_table(check.get("checked_items")),
            "",
            "## Blockers",
            "",
            _blockers_table(check),
            "",
            "## Non-claims",
            "",
            "\n".join(f"- {item}" for item in _non_claims()),
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


def _blockers_table(check: dict[str, Any]) -> str:
    rows: list[str] = []
    rows.extend(f"- missing ref: {item}" for item in _list(check.get("missing_refs")))
    rows.extend(f"- unsafe ref: {item}" for item in _list(check.get("unsafe_refs")))
    rows.extend(
        f"- mismatched ref: {item.get('path', 'unknown')} expected {item.get('expected_artifact_type', 'unknown')}"
        f" got {item.get('actual_artifact_type', 'unknown')}"
        for item in _list(check.get("mismatched_refs"))
    )
    rows.extend(
        f"- blocked item: {item.get('ref', 'unknown')} - {item.get('reason', 'blocked')}"
        for item in _list(check.get("blocked_items"))
    )
    rows.extend(
        f"- failed control: {item.get('control_id', 'unknown')}"
        for item in _list(check.get("failed_controls"))
    )
    if not rows:
        return "- none"
    return "\n".join(rows)


def _non_claims() -> list[str]:
    return [
        "not human acceptance",
        "not business validation",
        "not durable memory",
        "not Company KB promotion",
        "not provider success",
    ]


def _bool_label(value: Any) -> str:
    return "true" if value is True else "false"


def _started_label(value: Any) -> str:
    return "started" if value is True else "not started"


def _enabled_label(value: Any) -> str:
    return "enabled" if value is True else "disabled"


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


__all__ = (
    "render_operator_run_package_check_markdown",
    "write_operator_run_package_check_markdown",
)
