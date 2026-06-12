from __future__ import annotations

from typing import Any

from apps.api.runtime_attribute_vocabulary import find_lock_conflicts


TOTAL_PROMPT_BUDGET = 1500
SEGMENT_SEPARATOR_RESERVE = 8
VISIBLE_PROMPT_FLOOR = 550
LOCK_IDENTITY_FLOOR = 400
SEGMENT_CAPS = {
    "scene_director": 250,
    "upstream_summary": 150,
    "preference": 100,
}
TRUNCATION_ORDER = [
    "preference",
    "upstream_summary",
    "scene_director",
    "visible_prompt_above_floor",
    "lock_identity_never",
]


def apply_context_budget(mode: str, text: dict[str, str]) -> tuple[dict[str, str], dict[str, Any]]:
    """Enforce the provider prompt character budget on a text channel.

    generate mode waterfall:
      1. lock/identity segment is never truncated;
      2. visible prompt keeps at least VISIBLE_PROMPT_FLOOR characters and
         may use any room left by the identity segment;
      3. scene/director, upstream summary, and preference each consume the
         smaller of their cap and the remaining budget, in that order.

    optimize mode is report-only: the visible prompt there is a human-facing
    document, not a provider payload, so nothing is truncated.
    """
    raw = {
        "visible_prompt": str(text.get("visible_prompt") or ""),
        "lock_identity": str(text.get("asset_identity_segment") or ""),
        "scene_director": str(text.get("scene_director_segment") or ""),
        "upstream_summary": str(text.get("upstream_summary_segment") or ""),
        "preference": str(text.get("preference_segment") or ""),
    }
    if mode != "generate":
        report = _report(mode, raw, raw, enforcement_applied=False)
        return dict(text), report

    final: dict[str, str] = {}
    identity = raw["lock_identity"]
    final["lock_identity"] = identity

    effective_total = TOTAL_PROMPT_BUDGET - SEGMENT_SEPARATOR_RESERVE
    visible_allow = max(VISIBLE_PROMPT_FLOOR, effective_total - len(identity))
    final["visible_prompt"] = _truncate(raw["visible_prompt"], visible_allow)

    remaining = effective_total - len(identity) - len(final["visible_prompt"])
    remaining = max(0, remaining)
    for name in ("scene_director", "upstream_summary", "preference"):
        allow = min(SEGMENT_CAPS[name], remaining)
        final[name] = _truncate(raw[name], allow)
        remaining = max(0, remaining - len(final[name]))

    budgeted = dict(text)
    budgeted["visible_prompt"] = final["visible_prompt"]
    budgeted["asset_identity_segment"] = final["lock_identity"]
    budgeted["scene_director_segment"] = final["scene_director"]
    budgeted["upstream_summary_segment"] = final["upstream_summary"]
    budgeted["preference_segment"] = final["preference"]
    report = _report(mode, raw, final, enforcement_applied=True)
    return budgeted, report


def context_warnings(
    assets: dict[str, dict[str, Any]],
    refs: dict[str, dict[str, Any]],
    prompt: str,
    overrides: set[tuple[str, str]],
) -> list[dict[str, str]]:
    """Best-effort warnings: unconnected named assets and lexical lock conflicts.

    Detection feeds the UI only; lock enforcement happens by unconditional
    injection in the text channel and never depends on these warnings.
    """
    prompt_fold = prompt.casefold()
    warnings: list[dict[str, str]] = []
    for asset_id, asset in sorted(assets.items()):
        label = str(asset.get("label") or "")
        if label and label.casefold() in prompt_fold and asset_id not in refs:
            warnings.append({"warning_id": "named_asset_not_connected", "asset_id": asset_id, "label": label})
        for lock in asset.get("negative_locks", []):
            lock_text = str(lock)
            if (asset_id, lock_text) in overrides:
                continue
            for conflict in find_lock_conflicts(lock_text, prompt):
                warnings.append(
                    {
                        "warning_id": "best_effort_lock_conflict",
                        "asset_id": asset_id,
                        "lock_text": lock_text,
                        "attribute": conflict["attribute"],
                        "lock_value": conflict["lock_value"],
                        "prompt_value": conflict["prompt_value"],
                        "connected": "true" if asset_id in refs else "false",
                        "detection": "lexical_best_effort_low_recall",
                    }
                )
    return warnings


def duplicate_labels(assets: list[dict[str, Any]]) -> list[dict[str, str]]:
    seen: dict[tuple[str, str], str] = {}
    duplicates: list[dict[str, str]] = []
    for asset in assets:
        key = (str(asset.get("asset_type")), str(asset.get("label")).casefold())
        if key in seen:
            duplicates.append(
                {
                    "asset_type": key[0],
                    "label": str(asset.get("label")),
                    "first_asset_id": seen[key],
                    "asset_id": str(asset.get("asset_id")),
                }
            )
        else:
            seen[key] = str(asset.get("asset_id"))
    return duplicates


def _truncate(value: str, limit: int) -> str:
    if limit <= 0:
        return ""
    if len(value) <= limit:
        return value
    cut = value[:limit]
    space = cut.rfind(" ")
    if space >= limit - 30:
        cut = cut[:space]
    return cut.rstrip()


def _report(
    mode: str,
    raw: dict[str, str],
    final: dict[str, str],
    *,
    enforcement_applied: bool,
) -> dict[str, Any]:
    allocations = {
        "visible_prompt": VISIBLE_PROMPT_FLOOR,
        "lock_identity": LOCK_IDENTITY_FLOOR,
        **SEGMENT_CAPS,
    }
    segments = {
        name: {
            "allocated": allocations[name],
            "raw_length": len(raw[name]),
            "used": len(final[name]),
            "truncated": len(final[name]) < len(raw[name]),
        }
        for name in ("visible_prompt", "lock_identity", "scene_director", "upstream_summary", "preference")
    }
    total_used = sum(item["used"] for item in segments.values())
    return {
        "unit": "characters",
        "mode": mode,
        "enforcement_applied": enforcement_applied,
        "total_limit": TOTAL_PROMPT_BUDGET,
        "total_used": total_used,
        "overflow_beyond_total": total_used > TOTAL_PROMPT_BUDGET,
        "segments": segments,
        "visible_prompt_floor": VISIBLE_PROMPT_FLOOR,
        "lock_identity_never_truncate": True,
        "truncation_order": TRUNCATION_ORDER,
    }


__all__ = (
    "LOCK_IDENTITY_FLOOR",
    "SEGMENT_CAPS",
    "TOTAL_PROMPT_BUDGET",
    "TRUNCATION_ORDER",
    "VISIBLE_PROMPT_FLOOR",
    "apply_context_budget",
    "context_warnings",
    "duplicate_labels",
)
