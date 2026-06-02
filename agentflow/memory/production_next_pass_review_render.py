from __future__ import annotations

from typing import Any


def render_next_pass_review_markdown(review: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Next Pass Review",
            "",
            f"Status: {review.get('review_status', 'unknown')}",
            f"Source task packet: {review.get('source_task_packet_id', 'unknown')}",
            "",
            "No-provider: true",
            "Provider calls: not started",
            "Durable memory write: disabled",
            "Company KB write: disabled",
            "",
            "## Used allowed refs",
            "",
            _refs_table(review.get("used_allowed_refs")),
            "",
            "## Blocked or unknown refs",
            "",
            _refs_table(review.get("blocked_or_unknown_refs"), reason=True),
            "",
            "## Feedback candidates",
            "",
            _candidate_table(review.get("feedback_candidates")),
            "",
            "## Non-claims",
            "",
            "\n".join(f"- {item}" for item in _list(review.get("non_claims"))),
            "",
        ]
    )


def _refs_table(value: Any, *, reason: bool = False) -> str:
    refs = _list(value)
    if not refs:
        return "- none"
    lines = []
    for ref in refs:
        ref_obj = _dict(ref)
        detail = ref_obj.get("reason", "used") if reason else f"usage_count={ref_obj.get('usage_count', 0)}"
        lines.append(f"- {ref_obj.get('ref_id', 'unknown')}: {detail}")
    return "\n".join(lines)


def _candidate_table(value: Any) -> str:
    candidates = _list(value)
    if not candidates:
        return "- none"
    return "\n".join(
        f"- {_dict(candidate).get('candidate_id', 'unknown')}: pending explicit promotion decision"
        for candidate in candidates
    )


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


__all__ = ("render_next_pass_review_markdown",)
