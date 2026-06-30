from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from agentflow.algorithms.feedback_overlay_prompt_policy import feedback_overlay_prompt_policy
from agentflow.algorithms.quality_feedback_scoring import sanitize_quality_feedback


ALGORITHM_ID = "afs.model_call_context.v0.1"
INPUT_CONTRACT = "project node intent, prompt, context bundle, asset states, refs, preferences, provider constraints, feedback evidence"
OUTPUT_CONTRACT = "safe model-call context with context id, source summary, eligible assets, refs, feedback evidence, and trace"
FAILURE_MODES = ("unknown_operation_intent", "unsafe_context_field_redacted", "draft_asset_rejected")
EVIDENCE_BOUNDARY = "pre-provider safe context only; no secrets, local paths, signed URLs, provider raw response, or media bytes"

SCHEMA_VERSION = "afs_model_call_context.v0.1"
OPERATION_INTENT_TARGETS = {
    "prompt_optimize": "prompt",
    "image_generate": "image",
    "video_generate": "video",
    "visual_inspect": "asset_card",
    "revision": "revision",
}

_URL_RE = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)
_BEARER_RE = re.compile(r"Bearer\s+\S+", re.IGNORECASE)
_WINDOWS_PATH_RE = re.compile(r"[A-Za-z]:\\[^\s\"'<>]+")
_API_KEY_RE = re.compile(r"(?i)(api[_-]?key|secret|token)\s*=\s*[^\s\"'<>]+")


def build_model_call_context(
    *,
    project_id: str,
    node_ref: dict[str, Any],
    operation_intent: str,
    generation_target: str | None = None,
    input_prompt: str = "",
    context_bundle: dict[str, Any] | None = None,
    fixed_assets: list[dict[str, Any]] | None = None,
    draft_assets: list[dict[str, Any]] | None = None,
    rejected_assets: list[dict[str, Any]] | None = None,
    retired_assets: list[dict[str, Any]] | None = None,
    reference_image_refs: list[str] | None = None,
    upstream_refs: list[str] | None = None,
    user_preferences: dict[str, Any] | None = None,
    expert_rule_ids: list[str] | None = None,
    provider_constraints: dict[str, Any] | None = None,
    feedback_events: list[dict[str, Any]] | None = None,
    revision_control: dict[str, Any] | None = None,
) -> dict[str, Any]:
    operation = str(operation_intent or "").strip()
    if operation not in OPERATION_INTENT_TARGETS:
        raise ValueError("unknown model-call operation intent")
    target = str(generation_target or OPERATION_INTENT_TARGETS[operation]).strip()
    bundle = context_bundle or {}
    fixed_ids = _asset_ids(fixed_assets)
    draft_ids = _asset_ids(draft_assets)
    rejected_ids = _asset_ids(rejected_assets)
    retired_ids = _asset_ids(retired_assets)
    refs = _dedupe([*_bundle_reference_refs(bundle), *(reference_image_refs or [])])
    events = [sanitize_quality_feedback(item) for item in (feedback_events or []) if isinstance(item, dict)]
    overlays = _bundle_feedback_context_overlays(bundle)
    overlay_prompt_policy = feedback_overlay_prompt_policy(
        context_bundle=bundle,
        context_overlays=overlays,
    )
    payload = {
        "schema_version": SCHEMA_VERSION,
        "algorithm_id": ALGORITHM_ID,
        "project_id": str(project_id or "").strip(),
        "node_ref": {
            "node_id": str(node_ref.get("node_id") or "").strip(),
            "node_type": str(node_ref.get("node_type") or "").strip(),
            "upstream_refs": _safe_ref_list(upstream_refs or []),
        },
        "operation_intent": operation,
        "generation_target": target,
        "input_prompt": {
            "visible_prompt": _sanitize_text(input_prompt),
            "char_count": len(str(input_prompt or "")),
        },
        "context_sources": {
            "context_bundle_present": bool(context_bundle),
            "context_bundle_algorithm_id": bundle.get("algorithm_id"),
            "included_asset_count": len(bundle.get("included_assets") or []),
            "excluded_asset_count": len(bundle.get("excluded_assets") or []),
            "feedback_context_overlay_count": len(overlays),
            "feedback_context_overlay_prompt_policy_id": overlay_prompt_policy["policy_id"],
            "upstream_ref_count": len(upstream_refs or []),
        },
        "asset_context": {
            "fixed_asset_ids": fixed_ids,
            "draft_asset_ids": draft_ids,
            "rejected_asset_ids": rejected_ids,
            "retired_asset_ids": retired_ids,
            "context_eligible_asset_ids": fixed_ids,
            "draft_assets_enter_context": False,
        },
        "reference_context": {
            "reference_image_refs": _safe_ref_list(refs),
            "reference_image_count": len(refs),
        },
        "preference_context": {
            "user_preferences": user_preferences or {},
            "expert_rule_ids": _safe_ref_list(expert_rule_ids or []),
        },
        "feedback_context": {
            "events": events,
            "context_overlays": overlays,
            "prompt_policy": overlay_prompt_policy,
            "revision_control": revision_control or {},
            "feedback_is_memory": False,
        },
        "provider_constraints": provider_constraints or {},
        "safety_boundary": _safety_boundary(),
        "outputs": {
            "context_bundle_ref": "inline_context_bundle" if context_bundle else "not_provided",
            "canonical_brief_ref": "derived_after_prompt_optimization",
            "request_plan_ref": "derived_by_request_projection",
            "safe_manifest_ref": "provider_boundary_output",
        },
        "trace_summary": {
            "context_bundle_present": bool(context_bundle),
            "included_asset_ids": _bundle_asset_ids(bundle, "included_assets"),
            "excluded_asset_ids": _bundle_asset_ids(bundle, "excluded_assets"),
            "feedback_context_overlay_ids": [item["overlay_id"] for item in overlays if item.get("overlay_id")],
            "feedback_context_overlay_prompt_policy": overlay_prompt_policy,
            "warning_ids": _warning_ids(bundle),
            "draft_assets_rejected": True,
            "raw_evidence_not_memory": True,
        },
    }
    payload = _sanitize_payload(payload)
    payload["context_id"] = _context_id(payload)
    return payload


