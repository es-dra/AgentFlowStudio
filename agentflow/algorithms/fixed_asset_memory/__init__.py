from __future__ import annotations

from typing import Any


ALGORITHM_ID = "afs.fixed_asset_memory.v0.1"
INPUT_CONTRACT = "human reviewed asset payloads, asset records, status filters, version links"
OUTPUT_CONTRACT = "safe fixed asset records and public projections for Runtime and context resolver"
FAILURE_MODES = ("missing_signature", "empty_feature_card", "draft_context_pollution", "unsafe_projection")
EVIDENCE_BOUNDARY = "human-confirmed safe fields only; no media bytes, provider raw response, signed URLs, or durable memory writes"

VISUAL_ASSET_SCHEMA_VERSION = "0.2.0"
VIDEO_ASSET_SCHEMA_VERSION = "0.1.0"
ASSET_STATUSES = {"draft", "fixed", "rejected", "retired"}


def fixed_context_assets(assets: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        str(asset_id): asset
        for asset_id, asset in assets.items()
        if asset.get("status") == "fixed"
    }


def build_visual_asset_record(
    *,
    project_id: str,
    asset_id: str,
    request: Any,
    created_at: str,
    server_recorded_at: str,
) -> dict[str, Any]:
    return {
        "artifact_type": "agentflow_visual_asset",
        "schema_version": VISUAL_ASSET_SCHEMA_VERSION,
        "project_id": project_id,
        "asset_id": asset_id,
        "asset_kind": "visual_asset",
        "asset_type": request.asset_type,
        "label": request.label.strip(),
        "status": request.review_decision,
        "version": 1,
        "source_node_id": request.source_node_id,
        "supersedes_asset_id": request.supersedes_asset_id.strip() if request.supersedes_asset_id else None,
        "created_at": created_at,
        "image_asset_refs": clean_refs(request.source_image_asset_refs),
        "signature": request.signature.strip(),
        "feature_card": clean_feature_card(request.feature_card),
        "negative_locks": clean_locks(request.negative_locks),
        "promotion_review": _promotion_review(request.review_decision, request.reviewed_at, server_recorded_at),
        "claim_boundary": "fixed_asset_runtime_contract_not_provider_validation",
        "safe_fields_only": True,
        "media_bytes_returned_by_api": False,
        "provider_raw_response_stored": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
    }


def build_video_asset_record(
    *,
    project_id: str,
    asset_id: str,
    request: Any,
    created_at: str,
    server_recorded_at: str,
) -> dict[str, Any]:
    return {
        "artifact_type": "agentflow_video_asset",
        "schema_version": VIDEO_ASSET_SCHEMA_VERSION,
        "project_id": project_id,
        "asset_id": asset_id,
        "asset_kind": "video_asset",
        "asset_type": "video",
        "label": request.label.strip(),
        "status": request.review_decision,
        "version": 1,
        "source_node_id": request.source_node_id,
        "source_video_artifact_id": str(request.source_video_artifact_id).strip(),
        "summary": str(request.summary).strip(),
        "segments": clean_video_segments(request.segments),
        "feature_card": clean_feature_card(request.feature_card),
        "created_at": created_at,
        "promotion_review": _promotion_review(request.review_decision, request.reviewed_at, server_recorded_at),
        "claim_boundary": "video_asset_runtime_contract_not_provider_validation",
        "safe_fields_only": True,
        "media_bytes_returned_by_api": False,
        "provider_raw_response_stored": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
    }


def public_visual_asset(record: dict[str, Any]) -> dict[str, Any]:
    review = record.get("promotion_review") if isinstance(record.get("promotion_review"), dict) else {}
    retirement = record.get("retirement_review") if isinstance(record.get("retirement_review"), dict) else {}
    payload = {
        "asset_id": record.get("asset_id"),
        "asset_type": record.get("asset_type"),
        "label": record.get("label"),
        "status": record.get("status"),
        "version": record.get("version"),
        "signature": record.get("signature"),
        "image_asset_refs": list(record.get("image_asset_refs") or []),
        "source_node_id": record.get("source_node_id"),
        "supersedes_asset_id": record.get("supersedes_asset_id"),
        "created_at": record.get("created_at"),
        "reviewed_at": review.get("reviewed_at"),
        "server_recorded_at": review.get("server_recorded_at"),
    }
    if retirement:
        payload["retired_at"] = retirement.get("retired_at")
        payload["retirement_server_recorded_at"] = retirement.get("server_recorded_at")
    return payload


