from __future__ import annotations

from typing import Any


def runtime_health_payload() -> dict[str, Any]:
    return {
        "service": "agentflow_runtime_service",
        "status": "ready",
        "service_version": "0.2.0",
        "schema_version": "0.1.0",
        "runtime_root_persisted": False,
        "boundaries": {
            "local_only": True,
            "no_database": True,
            "no_account_system": True,
            "no_browser_persistence": True,
            "no_provider_call_by_default": True,
            "no_durable_memory_write": True,
        },
    }


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
            "visual_asset_register",
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


__all__ = ("runtime_capabilities_payload", "runtime_health_payload")
