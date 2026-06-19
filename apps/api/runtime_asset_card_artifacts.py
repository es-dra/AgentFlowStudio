from __future__ import annotations

from pathlib import Path
from typing import Any

from agentflow.harness.json_io import write_json
from apps.api.runtime_models import AssetCardDraftRequest
from apps.api.runtime_store import RuntimeStore, reject_unsafe_payload


def write_asset_card_artifacts(
    store: RuntimeStore,
    output_dir: Path,
    *,
    safe_manifest: dict[str, Any],
    draft: dict[str, Any] | None,
    model_call_context: dict[str, Any],
    model_request_plan: dict[str, Any],
    visual_observation: dict[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    reject_unsafe_payload(safe_manifest)
    reject_unsafe_payload(model_call_context)
    reject_unsafe_payload(model_request_plan)
    write_json(output_dir / "asset_card_draft_safe_manifest.json", safe_manifest)
    write_json(output_dir / "model_call_context.json", model_call_context)
    write_json(output_dir / "model_request_plan.json", model_request_plan)
    artifacts = {
        "asset_card_draft_safe_manifest": store.register_artifact(
            output_dir / "asset_card_draft_safe_manifest.json",
            role="asset_card_draft_safe_manifest",
        ),
        "model_call_context": store.register_artifact(output_dir / "model_call_context.json", role="model_call_context"),
        "model_request_plan": store.register_artifact(output_dir / "model_request_plan.json", role="model_request_plan"),
    }
    if visual_observation is not None:
        reject_unsafe_payload(visual_observation)
        write_json(output_dir / "visual_understanding_observation.json", visual_observation)
        artifacts["visual_understanding_observation"] = store.register_artifact(
            output_dir / "visual_understanding_observation.json",
            role="visual_understanding_observation",
        )
    if draft is not None:
        reject_unsafe_payload(draft)
        write_json(output_dir / "asset_card_draft.json", draft)
        artifacts["asset_card_draft"] = store.register_artifact(output_dir / "asset_card_draft.json", role="asset_card_draft")
    return artifacts


def draft_input_refs(request: AssetCardDraftRequest) -> list[dict[str, str]]:
    refs = [
        {"role": "asset_type", "ref": request.asset_type},
        {"role": "node_id", "ref": request.node_id or "not_provided"},
        {"role": "provider_service_id", "ref": request.provider_service_id},
    ]
    refs.extend({"role": "source_image_asset_ref", "ref": item} for item in request.source_image_asset_refs)
    refs.extend({"role": "sampled_image_asset_ref", "ref": item} for item in request.sampled_image_asset_refs)
    if request.source_video_artifact_id:
        refs.append({"role": "source_video_artifact_id", "ref": request.source_video_artifact_id})
    return refs


def vision_gate_state(value: str) -> dict[str, str]:
    return {
        "remote_llm": "blocked_by_default",
        "remote_asr": "blocked_by_default",
        "remote_image": "blocked_by_default",
        "remote_video": "blocked_by_default",
        "remote_vision": value,
    }


__all__ = (
    "draft_input_refs",
    "vision_gate_state",
    "write_asset_card_artifacts",
)