def public_visual_asset_detail(record: dict[str, Any]) -> dict[str, Any]:
    payload = public_visual_asset(record)
    payload.update(
        {
            "feature_card": dict(record.get("feature_card") or {}),
            "negative_locks": list(record.get("negative_locks") or []),
            "promotion_review": public_review(record.get("promotion_review")),
            "retirement_review": public_review(record.get("retirement_review")),
            "claim_boundary": record.get("claim_boundary"),
            "safe_fields_only": True,
            "media_bytes_returned_by_api": False,
            "provider_raw_response_stored": False,
        }
    )
    return payload


def public_video_asset(record: dict[str, Any]) -> dict[str, Any]:
    review = record.get("promotion_review") if isinstance(record.get("promotion_review"), dict) else {}
    return {
        "asset_id": record.get("asset_id"),
        "asset_kind": "video_asset",
        "asset_type": "video",
        "label": record.get("label"),
        "status": record.get("status"),
        "version": record.get("version"),
        "summary": record.get("summary"),
        "segments": list(record.get("segments") or []),
        "feature_card": dict(record.get("feature_card") or {}),
        "source_node_id": record.get("source_node_id"),
        "source_video_artifact_id": record.get("source_video_artifact_id"),
        "created_at": record.get("created_at"),
        "reviewed_at": review.get("reviewed_at"),
        "server_recorded_at": review.get("server_recorded_at"),
        "safe_fields_only": True,
        "media_bytes_returned_by_api": False,
        "provider_raw_response_stored": False,
    }


def public_review(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    return {
        key: value.get(key)
        for key in ("action", "reviewed_at", "server_recorded_at", "human_confirmed", "claim_boundary", "reason", "retired_at")
        if key in value
    }


def clean_refs(values: list[str]) -> list[str]:
    refs: list[str] = []
    for value in values:
        ref = str(value or "").strip()
        if ref and ref not in refs:
            refs.append(ref)
    return refs


def clean_feature_card(value: dict[str, Any]) -> dict[str, Any]:
    return {str(key): item for key, item in (value or {}).items() if str(key).strip() and item not in (None, "", [], {})}


def clean_locks(values: list[str]) -> list[str]:
    locks: list[str] = []
    for value in values:
        lock = str(value or "").strip()
        if lock and lock not in locks:
            locks.append(lock)
    return locks[:24]


def clean_video_segments(values: list[dict[str, Any]]) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    for index, item in enumerate(values or []):
        if not isinstance(item, dict):
            continue
        segment = {
            "segment_id": str(item.get("segment_id") or f"seg_{index + 1:03d}"),
            "start_time_sec": _non_negative_float(item.get("start_time_sec")),
            "end_time_sec": _non_negative_float(item.get("end_time_sec"), default=5.0),
            "visible_subjects": _string_list(item.get("visible_subjects")),
            "actions": _string_list(item.get("actions")),
            "scene_state": str(item.get("scene_state") or "").strip(),
            "camera_motion": str(item.get("camera_motion") or "").strip(),
            "props": _string_list(item.get("props")),
            "continuity_anchors": _string_list(item.get("continuity_anchors")),
            "drift_risks": _string_list(item.get("drift_risks")),
            "usable_reference_frames": _string_list(item.get("usable_reference_frames")),
        }
        if segment["end_time_sec"] < segment["start_time_sec"]:
            segment["end_time_sec"] = segment["start_time_sec"]
        segments.append(segment)
    return segments


def _promotion_review(action: str, reviewed_at: str, server_recorded_at: str) -> dict[str, Any]:
    return {
        "action": action,
        "reviewed_at": reviewed_at,
        "server_recorded_at": server_recorded_at,
        "human_confirmed": True,
        "claim_boundary": "operator_review_record_not_human_acceptance",
    }


def _human_confirmed(asset: dict[str, Any]) -> bool:
    review = asset.get("promotion_review") if isinstance(asset.get("promotion_review"), dict) else {}
    return review.get("human_confirmed") is True


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        source = value
    else:
        source = [value] if value not in (None, "") else []
    result: list[str] = []
    for item in source:
        text = str(item or "").strip()
        if text and text not in result:
            result.append(text)
    return result[:24]


def _non_negative_float(value: Any, *, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default
    return max(0.0, number)


__all__ = (
    "ALGORITHM_ID",
    "ASSET_STATUSES",
    "EVIDENCE_BOUNDARY",
    "FAILURE_MODES",
    "INPUT_CONTRACT",
    "OUTPUT_CONTRACT",
    "VISUAL_ASSET_SCHEMA_VERSION",
    "VIDEO_ASSET_SCHEMA_VERSION",
    "build_video_asset_record",
    "build_visual_asset_record",
    "clean_feature_card",
    "clean_locks",
    "clean_refs",
    "clean_video_segments",
    "fixed_context_assets",
    "public_review",
    "public_video_asset",
    "public_visual_asset",
    "public_visual_asset_detail",
)
