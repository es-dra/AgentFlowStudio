from __future__ import annotations

from typing import Any

from agentflow.algorithms.model_call_context import sanitize_context_payload, sanitize_context_text


ALGORITHM_ID = "afs.visual_understanding.v0.1"
INPUT_CONTRACT = "safe media refs, provider or local vision observation, project need, target asset types"
OUTPUT_CONTRACT = "normalized project-relevant visual observation for draft asset cards"
FAILURE_MODES = ("missing_safe_ref", "unsupported_asset_type", "unsafe_provider_observation_redacted")
EVIDENCE_BOUNDARY = "normalized observation remains draft evidence and cannot write fixed assets"

ASSET_TYPES = {"character", "scene", "video"}


def normalize_visual_observation(
    *,
    project_id: str,
    observation_id: str,
    source_refs: dict[str, Any],
    provider_observation: dict[str, Any],
    project_need: dict[str, Any],
) -> dict[str, Any]:
    requested = [str(item) for item in (project_need.get("asset_types") or []) if str(item) in ASSET_TYPES]
    labels = [str(item) for item in (provider_observation.get("labels") or []) if str(item) in ASSET_TYPES]
    selected = requested or labels
    payload = {
        "artifact_type": "agentflow_visual_understanding_observation",
        "schema_version": "afs_visual_understanding_observation.v0.1",
        "algorithm_id": ALGORITHM_ID,
        "project_id": project_id,
        "observation_id": observation_id,
        "source_refs": {
            "image_asset_refs": _clean_refs(source_refs.get("image_asset_refs") or []),
            "video_artifact_id": sanitize_context_text(source_refs.get("video_artifact_id")),
        },
        "normalized_observation": {
            "description": sanitize_context_text(provider_observation.get("description")),
            "safe_labels": labels,
        },
        "project_relevance": {
            "focus": sanitize_context_text(project_need.get("focus")),
            "selected_asset_types": selected,
            "selection_reason": "project_need_asset_types_then_safe_provider_labels",
        },
        "safe_evidence": {
            "image_asset_ref_count": len(source_refs.get("image_asset_refs") or []),
            "has_video_artifact_ref": bool(source_refs.get("video_artifact_id")),
            "provider_raw_response_stored": False,
            "media_bytes_returned_by_api": False,
        },
        "asset_card_policy": {
            "default_status": "draft",
            "writes_fixed_asset": False,
            "requires_human_confirmation": True,
            "included_in_context_before_confirmation": False,
        },
        "safety_boundary": {
            "no_provider_raw": True,
            "no_local_path": True,
            "no_credentialed_url": True,
            "no_media_bytes": True,
        },
    }
    return sanitize_context_payload(payload)


def _clean_refs(values: list[Any]) -> list[str]:
    result: list[str] = []
    for value in values:
        ref = sanitize_context_text(value).strip()
        if ref and ref not in result:
            result.append(ref)
    return result


__all__ = (
    "ALGORITHM_ID",
    "ASSET_TYPES",
    "EVIDENCE_BOUNDARY",
    "FAILURE_MODES",
    "INPUT_CONTRACT",
    "OUTPUT_CONTRACT",
    "normalize_visual_observation",
)
