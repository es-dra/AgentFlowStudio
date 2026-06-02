from __future__ import annotations

from typing import Any


def readiness_markdown(readiness: dict[str, Any]) -> str:
    blocked_lines = "\n".join(
        f"- {item.get('ref_id', 'unknown')}: {item.get('reason', 'blocked')}"
        for item in _list(readiness.get("blocked_refs"))
    )
    return "\n".join(
        [
            "# Production Memory Asset Profile Readiness",
            "",
            f"Status: {readiness.get('readiness_status', 'unknown')}",
            f"Project: {readiness.get('project_id', 'unknown')}",
            f"Profiles: {readiness.get('ready_profile_count', 0)}/{readiness.get('profile_count', 0)} ready for tester review",
            "",
            "## Controls",
            "",
            "\n".join(f"- {item['control_id']}: {item['status']}" for item in _list(readiness.get("controls"))),
            "",
            "## Blocked Refs",
            "",
            blocked_lines or "- none",
            "",
        ]
    )


def package_markdown(package: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Production Memory Asset Test Package",
            "",
            f"Status: {package.get('package_status', 'unknown')}",
            f"Project: {package.get('project_id', 'unknown')}",
            "",
            "## Tester Outputs",
            "",
            "\n".join(f"- {item}" for item in _list(package.get("tester_outputs"))),
            "",
            "## Non-claims",
            "",
            "\n".join(f"- {item}" for item in _list(package.get("non_claims"))),
            "",
        ]
    )


def rubric_markdown() -> str:
    return "\n".join(
        [
            "# Asset Consistency Rubric",
            "",
            "| Area | Pass | Partial | Fail | Unknown |",
            "|---|---|---|---|---|",
            "| Character identity | Key identity anchors preserved | Some anchors preserved | Identity drifted | Cannot judge |",
            "| Character constraints | No negative constraint violated | Minor ambiguity | Constraint violated | Cannot judge |",
            "| Scene continuity | Spatial anchors preserved | Some anchors preserved | Scene anchors drifted | Cannot judge |",
            "| Allowed variation | Variation stays within profile | Borderline | Variation breaks profile | Cannot judge |",
            "",
            "Machine readiness is not human acceptance. Tester review is required.",
            "",
        ]
    )


def tester_feedback_template() -> str:
    return "\n".join(
        [
            "# Tester Feedback Template",
            "",
            "Project:",
            "Reviewer:",
            "Review time:",
            "",
            "## Character Profile",
            "",
            "- Kept: ",
            "- Drifted: ",
            "- Violated constraints: ",
            "- Decision: kept / partially kept / not kept / cannot judge",
            "",
            "## Scene Profile",
            "",
            "- Kept: ",
            "- Drifted: ",
            "- Violated constraints: ",
            "- Decision: kept / partially kept / not kept / cannot judge",
            "",
            "## Suggested Next State",
            "",
            "- candidate / promoted / blocked / retired:",
            "- Rationale:",
            "",
        ]
    )


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


__all__ = (
    "package_markdown",
    "readiness_markdown",
    "rubric_markdown",
    "tester_feedback_template",
)
