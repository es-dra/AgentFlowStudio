from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from agentflow.harness.constants import AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS
from agentflow.memory.production_asset_profile_constants import (
    PROVIDER_VALIDATION_PLAN_KIND,
    PROVIDER_VALIDATION_RESULT_KIND,
)
from agentflow.memory.production_loop import SCHEMA_VERSION


PROVIDER_CONFIG_ENV = "AFS_PROVIDER_CONFIG"
ProviderValidationExecutor = Callable[..., dict[str, Any]]


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
            "provider_config_provided": provider_config_path is not None or bool(os.environ.get(PROVIDER_CONFIG_ENV)),
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
    if provider_config_path is None and not os.environ.get(PROVIDER_CONFIG_ENV):
        blockers.append(_blocker("provider_config_missing", "provide --provider-config or AFS_PROVIDER_CONFIG"))
    if character_reference_image_path is None:
        blockers.append(_blocker("character_reference_image_missing", "provide a local ignored character reference image"))
    if image_service == "codex_image":
        blockers.append(
            _blocker(
                "codex_image_legacy_smoke_unavailable",
                "Codex image validation now runs through Studio Runtime, not this legacy asset package.",
            )
        )
    else:
        blockers.append(_blocker("image_adapter_unavailable", f"unsupported image service for this package: {image_service}"))
    return blockers


def run_provider_validation(
    seed: dict[str, Any],
    *,
    provider_config_path: Path | None,
    character_reference_image_path: Path | None,
    image_service: str,
    video_service: str,
    provider_validation_executor: ProviderValidationExecutor | None = None,
) -> dict[str, Any]:
    if provider_validation_executor is None:
        return {
            "kind": PROVIDER_VALIDATION_RESULT_KIND,
            "artifact_type": PROVIDER_VALIDATION_RESULT_KIND,
            "schema_version": SCHEMA_VERSION,
            "status": "blocked",
            "provider_calls_started": False,
            "blockers": [
                _blocker(
                    "provider_adapter_unregistered",
                    "live provider validation requires an injected provider adapter",
                )
            ],
            "writes_long_term_memory": False,
            "writes_company_kb": False,
        }
    try:
        result = provider_validation_executor(
            seed,
            provider_config_path=provider_config_path,
            character_reference_image_path=character_reference_image_path,
            image_service=image_service,
            video_service=video_service,
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
    if not isinstance(result, dict):
        return {
            "kind": PROVIDER_VALIDATION_RESULT_KIND,
            "artifact_type": PROVIDER_VALIDATION_RESULT_KIND,
            "schema_version": SCHEMA_VERSION,
            "status": "failed",
            "provider_calls_started": True,
            "safe_error": "provider validation adapter returned a non-object result",
            "blockers": [_blocker("provider_validation_failed", "provider validation adapter returned a non-object result")],
        }
    normalized = dict(result)
    normalized.setdefault("kind", PROVIDER_VALIDATION_RESULT_KIND)
    normalized.setdefault("artifact_type", PROVIDER_VALIDATION_RESULT_KIND)
    normalized.setdefault("schema_version", SCHEMA_VERSION)
    normalized.setdefault("status", "succeeded")
    normalized.setdefault("provider_calls_started", True)
    normalized.setdefault("writes_long_term_memory", False)
    normalized.setdefault("writes_company_kb", False)
    return normalized


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
    "PROVIDER_CONFIG_ENV",
    "ProviderValidationExecutor",
    "build_provider_validation_plan",
    "provider_status",
    "provider_validation_blockers",
    "run_provider_validation",
)
