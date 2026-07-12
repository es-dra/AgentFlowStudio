from __future__ import annotations

from typing import Any, Callable

from apps.api.runtime_store import safe_id


TextSanitizer = Callable[[Any, str, int], str]
NumberSanitizer = Callable[[Any, float], float]


def production_graph_snapshot(value: Any, *, text: TextSanitizer, number: NumberSanitizer) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    summary = value.get("summary") if isinstance(value.get("summary"), dict) else {}
    nodes = []
    for item in value.get("nodes", []) if isinstance(value.get("nodes"), list) else []:
        if not isinstance(item, dict):
            continue
        node_type = text(item.get("node_type"), "", 80)
        if node_type != "fixed_visual_asset":
            continue
        asset_id = safe_id(text(item.get("asset_id") or item.get("visual_asset_id") or item.get("id"), "", 160))
        if asset_id:
            nodes.append({"node_type": node_type, "asset_id": asset_id})
        if len(nodes) >= 24:
            break
    result = {
        "summary": {
            "fixed_visual_asset_count": int(max(0, min(99, number(summary.get("fixed_visual_asset_count"), 0)))),
            "human_review_needed": bool(summary.get("human_review_needed")),
            "content_quality_status": text(summary.get("content_quality_status"), "", 80),
        },
        "nodes": nodes,
    }
    if not result["summary"]["fixed_visual_asset_count"] and not nodes:
        return {}
    return result


def production_graph_review(value: Any, *, text: TextSanitizer) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    result = {
        "artifact_id": text(value.get("artifact_id"), "", 180),
        "fixed_asset_reuse_count": int(max(0, min(99, int(value.get("fixed_asset_reuse_count") or 0)))),
        "fixed_visual_asset_ids": _text_list(value.get("fixed_visual_asset_ids"), text=text, max_items=24, max_length=120, safe=True),
    }
    return {key: item for key, item in result.items() if item not in ("", [], {}, None)}


def source_evidence_refs(value: Any, *, text: TextSanitizer) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for item in value if isinstance(value, list) else []:
        if not isinstance(item, dict):
            continue
        ref = {
            "asset_id": safe_id(text(item.get("asset_id"), "", 120)),
            "asset_type": _asset_type(item.get("asset_type")),
            "label": text(item.get("label"), "", 120),
            "status": text(item.get("status"), "", 40),
            "source_human_gate_id": text(item.get("source_human_gate_id"), "", 160),
            "source_asset_card_candidate_id": text(item.get("source_asset_card_candidate_id"), "", 180),
            "source_stage": text(item.get("source_stage"), "", 80),
            "provider_calls_started": bool(item.get("provider_calls_started")),
            "human_creative_acceptance_claimed": bool(item.get("human_creative_acceptance_claimed")),
        }
        if ref["asset_id"] or ref["source_human_gate_id"] or ref["source_asset_card_candidate_id"]:
            refs.append(ref)
        if len(refs) >= 8:
            break
    return refs


def visual_asset_source_evidence(value: Any, *, text: TextSanitizer) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    result = {
        "source_human_gate_id": text(value.get("source_human_gate_id"), "", 160),
        "source_asset_card_candidate_id": text(value.get("source_asset_card_candidate_id"), "", 180),
        "source_stage": text(value.get("source_stage"), "", 80),
        "provider_calls_started": bool(value.get("provider_calls_started")),
        "generated_media_claimed": bool(value.get("generated_media_claimed")),
        "human_creative_acceptance_claimed": bool(value.get("human_creative_acceptance_claimed")),
        "business_validation_claimed": bool(value.get("business_validation_claimed")),
    }
    return {key: item for key, item in result.items() if item not in ("", [], {}, None)}


def promotion_gate_summary(value: Any, *, text: TextSanitizer) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    result = {
        "scope": text(value.get("scope"), "", 120),
        "source_contract": text(value.get("source_contract"), "", 120),
        "source_human_gate_id": text(value.get("source_human_gate_id"), "", 160),
        "source_asset_card_candidate_id": text(value.get("source_asset_card_candidate_id"), "", 180),
        "provider_calls_started": bool(value.get("provider_calls_started")),
        "generated_media_claimed": bool(value.get("generated_media_claimed")),
        "human_creative_acceptance_claimed": bool(value.get("human_creative_acceptance_claimed")),
        "business_validation_claimed": bool(value.get("business_validation_claimed")),
    }
    return {key: item for key, item in result.items() if item not in ("", [], {}, None)}


def visual_assets(value: Any, *, project_id: str | None, preview_url: Callable[..., str], text: TextSanitizer) -> list[dict[str, Any]]:
    assets: list[dict[str, Any]] = []
    for item in value if isinstance(value, list) else []:
        if not isinstance(item, dict):
            continue
        asset = {
            "asset_id": safe_id(text(item.get("asset_id") or item.get("visual_asset_id"), "", 120)),
            "visual_asset_id": safe_id(text(item.get("visual_asset_id") or item.get("asset_id"), "", 120)),
            "asset_type": _asset_type(item.get("asset_type")),
            "label": text(item.get("label") or item.get("title"), "", 120),
            "status": text(item.get("status") or item.get("asset_status"), "fixed", 40),
            "signature": text(item.get("signature") or item.get("safe_summary"), "", 1000),
            "feature_card": _text_map(item.get("feature_card"), text=text, max_items=32, max_length=1000),
            "negative_locks": _text_list(item.get("negative_locks"), text=text, max_items=32, max_length=500),
            "image_asset_refs": _text_list(item.get("image_asset_refs"), text=text, max_items=16, max_length=120, safe=True),
            "source_node_id": text(item.get("source_node_id"), "", 120),
            "runtime_status": text(item.get("runtime_status"), "", 80),
            "disabled_reason": text(item.get("disabled_reason"), "", 240),
            "excluded_reason": text(item.get("excluded_reason"), "", 120),
        }
        source_evidence = visual_asset_source_evidence(item.get("source_evidence"), text=text)
        promotion_gate = promotion_gate_summary(item.get("promotion_gate"), text=text)
        if source_evidence:
            asset["source_evidence"] = source_evidence
        if promotion_gate:
            asset["promotion_gate"] = promotion_gate
        preview = preview_url(item.get("preview_url"), project_id=project_id) if item.get("preview_url") else ""
        if preview:
            asset["preview_url"] = preview
        if asset["asset_id"]:
            assets.append(asset)
        if len(assets) >= 24:
            break
    return assets




def _text_map(value: Any, *, text: TextSanitizer, max_items: int, max_length: int) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, str] = {}
    for key, item in list(value.items())[:max_items]:
        safe_key = safe_id(str(key))[:80]
        safe_value = text(item, "", max_length)
        if safe_key and safe_value:
            result[safe_key] = safe_value
    return result


def _text_list(value: Any, *, text: TextSanitizer, max_items: int, max_length: int, safe: bool = False) -> list[str]:
    source = value if isinstance(value, list) else []
    result = []
    for item in source[:max_items]:
        clean = text(item, "", max_length)
        if clean:
            result.append(safe_id(clean) if safe else clean)
    return result


def _asset_type(value: Any) -> str:
    clean = str(value or "").strip()
    return clean if clean in {"character", "scene", "prop", "video"} else "character"


__all__ = (
    "production_graph_snapshot",
    "production_graph_review",
    "promotion_gate_summary",
    "source_evidence_refs",
    "visual_asset_source_evidence",
    "visual_assets",
)
