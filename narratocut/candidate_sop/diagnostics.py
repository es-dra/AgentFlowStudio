from __future__ import annotations

from collections import Counter
from typing import Any


SELECTION_DIAGNOSTICS = "selection_diagnostics.json"
DIAGNOSTICS_SOURCE = "phase14_5_selection_diagnostics"
NEAR_MISS_SCORE_MARGIN = 0.05
LOW_SELECTED_SCORE = 0.25
EXPECTED_PRUNING_REASONS = {"overlap", "duplicate_source_window"}


def build_selection_diagnostics(score_report: dict[str, Any]) -> dict[str, Any]:
    candidates = [item for item in score_report.get("candidates", []) if isinstance(item, dict)]
    selected = [item for item in candidates if item.get("decision") == "selected"]
    rejected = [item for item in candidates if item.get("decision") == "rejected"]
    selected_scores = [_score(item) for item in selected]
    selected_scores = [score for score in selected_scores if score is not None]
    selected_floor = min(selected_scores) if selected_scores else None
    best_rejected = _best_rejected_score(rejected)
    near_misses = _near_misses(rejected, selected_floor)
    actionable_near_misses = _actionable_near_misses(near_misses)
    rejection_reason_counts = _rejection_reason_counts(rejected)
    selected_position_counts = _position_counts(selected, candidates)
    warnings = _warnings(
        selected=selected,
        selected_scores=selected_scores,
        selected_position_counts=selected_position_counts,
        near_misses=actionable_near_misses,
        rejection_reason_counts=rejection_reason_counts,
    )

    return {
        "schema_version": "0.1",
        "status": "succeeded",
        "source": DIAGNOSTICS_SOURCE,
        "candidate_count": len(candidates),
        "selected_count": len(selected),
        "rejected_count": len(rejected),
        "selected_candidates": [_candidate_summary(item) for item in selected],
        "top_rejected_candidates": [_candidate_summary(item) for item in sorted(rejected, key=_sort_key)[:5]],
        "near_misses": near_misses,
        "selected_score_range": _score_range(selected_scores),
        "score_gaps": {
            "selected_floor": _rounded(selected_floor),
            "best_rejected_score": _rounded(best_rejected),
            "best_rejected_gap_to_selected_floor": _rounded(
                selected_floor - best_rejected if selected_floor is not None and best_rejected is not None else None
            ),
        },
        "rejection_reason_counts": dict(sorted(rejection_reason_counts.items())),
        "boundary_strategy_counts": dict(sorted(_boundary_strategy_counts(candidates).items())),
        "source_position_counts": dict(sorted(_position_counts(candidates, candidates).items())),
        "selected_position_counts": dict(sorted(selected_position_counts.items())),
        "warnings": warnings,
        "errors": [],
        "manifest_path": SELECTION_DIAGNOSTICS,
    }


def _near_misses(rejected: list[dict[str, Any]], selected_floor: float | None) -> list[dict[str, Any]]:
    if selected_floor is None:
        return []
    near = [
        item
        for item in rejected
        if (_score(item) is not None and _score(item) >= selected_floor - NEAR_MISS_SCORE_MARGIN)
    ]
    return [_candidate_summary(item) for item in sorted(near, key=_sort_key)[:5]]


def _actionable_near_misses(near_misses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in near_misses if not _is_expected_pruning(item)]


def _is_expected_pruning(candidate: dict[str, Any]) -> bool:
    reasons = set(_list_text(candidate.get("rejection_reasons")))
    return bool(reasons) and reasons <= EXPECTED_PRUNING_REASONS


def _warnings(
    *,
    selected: list[dict[str, Any]],
    selected_scores: list[float],
    selected_position_counts: Counter[str],
    near_misses: list[dict[str, Any]],
    rejection_reason_counts: Counter[str],
) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    if selected_scores and min(selected_scores) < LOW_SELECTED_SCORE:
        warnings.append(
            {
                "code": "low_selected_score",
                "message": "At least one selected candidate has a low selection score.",
                "details": {"selected_score_floor": _rounded(min(selected_scores))},
            }
        )
    if near_misses:
        warnings.append(
            {
                "code": "near_miss_rejected",
                "message": "One or more rejected candidates were close to the selected score floor.",
                "details": {"near_miss_count": len(near_misses)},
            }
        )
    selection_limit_near_misses = [
        item for item in near_misses if "selection_limit" in _list_text(item.get("rejection_reasons"))
    ]
    if selection_limit_near_misses and rejection_reason_counts.get("selection_limit", 0) > max(len(selected), 1):
        warnings.append(
            {
                "code": "too_many_selection_limit_rejections",
                "message": "Many candidates were rejected only because the selection limit was reached.",
                "details": {
                    "selection_limit_rejections": rejection_reason_counts["selection_limit"],
                    "near_miss_selection_limit_rejections": len(selection_limit_near_misses),
                },
            }
        )
    if selected and selected_position_counts and max(selected_position_counts.values()) == len(selected):
        warnings.append(
            {
                "code": "selection_clustered",
                "message": "All selected candidates come from the same broad source-time band.",
                "details": {"selected_position_counts": dict(sorted(selected_position_counts.items()))},
            }
        )
    if selected and not any(_has_strong_hook(item) for item in selected):
        warnings.append(
            {
                "code": "few_strong_hooks",
                "message": "No selected candidate has strong hook evidence.",
                "details": {"selected_count": len(selected)},
            }
        )
    return warnings


