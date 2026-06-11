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
            "import_project",
            "export_project",
            "read_project_manifest",
            "read_artifact",
            "register_source_asset",
            "register_content_card",
            "draft_canvas",
            "update_scene_inspector",
            "record_review_decision",
            "asset_test_run",
            "two_round_validate",
            "record_feedback",
            "provider_validation_plan",
            "keyframe_generation",
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
                "run_provider_preflight",
            ],
            "provider_default": "gated",
        },
        "statuses": ["queued", "running", "succeeded", "failed", "blocked", "cancelled"],
        "safe_ref_policy": "frontend receives artifact_id and summaries, not private local paths",
    }


__all__ = ("runtime_capabilities_payload", "runtime_health_payload")
