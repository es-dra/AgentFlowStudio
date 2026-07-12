from __future__ import annotations

from typing import Any, Callable

from apps.api import runtime_studio_state_param_values as param_values
from apps.api.runtime_store import safe_id


TextSanitizer = Callable[[Any, str, int], str]
NumberSanitizer = Callable[[Any, float], float]


def generation_manifest_summary(
    value: Any,
    *,
    text: TextSanitizer,
    number: NumberSanitizer,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    batch_summary = value.get("batch_summary") if isinstance(value.get("batch_summary"), dict) else {}
    diagnostics = value.get("provider_diagnostics") if isinstance(value.get("provider_diagnostics"), dict) else {}
    retry = value.get("retry") if isinstance(value.get("retry"), dict) else {}
    result: dict[str, Any] = {
        "status": text(value.get("status"), "", 40),
        "batch_status": text(value.get("batch_status"), "", 40),
        "stage": text(value.get("stage") or diagnostics.get("provider_stage"), "", 80),
        "failure_class": text(value.get("failure_class") or diagnostics.get("failure_class"), "", 80),
        "job_id": safe_id(text(value.get("job_id"), "", 120)),
        "node_id": safe_id(text(value.get("node_id"), "", 120)),
        "artifact_id": safe_id(text(value.get("artifact_id"), "", 120)),
        "output_count": _count(number(value.get("output_count"), 0), maximum=9999),
        "reference_image_count": _count(number(value.get("reference_image_count"), 0), maximum=9999),
        "retry_count": _count(number(value.get("retry_count") or retry.get("retry_count"), 0), maximum=99),
        "provider_calls_started": bool(value.get("provider_calls_started")),
        "provider_diagnostics": _provider_diagnostics(diagnostics, text=text, number=number),
        "batch_summary": {
            "requested_count": _count(number(batch_summary.get("requested_count"), 0), maximum=9999),
            "complete_count": _count(number(batch_summary.get("complete_count"), 0), maximum=9999),
            "retryable_count": _count(number(batch_summary.get("retryable_count"), 0), maximum=9999),
            "needs_attention_count": _count(number(batch_summary.get("needs_attention_count"), 0), maximum=9999),
        },
        "retry": _retry_summary(retry, text=text, number=number),
        "blocks": _generation_blocks(value.get("blocks"), text=text, number=number),
        "review_preview_refs": _preview_refs(value.get("review_preview_refs"), text=text, number=number),
    }
    return _compact(result)


def model_call_context_summary(value: Any, *, text: TextSanitizer, number: NumberSanitizer) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {
        "context_id": safe_id(text(value.get("context_id"), "", 160)),
        "schema_version": text(value.get("schema_version"), "", 80),
        "operation_intent": text(value.get("operation_intent"), "", 80),
        "generation_target": text(value.get("generation_target"), "", 80),
        "artifact": _artifact_ref(value.get("artifact"), text=text),
        "context_sources": _count_map(value.get("context_sources"), text=text, number=number),
        "asset_context": _model_asset_context(value.get("asset_context"), number=number),
        "reference_context": _count_map(value.get("reference_context"), text=text, number=number),
        "provider_constraints": _provider_constraints(value.get("provider_constraints"), text=text),
        "trace_summary": _trace_summary(value.get("trace_summary"), text=text),
        "safety_boundary": _safety_boundary(value.get("safety_boundary")),
        "non_claims": param_values.text_list(value.get("non_claims"), text=text, max_items=12, max_length=160, safe=True),
    }


def safe_refs(value: Any, *, text: TextSanitizer) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    for item in value if isinstance(value, list) else []:
        if not isinstance(item, dict):
            continue
        label = text(item.get("label"), "", 80)
        ref = safe_id(text(item.get("value"), "", 160))
        if label and ref:
            refs.append({"label": label, "value": ref})
        if len(refs) >= 8:
            break
    return refs


def safe_public_text(value: Any, *, text: TextSanitizer, limit: int) -> str:
    cleaned = text(value, "", limit)
    for marker in (
        "provider_raw_response",
        "provider_raw_persisted",
        "provider_raw",
        "raw_provider_response",
        "raw_response",
        "provider_response",
    ):
        if marker in cleaned.lower():
            cleaned = cleaned.replace(marker, "<provider-response-redacted>")
            cleaned = cleaned.replace(marker.upper(), "<provider-response-redacted>")
    return cleaned[:limit]


def _generation_blocks(value: Any, *, text: TextSanitizer, number: NumberSanitizer) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for item in value if isinstance(value, list) else []:
        if not isinstance(item, dict):
            continue
        block = {
            "block_id": safe_id(text(item.get("block_id") or item.get("code"), "", 100)),
            "candidate_id": safe_id(text(item.get("candidate_id"), "", 32)),
            "reason": safe_public_text(item.get("reason") or item.get("message") or item.get("error"), text=text, limit=360),
            "required_gate": text(item.get("required_gate"), "", 80),
            "failure_class": text(item.get("failure_class"), "", 80),
            "provider_stage": text(item.get("provider_stage"), "", 80),
            "retry_count": _count(number(item.get("retry_count"), 0), maximum=99),
            "attempt_count": _count(number(item.get("attempt_count"), 0), maximum=100),
            "provider_elapsed_ms": max(0, number(item.get("provider_elapsed_ms"), 0)),
        }
        blocks.append(_compact(block))
        if len(blocks) >= 8:
            break
    return blocks


def _provider_diagnostics(value: Any, *, text: TextSanitizer, number: NumberSanitizer) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return _compact(
        {
            "provider_stage": text(value.get("provider_stage"), "", 80),
            "failure_class": text(value.get("failure_class"), "", 80),
            "error_type": text(value.get("error_type"), "", 80),
            "reason": safe_public_text(value.get("reason"), text=text, limit=360),
            "required_gate": text(value.get("required_gate"), "", 80),
            "retry_count": _count(number(value.get("retry_count"), 0), maximum=99),
            "attempt_count": _count(number(value.get("attempt_count"), 0), maximum=100),
            "provider_elapsed_ms": max(0, number(value.get("provider_elapsed_ms"), 0)),
        }
    )


def _retry_summary(value: Any, *, text: TextSanitizer, number: NumberSanitizer) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return _compact(
        {
            "retry_count": _count(number(value.get("retry_count"), 0), maximum=99),
            "default_scope": text(value.get("default_scope"), "", 80),
            "retryable_item_ids": param_values.text_list(value.get("retryable_item_ids"), text=text, max_items=16, max_length=80, safe=True),
            "preserved_item_ids": param_values.text_list(value.get("preserved_item_ids"), text=text, max_items=16, max_length=80, safe=True),
            "preserve_successful_outputs": bool(value.get("preserve_successful_outputs")),
        }
    )


def _preview_refs(value: Any, *, text: TextSanitizer, number: NumberSanitizer) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for item in value if isinstance(value, list) else []:
        if not isinstance(item, dict):
            continue
        refs.append(
            _compact(
                {
                    "job_id": safe_id(text(item.get("job_id"), "", 120)),
                    "candidate_id": safe_id(text(item.get("candidate_id"), "", 40)),
                    "safe_preview_ref": text(item.get("safe_preview_ref"), "", 220),
                    "byte_count": _count(number(item.get("byte_count"), 0), maximum=100000000),
                    "width": _count(number(item.get("width"), 0), maximum=20000),
                    "height": _count(number(item.get("height"), 0), maximum=20000),
                    "aspect_ratio": text(item.get("aspect_ratio"), "", 20),
                }
            )
        )
        if len(refs) >= 8:
            break
    return refs


def _artifact_ref(value: Any, *, text: TextSanitizer) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return _compact(
        {
            "artifact_id": safe_id(text(value.get("artifact_id"), "", 160)),
            "artifact_type": text(value.get("artifact_type"), "", 120),
            "filename": text(value.get("filename"), "", 120).replace("/", "").replace("\\", ""),
            "role": text(value.get("role"), "", 80),
            "media_type": text(value.get("media_type"), "", 80),
        }
    )


def _count_map(value: Any, *, text: TextSanitizer, number: NumberSanitizer) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, Any] = {}
    for key, item in list(value.items())[:16]:
        safe_key = safe_id(text(key, "", 80))
        if safe_key:
            result[safe_key] = bool(item) if isinstance(item, bool) else _count(number(item, 0), maximum=9999)
    return result


