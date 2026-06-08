from __future__ import annotations

from pathlib import Path
from typing import Any

from agentflow.memory.production_asset_profile_constants import PROVIDER_VALIDATION_RESULT_KIND
from agentflow.memory.production_loop import SCHEMA_VERSION
from agentflow_studio.model_gateway.company_secrets import load_company_provider_secrets
from agentflow_studio.model_gateway.kling_video_smoke import run_kling_i2v_smoke
from agentflow_studio.model_gateway.minimax_image_smoke import run_minimax_image_smoke


def run_asset_profile_provider_validation(
    seed: dict[str, Any],
    *,
    provider_config_path: Path | None,
    character_reference_image_path: Path | None,
    image_service: str,
    video_service: str,
) -> dict[str, Any]:
    output_root = Path("data/processed/runs/production_memory_loop/asset_provider_validation")
    image_output = output_root / "image"
    video_output = output_root / "video"
    store = load_company_provider_secrets(provider_config_path)
    prompts = _dict(seed.get("provider_validation"))
    image_manifest = run_minimax_image_smoke(
        store,
        service_id=image_service,
        prompt=str(prompts.get("image_prompt") or "Sanitized character consistency keyframe prompt."),
        output_dir=image_output,
        subject_reference_image_path=character_reference_image_path,
    )
    source_image = image_output / str(_dict(_list(image_manifest.get("outputs"))[0]).get("image_path"))
    video_manifest = run_kling_i2v_smoke(
        store,
        service_id=video_service,
        prompt=str(prompts.get("video_prompt") or "Sanitized scene continuity image-to-video prompt."),
        image_path=source_image,
        output_dir=video_output,
    )
    return {
        "kind": PROVIDER_VALIDATION_RESULT_KIND,
        "artifact_type": PROVIDER_VALIDATION_RESULT_KIND,
        "schema_version": SCHEMA_VERSION,
        "status": "succeeded",
        "provider_calls_started": True,
        "image_manifest_ref": "provider_validation/image/minimax_image_smoke_manifest.json",
        "video_manifest_ref": "provider_validation/video/kling_i2v_smoke_manifest.json",
        "image_status": str(image_manifest.get("status", "unknown")),
        "video_status": str(video_manifest.get("status", "unknown")),
        "claim_boundary": "provider_smoke_only_not_human_acceptance",
        "writes_long_term_memory": False,
        "writes_company_kb": False,
    }


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


__all__ = ("run_asset_profile_provider_validation",)
