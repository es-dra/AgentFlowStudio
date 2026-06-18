from __future__ import annotations

import os
from typing import Any


TRUE_VALUES = {"1", "true", "yes", "on"}


def runtime_health_payload(studio_static: dict[str, Any] | None = None) -> dict[str, Any]:
    auth_required = runtime_auth_required()
    return {
        "service": "agentflow_runtime_service",
        "status": "ready",
        "service_version": "0.2.0",
        "schema_version": "0.1.0",
        "runtime_root_persisted": False,
        "studio_static": studio_static or {
            "mounted": False,
            "root_exists": False,
            "index_exists": False,
            "entry_js_exists": False,
            "status": "missing",
        },
        "provider_gates": runtime_provider_gates(),
        "auth_required": auth_required,
        "boundaries": {
            "local_only": True,
            "no_database": True,
            "no_account_system": not auth_required,
            "no_browser_persistence": True,
            "no_provider_call_by_default": True,
            "no_durable_memory_write": True,
        },
    }


def runtime_provider_gates(env: dict[str, str] | None = None) -> dict[str, bool]:
    source = env if env is not None else os.environ
    return {
        "llm": _enabled(source.get("AFS_ALLOW_REMOTE_LLM")),
        "image": _enabled(source.get("AFS_ALLOW_REMOTE_IMAGE")),
        "video": _enabled(source.get("AFS_ALLOW_REMOTE_VIDEO")),
        "asr": _enabled(source.get("AFS_ALLOW_REMOTE_ASR")),
        "vision": _enabled(source.get("AFS_ALLOW_REMOTE_VISION")),
        "external_download": _enabled(source.get("AFS_ALLOW_EXTERNAL_DOWNLOAD")),
    }


def runtime_auth_required(env: dict[str, str] | None = None) -> bool:
    source = env if env is not None else os.environ
    return _enabled(source.get("AFS_AUTH_ENABLED"))


def _enabled(value: str | None) -> bool:
    return str(value or "").strip().lower() in TRUE_VALUES


def runtime_capabilities_payload() -> dict[str, Any]:
    return {
        "actions": [
            "create_project",
            "list_projects",
            "read_project_manifest",
            "read_artifact",
            "read_job",
            "record_feedback",
            "prompt_optimization",
            "script_draft_plan",
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


__all__ = ("runtime_auth_required", "runtime_capabilities_payload", "runtime_health_payload", "runtime_provider_gates")
