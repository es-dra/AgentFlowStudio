from __future__ import annotations

from typing import Any

from apps.api.runtime_store import RuntimeStore, project_summary
from apps.api.runtime_workbench_activity import build_activity_timeline
from apps.api.runtime_workbench_assets import build_asset_library
from apps.api.runtime_workbench_board import build_production_board
from apps.api.runtime_workbench_commands import build_command_hub
from apps.api.runtime_workbench_creation import build_creation_workspace
from apps.api.runtime_workbench_content import build_filmstrip
from apps.api.runtime_workbench_jobs import build_job_center
from apps.api.runtime_workbench_project_hub import build_project_hub
from apps.api.runtime_workbench_readiness import build_project_readiness
from apps.api.runtime_workbench_review import build_review_room
from apps.api.runtime_workbench_style import build_style_memory
from apps.api.runtime_workbench_cards import (
    NAVIGATION,
    NON_CLAIMS,
    SAFE_REF_POLICY,
    build_workbench_cards,
    build_workbench_events,
)


def build_workbench_state(store: RuntimeStore, project_id: str) -> dict[str, Any]:
    manifest = store.ensure_project_manifest(project_id)
    manifest_artifact = store.register_artifact(store.project_manifest_path(project_id), role="project_manifest")
    jobs = store.list_project_jobs(project_id)
    project = {
        **project_summary(manifest, manifest_artifact),
        "artifact_id": manifest_artifact["artifact_id"],
    }
    cards, provider_gate = build_workbench_cards(store, manifest=manifest, jobs=jobs, project=project)
    filmstrip = build_filmstrip(manifest)
    project_readiness = build_project_readiness(manifest, jobs, provider_gate)
    production_board = build_production_board(manifest, jobs, provider_gate, project_readiness)
    command_hub = build_command_hub(project_readiness, production_board)
    return {
        "artifact_type": "agentflow_runtime_workbench_state",
        "schema_version": "0.1.0",
        "project_id": project_id,
        "navigation": NAVIGATION,
        "project": project,
        "project_readiness": project_readiness,
        "workspace": {
            "default_surface": "creation_canvas",
            "primary_action": project_readiness["current_action"],
            "status_vocabulary": [
                "not_started",
                "ready_not_run",
                "running",
                "succeeded",
                "failed",
                "blocked",
                "cancelled",
                "needs_review",
            ],
        },
        "asset_library": build_asset_library(manifest),
        "cards": cards,
        "filmstrip": filmstrip,
        "creation_workspace": build_creation_workspace(
            manifest=manifest,
            cards=cards,
            filmstrip=filmstrip,
            project_readiness=project_readiness,
            command_hub=command_hub,
        ),
        "review_room": build_review_room(store, manifest, jobs),
        "style_memory": build_style_memory(store, manifest),
        "job_center": build_job_center(jobs),
        "activity_timeline": build_activity_timeline(jobs),
        "production_board": production_board,
        "command_hub": command_hub,
        "project_hub": build_project_hub(manifest, jobs, project, command_hub),
        "events": build_workbench_events(jobs),
        "provider_gate": provider_gate,
        "advanced_evidence": {
            "visible_by_default": False,
            "available": True,
            "non_claims": NON_CLAIMS,
            "artifact_refs_available": True,
        },
        "safe_ref_policy": SAFE_REF_POLICY,
        "non_claims": NON_CLAIMS,
    }


__all__ = ("build_workbench_state",)
