from __future__ import annotations

import re
from typing import Any


ALGORITHM_ID = "afs.quality_feedback_scoring.v0.1"
INPUT_CONTRACT = "raw Studio feedback payload and optional generated media refs"
OUTPUT_CONTRACT = "sanitized raw evidence event and bounded quality scores"
FAILURE_MODES = ("unknown_metric_dropped", "unsafe_text_redacted", "out_of_range_score_dropped")
EVIDENCE_BOUNDARY = "raw evidence is not durable memory and never stores provider raw response or media bytes"

QUALITY_FEEDBACK_METRICS = {
    "identity_similarity",
    "wardrobe_consistency",
    "scene_continuity",
    "text_or_watermark",
    "target_change_success",
}
FEEDBACK_TAXONOMY_CATEGORIES = (
    "character",
    "scene",
    "prop",
    "style",
    "shot",
    "narrative",
    "rhythm",
    "provider",
    "generation_failure",
    "asset",
    "artifact_quality",
    "revision",
    "general",
)
METRIC_FEEDBACK_TAXONOMY = {
    "identity_similarity": ("character",),
    "wardrobe_consistency": ("character", "style"),
    "scene_continuity": ("scene",),
    "text_or_watermark": ("artifact_quality",),
}
TEXT_FEEDBACK_TAXONOMY = {
    "character": ("character", "identity", "face", "wardrobe", "costume"),
    "scene": ("scene", "environment", "location", "continuity"),
    "prop": ("prop", "object", "item"),
    "style": ("style", "tone", "palette"),
    "shot": ("shot", "camera", "frame", "keyframe"),
    "narrative": ("story", "narrative", "plot"),
    "rhythm": ("rhythm", "pacing", "beat", "timing"),
    "provider": ("provider", "model", "api"),
    "generation_failure": ("failed", "failure", "error", "blocked"),
    "asset": ("asset", "graph_asset"),
}
SAFE_TOKEN_RE = re.compile(r"[^a-zA-Z0-9_.:-]+")
ASSET_GRAPH_FEEDBACK_DECISIONS = {"confirm", "lock", "revise", "reject"}


def sanitize_quality_feedback(feedback: dict[str, Any]) -> dict[str, Any]:
    if feedback.get("kind") == "studio_quality_feedback":
        ratings = {
            key: value
            for key, value in (feedback.get("ratings") or {}).items()
            if key in QUALITY_FEEDBACK_METRICS and _rating_or_none(value) is not None
        }
        target_change_success = _rating_or_none(feedback.get("target_change_success"))
        drift_notes = _sanitize_feedback_text(feedback.get("drift_notes"))
        return {
            "kind": "studio_quality_feedback",
            "node_id": _safe_token(feedback.get("node_id")),
            "node_type": _safe_token(feedback.get("node_type")),
            "video_job_id": _safe_token(feedback.get("video_job_id")),
            "video_revision_job_id": _safe_token(feedback.get("video_revision_job_id")),
            "artifact_ref": _safe_token(feedback.get("artifact_ref")),
            "safe_preview_ref": "runtime_preview_endpoint"
            if feedback.get("safe_preview_ref") == "runtime_preview_endpoint"
            else "none",
            "ratings": ratings,
            "target_change_success": target_change_success,
            "drift_notes": drift_notes,
            "feedback_taxonomy": _feedback_taxonomy(
                kind="studio_quality_feedback",
                ratings=ratings,
                target_change_success=target_change_success,
                text=drift_notes,
                decisions=[],
            ),
            "prompt_char_count": _bounded_int(feedback.get("prompt_char_count")),
            "result_char_count": _bounded_int(feedback.get("result_char_count")),
            "raw_evidence_policy": "raw_evidence_not_memory",
            "feedback_is_memory": False,
            "writes_long_term_memory": False,
            "writes_company_kb": False,
            "safety_boundary": {
                "no_provider_raw": True,
                "no_private_external_link": True,
                "no_local_path": True,
                "no_media_bytes": True,
            },
        }
    if feedback.get("kind") in {"studio_asset_graph_feedback", "asset_graph_feedback"}:
        decisions = _sanitize_asset_graph_decisions(feedback.get("decisions") or feedback.get("asset_decisions"))
        return {
            "kind": "studio_asset_graph_feedback",
            "node_id": _safe_token(feedback.get("node_id")),
            "node_type": _safe_token(feedback.get("node_type")),
            "asset_graph_ref": _safe_token(feedback.get("asset_graph_ref")),
            "decisions": decisions,
            "feedback_taxonomy": _feedback_taxonomy(
                kind="studio_asset_graph_feedback",
                ratings={},
                target_change_success=None,
                text="",
                decisions=decisions,
            ),
            "raw_evidence_policy": "asset_graph_feedback_overlay_not_memory",
            "feedback_is_memory": False,
            "writes_long_term_memory": False,
            "writes_company_kb": False,
            "safety_boundary": {
                "no_provider_raw": True,
                "no_private_external_link": True,
                "no_local_path": True,
                "no_media_bytes": True,
            },
        }
    return {
        "kind": _safe_token(feedback.get("kind")) or "runtime_feedback",
        "note": _sanitize_feedback_text(feedback.get("note") or feedback.get("summary")),
        "feedback_taxonomy": ["general"],
        "raw_evidence_policy": "raw_evidence_not_memory",
        "feedback_is_memory": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
    }


