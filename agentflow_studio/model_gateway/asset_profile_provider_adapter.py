from __future__ import annotations

from pathlib import Path
from typing import Any

from agentflow.memory.production_asset_profile_constants import PROVIDER_VALIDATION_RESULT_KIND
from agentflow.memory.production_loop import SCHEMA_VERSION


def run_asset_profile_provider_validation(
    seed: dict[str, Any],
    *,
    provider_config_path: Path | None,
    character_reference_image_path: Path | None,
    image_service: str,
    video_service: str,
) -> dict[str, Any]:
    _ = (seed, provider_config_path, character_reference_image_path, image_service, video_service)
    return {
        "kind": PROVIDER_VALIDATION_RESULT_KIND,
        "artifact_type": PROVIDER_VALIDATION_RESULT_KIND,
        "schema_version": SCHEMA_VERSION,
        "status": "blocked",
        "provider_calls_started": False,
        "blockers": [
            {
                "blocker_id": "legacy_asset_profile_provider_adapter_removed",
                "message": "Image provider validation now runs through Studio Runtime.",
            }
        ],
        "claim_boundary": "provider_smoke_only_not_human_acceptance",
        "writes_long_term_memory": False,
        "writes_company_kb": False,
    }


__all__ = ("run_asset_profile_provider_validation",)
