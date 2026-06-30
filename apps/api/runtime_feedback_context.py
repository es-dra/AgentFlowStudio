from __future__ import annotations

import re
from typing import Any

from apps.api.runtime_store import RuntimeStore, reject_unsafe_payload


OVERLAY_ARTIFACT_TYPE = "agentflow_runtime_feedback_candidate_context_overlay"
MAX_CONTEXT_OVERLAYS = 5
_URL_RE = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)


def attach_feedback_context_overlays(
    store: RuntimeStore,
    project_id: str,
    context_bundle: dict[str, Any],
) -> dict[str, Any]:
    overlays = feedback_context_overlays(store, project_id)
    if not overlays:
        return context_bundle
    bundle = dict(context_bundle)
    trace = dict(bundle.get("trace_summary") or {})
    trace["feedback_context_overlay_count"] = len(overlays)
    trace["feedback_context_overlay_ids"] = [item["overlay_id"] for item in overlays]
    trace["feedback_context_overlay_source"] = "project_manifest_feedback_refs"
    trace["feedback_overlays_are_memory"] = False
    trace["feedback_overlays_write_company_kb"] = False
    bundle["feedback_context_overlays"] = overlays
    bundle["trace_summary"] = trace
    reject_unsafe_payload(bundle)
    return bundle


def feedback_context_overlays(
    store: RuntimeStore,
    project_id: str,
    *,
    limit: int = MAX_CONTEXT_OVERLAYS,
) -> list[dict[str, Any]]:
    manifest = store.ensure_project_manifest(project_id)
    refs = [item for item in manifest.get("feedback_refs", []) if isinstance(item, dict)]
    overlays: list[dict[str, Any]] = []
    for ref in reversed(refs):
        if str(ref.get("artifact_type") or "") != OVERLAY_ARTIFACT_TYPE:
            continue
        summary = _overlay_summary(store, ref)
        if not summary:
            continue
        overlays.append(summary)
        if len(overlays) >= limit:
            break
    overlays.reverse()
    reject_unsafe_payload({"feedback_context_overlays": overlays})
    return overlays


def _overlay_summary(store: RuntimeStore, ref: dict[str, Any]) -> dict[str, Any] | None:
    artifact_id = str(ref.get("artifact_id") or "").strip()
    if not artifact_id:
        return None
    try:
        artifact = store.read_artifact(artifact_id)
    except (KeyError, ValueError, TypeError):
        return None
    payload = artifact.get("payload")
    if not isinstance(payload, dict) or payload.get("artifact_type") != OVERLAY_ARTIFACT_TYPE:
        return None
    overlay = payload.get("overlay") if isinstance(payload.get("overlay"), dict) else {}
    safety = payload.get("safety_boundary") if isinstance(payload.get("safety_boundary"), dict) else {}
    if (
        overlay.get("context_overlay_written") is not True
        or overlay.get("overlay_scope") != "next_local_context_pass"
        or payload.get("writes_long_term_memory") is not False
        or payload.get("writes_company_kb") is not False
        or payload.get("provider_calls_started") is not False
        or safety.get("raw_provider_response_stored") is not False
        or safety.get("external_private_link_stored") is not False
        or safety.get("absolute_path_stored") is not False
        or safety.get("media_bytes_stored") is not False
    ):
        return None
    summary = {
        "overlay_id": _safe_text(payload.get("overlay_id"), limit=180),
        "source_feedback_id": _safe_text(payload.get("source_feedback_id"), limit=180),
        "source_promotion_decision_id": _safe_text(payload.get("source_promotion_decision_id"), limit=180),
        "candidate_id": _safe_text(payload.get("candidate_id"), limit=180),
        "candidate_scope": _safe_text(payload.get("candidate_scope"), limit=120),
        "safe_target": _safe_dict(payload.get("safe_target"), limit=180),
        "safe_evidence_summary": _safe_evidence(payload.get("safe_evidence_summary")),
        "overlay_scope": _safe_text(overlay.get("overlay_scope"), limit=120),
        "overlay_intent": _safe_text(overlay.get("overlay_intent"), limit=600),
        "decision_effect": _safe_text(overlay.get("decision_effect"), limit=120),
        "context_overlay_consumed": True,
        "candidate_feedback_included_in_context": bool(overlay.get("candidate_included_in_context")),
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "safety_boundary": {
            "raw_provider_response_stored": bool(safety.get("raw_provider_response_stored")),
            "external_private_link_stored": bool(safety.get("external_private_link_stored")),
            "absolute_path_stored": bool(safety.get("absolute_path_stored")),
            "media_bytes_stored": bool(safety.get("media_bytes_stored")),
        },
        "artifact_ref": {
            "artifact_id": _safe_text(artifact.get("artifact_id"), limit=180),
            "artifact_type": _safe_text(artifact.get("artifact_type"), limit=180),
            "role": _safe_text(artifact.get("role"), limit=120),
            "filename": _safe_text(artifact.get("filename"), limit=180),
        },
    }
    if not summary["overlay_id"]:
        return None
    reject_unsafe_payload(summary)
    return summary


def _safe_text(value: Any, *, limit: int) -> str:
    return _URL_RE.sub("<url-redacted>", " ".join(str(value or "").split()))[:limit]


def _safe_dict(value: Any, *, limit: int) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {
        _safe_text(key, limit=80): _safe_text(item, limit=limit)
        for key, item in value.items()
        if _safe_text(key, limit=80) and _safe_text(item, limit=limit)
    }


def _safe_evidence(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {
        "rating_count": _bounded_int(value.get("rating_count")),
        "decision_count": _bounded_int(value.get("decision_count")),
        "has_note": bool(value.get("has_note")),
        "raw_evidence_policy": _safe_text(value.get("raw_evidence_policy"), limit=120) or "raw_evidence_not_memory",
    }


def _bounded_int(value: Any) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, min(number, 1000))


__all__ = (
    "MAX_CONTEXT_OVERLAYS",
    "OVERLAY_ARTIFACT_TYPE",
    "attach_feedback_context_overlays",
    "feedback_context_overlays",
)
