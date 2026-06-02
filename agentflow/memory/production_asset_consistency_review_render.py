from __future__ import annotations

from typing import Any

from agentflow.memory.production_asset_profile_promotion_utils import list_value


def render_asset_consistency_review_markdown(review: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Production Memory Asset Consistency Review",
            "",
            f"Status: {review.get('review_status', 'unknown')}",
            f"Overall result: {review.get('overall_consistency_result', 'unknown')}",
            f"Comparison scope: {review.get('comparison_scope', 'unknown')}",
            f"Findings: {len(list_value(review.get('consistency_findings')))}",
            f"Blocked findings: {len(list_value(review.get('blocked_findings')))}",
            "Provider calls: not started",
            "Creates asset feedback: false",
            "Creates profile update candidate: false",
            "Creates promotion decision: false",
            "Writes long-term memory: false",
            "Writes Company KB: false",
            "",
            "## Consistency Findings",
            "",
            _findings_table(review.get("consistency_findings")),
            "",
            "## Blocked Findings",
            "",
            _blocked_table(review.get("blocked_findings")),
            "",
        ]
    )


def _findings_table(value: Any) -> str:
    findings = list_value(value)
    if not findings:
        return "- none"
    return "\n".join(
        f"- {item.get('profile_ref', 'unknown')}: {item.get('review_dimension', 'unknown')} -> {item.get('review_result', 'unknown')}"
        for item in findings
    )


def _blocked_table(value: Any) -> str:
    findings = list_value(value)
    if not findings:
        return "- none"
    return "\n".join(f"- {item.get('profile_ref', 'unknown')}: {item.get('reason', 'blocked')}" for item in findings)


__all__ = ("render_asset_consistency_review_markdown",)