def _safe_token(value: Any) -> str:
    return SAFE_TOKEN_RE.sub("_", str(value or "")).strip("_")[:120]


def _sanitize_feedback_text(value: Any) -> str:
    text = str(value or "")
    text = re.sub(r"Bearer\s+\S+", "Bearer <redacted>", text, flags=re.IGNORECASE)
    text = re.sub(r"[A-Za-z]:\\[^\s\"'<>]+", "<local-path-redacted>", text)
    text = re.sub(r"https?://[^\s\"'<>]+", "<url-redacted>", text)
    return text[:600]


def _sanitize_asset_graph_decisions(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    decisions: list[dict[str, Any]] = []
    for item in value[:32]:
        if not isinstance(item, dict):
            continue
        decision = str(item.get("decision") or "").strip()
        graph_asset_id = _safe_token(item.get("graph_asset_id") or item.get("asset_id"))
        if decision not in ASSET_GRAPH_FEEDBACK_DECISIONS or not graph_asset_id:
            continue
        decisions.append(
            {
                "graph_asset_id": graph_asset_id,
                "decision": decision,
                "label": _sanitize_feedback_text(item.get("label"))[:120],
                "note": _sanitize_feedback_text(item.get("note") or item.get("reason"))[:240],
                "continuity_locks": _safe_text_list(item.get("continuity_locks") or item.get("lock_updates"), limit=8),
                "negative_locks": _safe_text_list(item.get("negative_locks") or item.get("avoid_updates"), limit=8),
            }
        )
    return decisions


def _feedback_taxonomy(
    *,
    kind: str,
    ratings: dict[str, int],
    target_change_success: int | None,
    text: str,
    decisions: list[dict[str, Any]],
) -> list[str]:
    categories: set[str] = set()
    if kind == "studio_asset_graph_feedback":
        categories.add("asset")
    for metric in ratings:
        categories.update(METRIC_FEEDBACK_TAXONOMY.get(metric, ()))
    if target_change_success is not None:
        categories.add("revision")
    categories.update(_taxonomy_from_text(text))
    for decision in decisions:
        if decision.get("decision") in {"revise", "reject"}:
            categories.add("revision")
        categories.update(_taxonomy_from_text(" ".join(_decision_text(decision))))
    if not categories:
        categories.add("general")
    return [category for category in FEEDBACK_TAXONOMY_CATEGORIES if category in categories]


def _decision_text(decision: dict[str, Any]) -> list[str]:
    values = [str(decision.get("label") or ""), str(decision.get("note") or "")]
    for key in ("continuity_locks", "negative_locks"):
        items = decision.get(key)
        if isinstance(items, list):
            values.extend(str(item) for item in items)
    return values


def _taxonomy_from_text(text: str) -> set[str]:
    lowered = str(text or "").lower()
    categories: set[str] = set()
    for category, keywords in TEXT_FEEDBACK_TAXONOMY.items():
        if any(keyword in lowered for keyword in keywords):
            categories.add(category)
    return categories


def _safe_text_list(value: Any, *, limit: int) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        text = _sanitize_feedback_text(item).strip()
        if text and text not in result:
            result.append(text[:160])
        if len(result) >= limit:
            break
    return result


def _rating_or_none(value: Any) -> int | None:
    try:
        rating = int(value)
    except (TypeError, ValueError):
        return None
    return rating if 1 <= rating <= 5 else None


def _bounded_int(value: Any) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, min(number, 200_000))


__all__ = (
    "ALGORITHM_ID",
    "EVIDENCE_BOUNDARY",
    "FAILURE_MODES",
    "INPUT_CONTRACT",
    "OUTPUT_CONTRACT",
    "ASSET_GRAPH_FEEDBACK_DECISIONS",
    "FEEDBACK_TAXONOMY_CATEGORIES",
    "QUALITY_FEEDBACK_METRICS",
    "sanitize_quality_feedback",
)
