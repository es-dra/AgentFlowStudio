from __future__ import annotations

from typing import Any

from agentflow.memory.production_operator_acceptance_feedback_candidate_handoff import (
    acceptance_feedback_candidate_promotion_markdown,
)


def render_operator_run_package_markdown(package: dict[str, Any]) -> str:
    action = _dict(package.get("next_operator_action"))
    return "\n".join(
        [
            "# Production Memory Operator Run Package",
            "",
            f"Status: {package.get('package_status', 'unknown')}",
            f"Project: {package.get('project_id', 'unknown')}",
            f"Operator loop: {package.get('source_operator_loop_id', 'unknown')}",
            f"Manifest check: {package.get('manifest_check_status', 'unknown')}",
            f"Operator handoff: {package.get('handoff_status', 'unknown')}",
            f"Next operator action: {action.get('action', 'unknown')}",
            "",
            f"Provider calls: {_started_label(package.get('provider_calls_started'))}",
            f"Durable memory write: {_enabled_label(package.get('writes_long_term_memory'))}",
            f"Company KB write: {_enabled_label(package.get('writes_company_kb'))}",
            "",
            "## Package Items",
            "",
            _package_items_table(package.get("package_items")),
            "",
            acceptance_feedback_candidate_promotion_markdown(
                package.get("acceptance_feedback_candidate_promotion")
            ),
            "",
            "## Blocked Items",
            "",
            _blocked_items_table(package.get("blocked_items")),
            "",
            "## Non-claims",
            "",
            "\n".join(f"- {item}" for item in _list(package.get("non_claims"))),
            "",
        ]
    )


def _package_items_table(value: Any) -> str:
    items = _list(value)
    if not items:
        return "- none"
    return "\n".join(f"- {item.get('path', 'unknown')}: {item.get('artifact_type', 'unknown')}" for item in items)


def _blocked_items_table(value: Any) -> str:
    items = _list(value)
    if not items:
        return "- none"
    return "\n".join(f"- {item.get('ref', 'unknown')}: {item.get('reason', 'blocked')}" for item in items)


def _started_label(value: Any) -> str:
    return "started" if value is True else "not started"


def _enabled_label(value: Any) -> str:
    return "enabled" if value is True else "disabled"


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []
