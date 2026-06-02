from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from agentflow.harness.constants import AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS
from agentflow.memory.production_asset_profile_constants import (
    PROVIDER_VALIDATION_PLAN_KIND,
    PROVIDER_VALIDATION_RESULT_KIND,
)
from agentflow.memory.production_loop import SCHEMA_VERSION
from agentflow_studio.model_gateway.company_secrets import COMPANY_PROVIDER_CONFIG_ENV


def build_provider_validation_plan(
    seed: dict[str, Any],
    *,
    generated_at: str,
    run_provider_validation: bool,
    provider_config_path: Path | None,
    project_materials_path: Path | None,
    character_reference_image_path: Path | None,
    image_service: str,
    video_service: str,
) -> dict[str, Any]:
    return {
        "kind": PROVIDER_VALIDATION_PLAN_KIND,
        "artifact_type": PROVIDER_VALIDATION_PLAN_KIND,
        "schema_version": SCHEMA_VERSION,
        "plan_id": f"asset-provider-validation:{seed.get('seed_id', 'unknown')}",
        "generated_at": generated_at,
        "run_provider_validation": run_provider_validation,
        "image_service": image_service,
        "video_service": video_service,
        "required_gates": ["AFS_ALLOW_REMOTE_IMAGE", "AFS_ALLOW_REMOTE_VIDEO"],
        "local_inputs": {
            "project_materials_provided": project_materials_path is not None,
            "character_reference_image_provided": character_reference_image_path is not None,
            "provider_config_provided": provider_config_path is not None or bool(os.environ.get(COMPANY_PROVIDER_CONFIG_ENV)),
            "raw_paths_persisted": False,
        },
        "prompts": {
            "image_prompt": str(_dict(seed.get("provider_validation")).get("image_prompt", "")),
            "video_prompt": str(_dict(seed.get("provider_validation")).get("video_prompt", "")),
        },
        "claim_boundary": "optional_provider_smoke_not_core_milestone",
        "writes_long_term_memory": False,
        "writes_company_kb": False,
    }


def provider_validation_blockers(
    provider_plan: dict[str, Any],
    *,
    provider_config_path: Path | None,
    character_reference_image_path: Path | None,
    image_service: str,
) -> list[dict[str, str]]:
    if provider_plan.get("run_provider_validation") is not True:
        return [_blocker("provider_validation_not_requested", "provider validation was not requested")]
    blockers: list[dict[str, str]] = []
    if not _env_gate_enabled("AFS_ALLOW_REMOTE_IMAGE"):
        blockers.append(_blocker("image_gate_unset", "set AFS_ALLOW_REMOTE_IMAGE=true for live image smoke"))
    if not _env_gate_enabled("AFS_ALLOW_REMOTE_VIDEO"):
        blockers.append(_blocker("video_gate_unset", "set AFS_ALLOW_REMOTE_VIDEO=true for live video smoke"))
    if provider_config_path is None and not os.environ.get(COMPANY_PROVIDER_CONFIG_ENV):
        blockers.append(_blocker("provider_config_missing", "provide --provider-config or AFS_PROVIDER_CONFIG"))
    if character_reference_image_path is None:
        blockers.append(_blocker("character_reference_image_missing", "provide a local ignored character reference image"))
    if image_service == "gpt_image2":
        blockers.append(_blocker("gpt_image2_adapter_unavailable", "GPT Image2 is not wired as a verified AFS smoke adapter"))
    elif image_service != "minimax_image":
        blockers.append(_blocker("image_adapter_unavailable", f"unsupported image service for this package: {image_service}"))
    return blockers


def run_provider_validation(
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
    try:
        from agentflow_studio.model_gateway.company_secrets import load_company_provider_secrets
        from agentflow_studio.model_gateway.kling_video_smoke import run_kling_i2v_smoke
        from agentflow_studio.model_gateway.minimax_image_smoke import run_minimax_image_smoke

        store = load_company_provider_secrets(provider_config_path)
        prompts = _dict(seed.get("provider_validation"))
        image_manifest = run_minimax_image_smoke(
            store,
            service_id=image_service,
            prompt=str(prompts.get("image_prompt") or "Sanitized character consistency keyframe prompt."),
            output_dir=image_output,
            subject_reference_image_path=character_reference_image_path,
        )
        source_image = image_output / str(_list(image_manifest.get("outputs"))[0].get("image_path"))
        video_manifest = run_kling_i2v_smoke(
            store,
            service_id=video_service,
            prompt=str(prompts.get("video_prompt") or "Sanitized scene continuity image-to-video prompt."),
            image_path=source_image,
            output_dir=video_output,
        )
    except Exception as exc:
        safe_error = _safe_error(exc)
        return {
            "kind": PROVIDER_VALIDATION_RESULT_KIND,
            "artifact_type": PROVIDER_VALIDATION_RESULT_KIND,
            "schema_version": SCHEMA_VERSION,
            "status": "failed",
            "provider_calls_started": True,
            "safe_error": safe_error,
            "blockers": [_blocker("provider_validation_failed", safe_error)],
        }
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


def provider_status(plan: dict[str, Any], blockers: list[dict[str, str]]) -> str:
    if plan.get("run_provider_validation") is not True:
        return "not_requested"
    return "blocked" if blockers else "ready_to_run_or_succeeded"


def _safe_error(exc: Exception) -> str:
    text = str(exc)
    if _has_private_fragment(text):
        return "provider validation failed; details withheld because the error included private fragments"
    return text[:240]


def _has_private_fragment(payload: Any) -> bool:
    raw_text = str(payload).lower()
    return any(fragment.lower() in raw_text for fragment in AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS)


def _env_gate_enabled(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _blocker(blocker_id: str, message: str) -> dict[str, str]:
    return {"blocker_id": blocker_id, "message": message}


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


__all__ = (
    "build_provider_validation_plan",
    "provider_status",
    "provider_validation_blockers",
    "run_provider_validation",
)