def _model_asset_context(value: Any, *, number: NumberSanitizer) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {
        "context_eligible_asset_count": _count(number(value.get("context_eligible_asset_count"), 0), maximum=9999),
        "draft_assets_enter_context": bool(value.get("draft_assets_enter_context")),
    }


def _provider_constraints(value: Any, *, text: TextSanitizer) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {"capability": text(value.get("capability"), "", 40), "provider_gate": text(value.get("provider_gate"), "", 80)}


def _trace_summary(value: Any, *, text: TextSanitizer) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        return {}
    return {
        "warning_ids": param_values.text_list(value.get("warning_ids"), text=text, max_items=12, max_length=160, safe=True),
        "feedback_context_overlay_ids": param_values.text_list(value.get("feedback_context_overlay_ids"), text=text, max_items=12, max_length=180, safe=True),
    }


def _safety_boundary(value: Any) -> dict[str, bool]:
    if not isinstance(value, dict):
        return {}
    keys = (
        "no_secrets",
        "no_provider_raw",
        "no_credentialed_url",
        "no_local_path",
        "no_media_bytes",
        "feedback_is_not_memory",
        "draft_assets_are_not_context_truth",
    )
    return {key: bool(value.get(key)) for key in keys if key in value}


def _count(value: float, *, maximum: int) -> int:
    return int(max(0, min(maximum, value)))


def _compact(value: dict[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if item not in ("", [], {}, None)}


__all__ = (
    "generation_manifest_summary",
    "model_call_context_summary",
    "safe_public_text",
    "safe_refs",
)
