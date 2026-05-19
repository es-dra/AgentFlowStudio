from __future__ import annotations

from typing import Any


def selection_diagnostic_lines(diagnostics: dict[str, Any] | None) -> list[str]:
    if not diagnostics:
        return ["- No selection diagnostics available."]
    return [
        f"- Candidates: {diagnostics.get('candidate_count', 0)} total, {diagnostics.get('selected_count', 0)} selected",
        f"- Selected score range: {_score_range(diagnostics.get('selected_score_range'))}",
        f"- Best rejected gap to selected floor: {_score_gap(diagnostics)}",
        f"- Rejection reasons: {_counts(diagnostics.get('rejection_reason_counts'))}",
        f"- Boundary strategies: {_counts(diagnostics.get('boundary_strategy_counts'))}",
        f"- Selected positions: {_counts(diagnostics.get('selected_position_counts'))}",
        f"- Top near miss: {_top_near_miss(diagnostics)}",
        f"- Warnings: {_diagnostic_warnings(diagnostics)}",
    ]


def _score_range(value: object) -> str:
    if not isinstance(value, dict):
        return "missing"
    low = _float(value.get("min"))
    high = _float(value.get("max"))
    if low is None or high is None:
        return "missing"
    return f"{low:.3f} - {high:.3f}"


def _score_gap(diagnostics: dict[str, Any]) -> str:
    gaps = diagnostics.get("score_gaps")
    if not isinstance(gaps, dict):
        return "missing"
    gap = _float(gaps.get("best_rejected_gap_to_selected_floor"))
    return f"{gap:.3f}" if gap is not None else "missing"


def _counts(value: object) -> str:
    if not isinstance(value, dict) or not value:
        return "none"
    return ", ".join(f"{key}={value[key]}" for key in sorted(value))


def _top_near_miss(diagnostics: dict[str, Any]) -> str:
    near_misses = diagnostics.get("near_misses")
    if not isinstance(near_misses, list) or not near_misses:
        return "none"
    top = near_misses[0]
    if not isinstance(top, dict):
        return "none"
    candidate_id = str(top.get("candidate_id") or "unknown")
    score = _float(top.get("selection_score"))
    reasons = top.get("rejection_reasons")
    reason_text = ", ".join(str(item) for item in reasons) if isinstance(reasons, list) and reasons else "unknown"
    return f"`{candidate_id}` score {score:.3f} ({reason_text})" if score is not None else f"`{candidate_id}` ({reason_text})"


def _diagnostic_warnings(diagnostics: dict[str, Any]) -> str:
    warnings = diagnostics.get("warnings")
    if not isinstance(warnings, list) or not warnings:
        return "none"
    codes = [str(item.get("code")) for item in warnings if isinstance(item, dict) and item.get("code")]
    return ", ".join(codes) if codes else "none"


def _float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
