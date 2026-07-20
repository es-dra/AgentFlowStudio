from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from agentflow_studio.production.manga_first_l4a_compiler import validate_manga_first_manifest
from agentflow_studio.production.manga_first_l4a_schema import ProductionTruthManifest


DEFAULT_PROVIDER_CONFIG = Path("configs/providers.example.json")


def build_manga_first_provider_call_plan(
    manifest_value: ProductionTruthManifest | dict[str, Any],
    *,
    provider_config_path: str | Path = DEFAULT_PROVIDER_CONFIG,
    keyframe_candidates_per_shot: int = 2,
    video_candidates_per_shot: int = 1,
    retry_limit: int = 1,
) -> dict[str, Any]:
    manifest = validate_manga_first_manifest(manifest_value)
    services = _safe_services(provider_config_path)
    image = _service_summary(services, "image_relay")
    video = _service_summary(services, "seedance_i2v")
    shot_count = len(manifest.shots)
    keyframe_calls = shot_count * keyframe_candidates_per_shot
    video_chunks = _video_chunk_count(manifest, supported_durations_sec=video.get("supported_durations_sec"))
    video_calls = video_chunks * video_candidates_per_shot
    return {
        "schema_version": "afs.manga_first_l4b.provider_call_plan.v0.1",
        "provider_dispatch_count": 0,
        "read_only_descriptor_check": True,
        "secret_values_read": False,
        "gates_required": sorted(
            {
                str(image.get("required_gate") or "AFS_ALLOW_REMOTE_IMAGE"),
                str(video.get("required_gate") or "AFS_ALLOW_REMOTE_VIDEO"),
            }
        ),
        "models": {
            "keyframe_image": image,
            "shot_video": video,
        },
        "call_counts": {
            "shot_count": shot_count,
            "keyframe_candidates_per_shot": keyframe_candidates_per_shot,
            "image_calls": keyframe_calls,
            "video_candidates_per_shot": video_candidates_per_shot,
            "video_chunks": video_chunks,
            "video_calls": video_calls,
            "max_retry_limit_per_call": retry_limit,
            "max_attempted_calls_with_retries": (keyframe_calls + video_calls) * (1 + retry_limit),
        },
        "charge_fingerprint": {
            "basis": "project_id + manifest_sha256 + stage + shot_id + capability + prompt_sha256",
            "retry_reuses_original_fingerprint": True,
            "completed_shot_repurchase_allowed": False,
        },
        "cost": {
            "status": "ESTIMATE_OWNER_DECISION_NEEDED",
            "local_authoritative_pricing_found": False,
            "currency": "OWNER_DECISION_NEEDED",
            "estimated_cost_range": "OWNER_DECISION_NEEDED",
            "recommended_hard_cap": "OWNER_COST_CAP_NEEDED_AFTER_OWNER_PRICE_CONFIRMATION",
            "reason": "configs/providers.example.json contains cost_hint/cost_estimate metadata but no authoritative unit price.",
        },
        "non_claims": [
            "provider_smoke_not_run",
            "pricing_not_confirmed_from_local_authority",
            "no_secret_read_or_output",
        ],
    }


def _safe_services(provider_config_path: str | Path) -> dict[str, Any]:
    path = Path(provider_config_path)
    if not path.is_absolute():
        path = Path.cwd() / path
    payload = json.loads(path.read_text(encoding="utf-8"))
    services = payload.get("services") if isinstance(payload, dict) else {}
    return services if isinstance(services, dict) else {}


def _service_summary(services: dict[str, Any], service_id: str) -> dict[str, Any]:
    service = services.get(service_id) if isinstance(services.get(service_id), dict) else {}
    descriptor = service.get("descriptor") if isinstance(service.get("descriptor"), dict) else {}
    return {
        "service_id": service_id,
        "provider": str(service.get("provider") or ""),
        "capability": str(service.get("capability") or descriptor.get("modality") or ""),
        "model": str(service.get("model") or "server-configured"),
        "required_gate": str(service.get("required_gate") or descriptor.get("required_gate") or ""),
        "execution_mode": str(descriptor.get("execution_mode") or ""),
        "prompt_char_limit": descriptor.get("prompt_char_limit"),
        "reference_image_slots": descriptor.get("reference_image_slots"),
        "supported_durations_sec": descriptor.get("supported_durations_sec") or [],
        "supported_resolutions": descriptor.get("supported_resolutions") or [],
        "cost_hint_present": bool(descriptor.get("cost_hint") or descriptor.get("cost_estimate")),
        "credential_env_present": _credential_env_present(service),
    }


def _credential_env_present(service: dict[str, Any]) -> bool:
    env_name = str(service.get("credential_env") or service.get("api_key_env") or "")
    if not env_name:
        return False
    return env_name in os.environ


def _video_chunk_count(manifest: ProductionTruthManifest, *, supported_durations_sec: Any = None) -> int:
    supported = [
        int(item)
        for item in (supported_durations_sec or [])
        if isinstance(item, (int, float)) and int(item) > 0
    ] or [10]
    count = 0
    for shot in manifest.shots:
        duration = float(shot["duration_seconds"])
        max_duration = max(supported)
        chunks = int(duration // max_duration)
        if duration % max_duration:
            chunks += 1
        count += max(1, chunks)
    return count
