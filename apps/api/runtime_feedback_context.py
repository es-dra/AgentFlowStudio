from __future__ import annotations

import re
from typing import Any

from agentflow.algorithms.feedback_overlay_prompt_policy import feedback_overlay_prompt_policy
from apps.api.runtime_store import RuntimeStore, reject_unsafe_payload


OVERLAY_ARTIFACT_TYPE = "agentflow_runtime_feedback_candidate_context_overlay"
MAX_CONTEXT_OVERLAYS = 5
_URL_RE = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)


def attach_feedback_context_overlays(
    store: RuntimeStore,
    project_id: str,
    context_bundle: dict[str, Any],
    context_subgraph: Any | None = None,
) -> dict[str, Any]:
    decisions = feedback_context_overlay_decisions(context_subgraph)
    has_decisions = _has_overlay_decisions(decisions)
    overlays = feedback_context_overlays(store, project_id)
    overlays = _apply_overlay_decisions(overlays, decisions)
    if not overlays and not has_decisions:
        return context_bundle
    bundle = dict(context_bundle)
    trace = dict(bundle.get("trace_summary") or {})
    trace["feedback_context_overlay_count"] = len(overlays)
    trace["feedback_context_overlay_ids"] = [item["overlay_id"] for item in overlays]
    trace["feedback_context_overlay_source"] = "project_manifest_feedback_refs"
    trace["feedback_overlays_are_memory"] = False
    trace["feedback_overlays_write_company_kb"] = False
    trace["feedback_context_overlay_prompt_policy"] = feedback_overlay_prompt_policy(
        context_overlays=overlays,
        selected_overlay_ids=decisions["selected_ids"],
        rejected_overlay_ids=decisions["rejected_ids"],
    )
    if has_decisions:
        trace["feedback_context_overlay_decision_source"] = "studio_context_subgraph"
        if decisions["selected_ids"]:
            trace["feedback_context_overlay_selected_ids"] = sorted(decisions["selected_ids"])
        if decisions["rejected_ids"]:
            trace["feedback_context_overlay_rejected_ids"] = sorted(decisions["rejected_ids"])
    if overlays:
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


def feedback_context_overlay_decisions(context_subgraph: Any | None) -> dict[str, set[str]]:
    params = _target_node_parameters(context_subgraph)
    raw = params.get("feedback_context_overlay_decisions")
    if not isinstance(raw, list):
        raw = params.get("feedbackOverlayDecisions")
    if not isinstance(raw, list):
        return {"selected_ids": set(), "rejected_ids": set()}
    selected_ids: set[str] = set()
    rejected_ids: set[str] = set()
    for item in raw[:20]:
        if not isinstance(item, dict):
            continue
        overlay_id = _safe_text(item.get("overlay_id"), limit=180)
        if not overlay_id:
            continue
        decision = _safe_text(item.get("decision"), limit=80)
        if decision in {"include_for_next_context", "included_for_next_context", "include"}:
            selected_ids.add(overlay_id)
        if decision in {"reject_for_next_context", "rejected_for_next_context", "reject"}:
            rejected_ids.add(overlay_id)
    selected_ids -= rejected_ids
    summary = {"selected_ids": selected_ids, "rejected_ids": rejected_ids}
    reject_unsafe_payload(
        {
            "selected_ids": sorted(selected_ids),
            "rejected_ids": sorted(rejected_ids),
        }
    )
    return summary


def _apply_overlay_decisions(overlays: list[dict[str, Any]], decisions: dict[str, set[str]]) -> list[dict[str, Any]]:
    selected_ids = decisions.get("selected_ids") or set()
    rejected_ids = decisions.get("rejected_ids") or set()
    if not selected_ids and not rejected_ids:
        return overlays
    result = []
    for overlay in overlays:
        overlay_id = str(overlay.get("overlay_id") or "")
        if overlay_id in rejected_ids:
            continue
        if selected_ids and overlay_id not in selected_ids:
            continue
        result.append(overlay)
    return result


def _has_overlay_decisions(decisions: dict[str, set[str]]) -> bool:
    return bool(decisions.get("selected_ids") or decisions.get("rejected_ids"))


def _target_node_parameters(context_subgraph: Any | None) -> dict[str, Any]:
    if context_subgraph is None:
        return {}
    target_node_id = _attr_or_key(context_subgraph, "target_node_id")
    nodes = _attr_or_key(context_subgraph, "nodes")
    if not target_node_id or not isinstance(nodes, list):
        return {}
    for node in nodes:
        if _attr_or_key(node, "id") != target_node_id:
            continue
        params = _attr_or_key(node, "node_parameters")
        return params if isinstance(params, dict) else {}
    return {}


def _attr_or_key(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        return value.get(key)
    return getattr(value, key, None)


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
    "feedback_context_overlay_decisions",
    "feedback_context_overlays",
)
