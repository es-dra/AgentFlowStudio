from __future__ import annotations

import os
from pathlib import Path
from typing import Any


TRUE_VALUES = {"1", "true", "yes", "on"}
LOCAL_BIND_HOSTS = {"", "127.0.0.1", "localhost", "::1"}
DEFAULT_RUNTIME_BIND_HOST = "127.0.0.1"
READINESS_NON_CLAIMS = [
    "not_public_edge_verified",
    "not_runtime_loaded_code_freshness",
    "not_provider_smoke",
    "not_generated_media_qa",
    "not_human_creative_acceptance",
    "not_product_or_business_readiness",
    "not_public_or_legal_readiness",
]


def runtime_health_payload(
    *,
    runtime_root: str | os.PathLike[str] | None = None,
    studio_static: dict[str, Any] | None = None,
    runtime_bind_host: str | None = None,
) -> dict[str, Any]:
    auth_required = runtime_auth_required()
    exposure = runtime_exposure_payload(runtime_bind_host=runtime_bind_host, auth_required=auth_required)
    return {
        "service": "agentflow_runtime_service",
        "status": "ready",
        "service_health": {
            "status": "ready",
            "scope": "process_health_only",
            "claims_acceptance_ready": False,
        },
        "service_version": "0.2.0",
        "schema_version": "0.1.0",
        "runtime_root_persisted": runtime_root_is_persisted(runtime_root),
        "studio_static": studio_static or {
            "mounted": False,
            "root_exists": False,
            "index_exists": False,
            "entry_js_exists": False,
            "status": "missing",
        },
        "provider_gates": runtime_provider_gates(),
        "auth_required": auth_required,
        "exposure": exposure,
        "readiness": runtime_readiness_payload(auth_required=auth_required, exposure=exposure),
        "boundaries": {
            "local_only": exposure["local_only"],
            "public_bind": exposure["public_bind"],
            "public_edge_verified": False,
            "no_database": True,
            "no_account_system": not auth_required,
            "no_browser_persistence": True,
            "no_provider_call_by_default": True,
            "no_durable_memory_write": True,
            "runtime_loaded_code_freshness_claim": "not_claimed",
            "acceptance_ready": False,
            "product_readiness": False,
        },
    }


def runtime_provider_gates(env: dict[str, str] | None = None) -> dict[str, bool]:
    source = env if env is not None else os.environ
    return {
        "llm": _enabled(source.get("AFS_ALLOW_REMOTE_LLM")),
        "image": _enabled(source.get("AFS_ALLOW_REMOTE_IMAGE")),
        "video": _enabled(source.get("AFS_ALLOW_REMOTE_VIDEO")),
        "audio": _enabled(source.get("AFS_ALLOW_REMOTE_AUDIO")),
        "asr": _enabled(source.get("AFS_ALLOW_REMOTE_ASR")),
        "vision": _enabled(source.get("AFS_ALLOW_REMOTE_VISION")),
        "external_download": _enabled(source.get("AFS_ALLOW_EXTERNAL_DOWNLOAD")),
    }


def runtime_auth_required(env: dict[str, str] | None = None) -> bool:
    source = env if env is not None else os.environ
    return _enabled(source.get("AFS_AUTH_ENABLED"))


def runtime_exposure_payload(*, runtime_bind_host: str | None = None, auth_required: bool | None = None) -> dict[str, Any]:
    host = _safe_bind_host(runtime_bind_host or os.environ.get("AFS_RUNTIME_SERVICE_HOST") or DEFAULT_RUNTIME_BIND_HOST)
    public_bind = _is_public_bind_host(host)
    auth_on = runtime_auth_required() if auth_required is None else bool(auth_required)
    if public_bind and not auth_on:
        claim_status = "public_bind_without_runtime_auth"
    elif public_bind:
        claim_status = "public_bind_requires_public_edge_gate"
    else:
        claim_status = "local_bind_only"
    return {
        "bind_host": host,
        "local_only": not public_bind,
        "public_bind": public_bind,
        "auth_required": auth_on,
        "public_edge_verified": False,
        "claim_status": claim_status,
    }


def runtime_readiness_payload(*, auth_required: bool, exposure: dict[str, Any]) -> dict[str, Any]:
    blocked_or_unverified = [
        "public_edge_not_verified_by_health",
        "runtime_loaded_code_freshness_requires_restart_or_reload_evidence",
        "provider_smoke_not_run_by_health",
        "generated_media_qa_not_run_by_health",
        "human_creative_acceptance_not_claimed",
        "product_business_public_legal_readiness_not_claimed",
    ]
    if not auth_required:
        blocked_or_unverified.insert(0, "runtime_auth_disabled")
    if exposure.get("public_bind") and not auth_required:
        blocked_or_unverified.insert(0, "public_bind_runtime_auth_disabled")
    return {
        "service_ready": True,
        "auth_ready_for_public_edge": bool(auth_required),
        "public_edge_verified": False,
        "runtime_three_end_alignment_evidence": False,
        "runtime_loaded_code_freshness_claim": "not_claimed",
        "acceptance_ready": False,
        "human_creative_acceptance": False,
        "product_readiness": False,
        "business_validation": False,
        "claim_boundary": "Service health only; public edge auth, runtime loaded-code freshness, provider smoke, generated-media QA, human creative acceptance, and product/business/public/legal readiness are not claimed.",
        "blocked_or_unverified": blocked_or_unverified,
        "non_claims": list(READINESS_NON_CLAIMS),
    }


def runtime_root_is_persisted(runtime_root: str | os.PathLike[str] | None) -> bool:
    if runtime_root is None:
        return False
    root = Path(runtime_root)
    if not root.is_absolute():
        return False
    try:
        root.resolve().relative_to(Path.cwd().resolve())
        return False
    except ValueError:
        return True


def _enabled(value: str | None) -> bool:
    return str(value or "").strip().lower() in TRUE_VALUES


def _safe_bind_host(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return DEFAULT_RUNTIME_BIND_HOST
    if "/" in text or "\\" in text or len(text) > 80:
        return "unsafe_or_invalid_host"
    return text


def _is_public_bind_host(value: str) -> bool:
    host = str(value or "").strip().lower()
    return host not in LOCAL_BIND_HOSTS


def runtime_capabilities_payload() -> dict[str, Any]:
    return {
        "actions": [
            "create_project",
            "list_projects",
            "read_project_manifest",
            "read_artifact",
            "read_job",
            "record_feedback",
            "company_os_gfr_projection",
            "prompt_optimization",
            "script_draft_plan",
            "storyboard_breakdown",
            "image_asset_upload",
            "asset_card_draft",
            "visual_asset_register",
            "video_asset_register",
            "keyframe_generation",
            "video_generation",
            "generation_comparison",
            "studio_state",
            "export_openapi_schema",
        ],
        "studio_flow": {
            "target_status": "ready_for_next_round",
            "actions": [
                "add_reference",
                "draft_canvas",
                "start_first_generation_check",
                "record_review_note",
                "start_next_round",
                "request_gated_generation",
            ],
            "provider_default": "gated",
        },
        "statuses": ["queued", "running", "succeeded", "failed", "blocked", "cancelled"],
        "safe_ref_policy": "frontend receives artifact_id and summaries, not private local paths",
    }


__all__ = (
    "runtime_auth_required",
    "runtime_capabilities_payload",
    "runtime_exposure_payload",
    "runtime_health_payload",
    "runtime_provider_gates",
    "runtime_readiness_payload",
    "runtime_root_is_persisted",
)