def _asset_ids(values: list[dict[str, Any]] | None) -> list[str]:
    return _safe_ref_list([str(item.get("asset_id") or "") for item in (values or []) if isinstance(item, dict)])


def _bundle_asset_ids(bundle: dict[str, Any], key: str) -> list[str]:
    values = bundle.get(key) if isinstance(bundle, dict) else []
    return _safe_ref_list([str(item.get("asset_id") or "") for item in (values or []) if isinstance(item, dict)])


def _bundle_reference_refs(bundle: dict[str, Any]) -> list[str]:
    values = bundle.get("reference_image_channel") if isinstance(bundle, dict) else []
    return [str(item.get("asset_id") or "") for item in (values or []) if isinstance(item, dict)]


def _bundle_feedback_context_overlays(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    values = bundle.get("feedback_context_overlays") if isinstance(bundle, dict) else []
    overlays: list[dict[str, Any]] = []
    for item in (values if isinstance(values, list) else []):
        if not isinstance(item, dict):
            continue
        overlay = {
            "overlay_id": _sanitize_text(item.get("overlay_id")).strip(),
            "candidate_id": _sanitize_text(item.get("candidate_id")).strip(),
            "candidate_scope": _sanitize_text(item.get("candidate_scope")).strip(),
            "feedback_taxonomy": _safe_ref_list(
                [_sanitize_text(taxonomy_id).strip() for taxonomy_id in _safe_list(item.get("feedback_taxonomy"))]
            ),
            "target_binding": _safe_payload(item.get("target_binding")),
            "scope_policy": _safe_payload(item.get("scope_policy")),
            "conflict_summary": _safe_payload(item.get("conflict_summary")),
            "safe_evidence_summary": _safe_evidence_summary(item.get("safe_evidence_summary")),
            "overlay_scope": _sanitize_text(item.get("overlay_scope")).strip(),
            "decision_effect": _sanitize_text(item.get("decision_effect")).strip(),
            "context_overlay_consumed": bool(item.get("context_overlay_consumed")),
            "provider_calls_started": False,
            "writes_long_term_memory": False,
            "writes_company_kb": False,
        }
        if overlay["overlay_id"]:
            overlays.append(overlay)
    return overlays


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _safe_evidence_summary(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    summary = {
        "rating_count": _bounded_int(value.get("rating_count")),
        "decision_count": _bounded_int(value.get("decision_count")),
        "has_note": bool(value.get("has_note")),
        "raw_evidence_policy": _sanitize_text(value.get("raw_evidence_policy")).strip() or "raw_evidence_not_memory",
    }
    if "taxonomy_count" in value:
        summary["taxonomy_count"] = _bounded_int(value.get("taxonomy_count"))
    return summary


def _safe_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            _sanitize_text(key).strip()[:80]: _safe_payload(item)
            for key, item in list(value.items())[:24]
            if _sanitize_text(key).strip()
        }
    if isinstance(value, list):
        return [_safe_payload(item) for item in value[:24]]
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return _bounded_int(value)
    return _sanitize_text(value).strip()[:180]


def _bounded_int(value: Any) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, min(number, 1000))


def _warning_ids(bundle: dict[str, Any]) -> list[str]:
    return _safe_ref_list([str(item.get("warning_id") or "") for item in (bundle.get("warnings") or []) if isinstance(item, dict)])


def _safe_ref_list(values: list[str]) -> list[str]:
    return _dedupe([_sanitize_text(value).strip() for value in values if str(value or "").strip()])


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _sanitize_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize_payload(item) for key, item in value.items() if str(key) not in {"raw_json", "provider_raw"}}
    if isinstance(value, list):
        return [_sanitize_payload(item) for item in value]
    if isinstance(value, str):
        return _sanitize_text(value)
    return value


def _sanitize_text(value: Any) -> str:
    text = str(value or "")
    text = _BEARER_RE.sub("<credential-redacted>", text)
    text = _URL_RE.sub("<url-redacted>", text)
    text = _WINDOWS_PATH_RE.sub("<local-path-redacted>", text)
    text = _API_KEY_RE.sub("<credential-redacted>", text)
    return text[:2000]


def _context_id(payload: dict[str, Any]) -> str:
    data = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "mctx_" + hashlib.sha256(data).hexdigest()[:20]


def _safety_boundary() -> dict[str, bool]:
    return {
        "no_secrets": True,
        "no_provider_raw": True,
        "no_credentialed_url": True,
        "no_local_path": True,
        "no_media_bytes": True,
        "feedback_is_not_memory": True,
        "draft_assets_are_not_context_truth": True,
    }


sanitize_context_payload = _sanitize_payload
sanitize_context_text = _sanitize_text


__all__ = (
    "ALGORITHM_ID",
    "EVIDENCE_BOUNDARY",
    "FAILURE_MODES",
    "INPUT_CONTRACT",
    "OPERATION_INTENT_TARGETS",
    "OUTPUT_CONTRACT",
    "SCHEMA_VERSION",
    "build_model_call_context",
    "sanitize_context_payload",
    "sanitize_context_text",
)
