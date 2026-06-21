from __future__ import annotations

from pathlib import Path
from typing import Any

from agentflow_studio.model_gateway.provider_adapter import ProviderDispatchRequest, load_provider_registry
from apps.api.runtime_image_assets import resolve_reference_images
from apps.api.runtime_models import AssetCardDraftRequest
from apps.api.runtime_store import RuntimeStore


def normalize_asset_card_provider_service(request: AssetCardDraftRequest) -> None:
    service_id = str(request.provider_service_id or "").strip()
    if request.asset_type == "video" and service_id in {"", "fake_vision", "vision_image"}:
        request.provider_service_id = "vision_video"
    elif request.asset_type in {"character", "scene", "prop"} and service_id in {"", "fake_vision"}:
        request.provider_service_id = "vision_image"


def dispatch_visual_inspection(
    store: RuntimeStore,
    project_id: str,
    request: AssetCardDraftRequest,
    output_dir: Path,
) -> dict[str, Any]:
    image_refs = [*request.source_image_asset_refs, *request.sampled_image_asset_refs]
    reference_images = resolve_reference_images(store, project_id, image_refs, limit=8)
    registry = load_provider_registry()
    return registry.dispatch(
        "vision",
        request.provider_service_id,
        ProviderDispatchRequest(
            prompt=_vision_provider_prompt(request),
            output_dir=output_dir,
            task_type=f"asset_card_draft:{request.asset_type}",
            reference_image_paths=tuple(item["path"] for item in reference_images),
        ),
    )


def provider_observation_for_asset_card(
    request: AssetCardDraftRequest,
    provider_result: dict[str, Any],
) -> dict[str, Any]:
    observation = provider_result.get("provider_observation") if isinstance(provider_result.get("provider_observation"), dict) else {}
    labels = [str(item) for item in observation.get("labels") or [] if str(item)]
    if request.asset_type not in labels:
        labels.append(request.asset_type)
    description = str(observation.get("description") or observation.get("summary") or request.prompt_text)
    result = {
        "description": description,
        "summary": str(observation.get("summary") or description),
        "labels": labels,
    }
    if isinstance(observation.get("feature_card"), dict):
        result["feature_card"] = observation["feature_card"]
    if isinstance(observation.get("segments"), list):
        result["segments"] = observation["segments"]
    return result


def draft_prompt_from_observation(request: AssetCardDraftRequest, observation: dict[str, Any]) -> str:
    parts = [
        str(observation.get("summary") or "").strip(),
        str(observation.get("description") or "").strip(),
        request.prompt_text.strip(),
    ]
    text = " ".join(part for part in parts if part)
    return text[:2000] or request.prompt_text


def vision_provider_constraints(request: AssetCardDraftRequest, gate: dict[str, Any]) -> dict[str, Any]:
    return {
        "capability": "vision",
        "provider_gate": gate.get("required_gate") or "AFS_ALLOW_REMOTE_VISION",
        "provider_gate_status": gate.get("status") or "unknown",
        "provider_service_id": request.provider_service_id,
        "accepted_asset_types": ["character", "scene", "prop", "video"],
        "mode": "visual_inspect",
    }


def _vision_provider_prompt(request: AssetCardDraftRequest) -> str:
    media = "video" if request.asset_type == "video" else "image"
    return "\n".join(
        [
            "AFS visual asset drafting request.",
            f"Asset type: {request.asset_type}",
            f"Media kind: {media}",
            f"User/project note: {request.prompt_text}",
            "Return JSON with observation.description, observation.summary, observation.labels, and optional feature_card or segments.",
            "Do not include local paths, signed URLs, credentials, raw provider payloads, or media bytes.",
        ]
    )


__all__ = (
    "dispatch_visual_inspection",
    "draft_prompt_from_observation",
    "normalize_asset_card_provider_service",
    "provider_observation_for_asset_card",
    "vision_provider_constraints",
)