def _candidate_summary(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": str(candidate.get("candidate_id") or ""),
        "decision": str(candidate.get("decision") or "unknown"),
        "selection_score": _rounded(_score(candidate)),
        "total_score": _rounded(_total_score(candidate)),
        "start_sec": _rounded(_optional_float(candidate.get("start_sec"))),
        "end_sec": _rounded(_optional_float(candidate.get("end_sec"))),
        "duration_sec": _rounded(_optional_float(candidate.get("duration_sec"))),
        "reasons": _list_text(candidate.get("reasons")),
        "rejection_reasons": _list_text(candidate.get("rejection_reasons")),
        "boundary_strategy": _boundary_strategy(candidate),
    }


def _score_range(scores: list[float]) -> dict[str, float] | None:
    if not scores:
        return None
    return {"min": _rounded(min(scores)), "max": _rounded(max(scores))}


def _best_rejected_score(rejected: list[dict[str, Any]]) -> float | None:
    scores = [_score(item) for item in rejected]
    scores = [score for score in scores if score is not None]
    return max(scores) if scores else None


def _rejection_reason_counts(rejected: list[dict[str, Any]]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for item in rejected:
        reasons = _list_text(item.get("rejection_reasons"))
        if reasons:
            counter.update(reasons)
        else:
            counter.update(["unknown"])
    return counter


def _boundary_strategy_counts(candidates: list[dict[str, Any]]) -> Counter[str]:
    return Counter(_boundary_strategy(item) for item in candidates)


def _position_counts(items: list[dict[str, Any]], all_candidates: list[dict[str, Any]]) -> Counter[str]:
    end_times = [_optional_float(item.get("end_sec")) for item in all_candidates]
    duration = max([end for end in end_times if end is not None], default=0.0)
    counter: Counter[str] = Counter()
    for item in items:
        counter[_position_bucket(_optional_float(item.get("start_sec")), duration)] += 1
    return counter


def _position_bucket(start_sec: float | None, duration: float) -> str:
    if start_sec is None or duration <= 0:
        return "unknown"
    ratio = start_sec / duration
    if ratio < 1 / 3:
        return "early"
    if ratio < 2 / 3:
        return "middle"
    return "late"


def _boundary_strategy(candidate: dict[str, Any]) -> str:
    evidence = _source_evidence(candidate)
    if evidence and evidence.get("boundary_strategy"):
        return str(evidence["boundary_strategy"])
    if isinstance(candidate.get("source_candidate"), dict):
        return "native_transcript_window"
    return "unknown"


def _has_strong_hook(candidate: dict[str, Any]) -> bool:
    if "strong_hook" in _list_text(candidate.get("reasons")) or "ocr_hook" in _list_text(candidate.get("reasons")):
        return True
    breakdown = candidate.get("score_breakdown")
    if not isinstance(breakdown, dict):
        return False
    hook = _optional_float(breakdown.get("hook_strength")) or 0.0
    on_screen = _optional_float(breakdown.get("on_screen_hook_strength")) or 0.0
    return max(hook, on_screen) >= 0.5


def _source_evidence(candidate: dict[str, Any]) -> dict[str, Any] | None:
    source_candidate = candidate.get("source_candidate")
    evidence = source_candidate.get("evidence") if isinstance(source_candidate, dict) else None
    return evidence if isinstance(evidence, dict) else None


def _sort_key(candidate: dict[str, Any]) -> tuple[float, float, str]:
    return (-(_score(candidate) or 0.0), _optional_float(candidate.get("start_sec")) or 0.0, str(candidate.get("candidate_id") or ""))


def _score(candidate: dict[str, Any]) -> float | None:
    return _optional_float(candidate.get("selection_score") if candidate.get("selection_score") is not None else candidate.get("total_score"))


def _total_score(candidate: dict[str, Any]) -> float | None:
    return _optional_float(candidate.get("total_score"))


def _list_text(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def _rounded(value: float | None) -> float | None:
    return round(value, 6) if value is not None else None


def _optional_float(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
