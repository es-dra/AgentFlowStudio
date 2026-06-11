from __future__ import annotations

from pathlib import Path
from typing import Any

from apps.api.runtime_store import RuntimeStore


def asset_run_artifacts(store: RuntimeStore, output_dir: Path) -> dict[str, Any]:
    names = {
        "asset_test_package": "asset_test_package.json",
        "asset_feedback_event": "asset_feedback_event.json",
        "asset_profile_version": "asset_profile_version.json",
        "asset_profile_context_projection": "asset_profile_context_projection.json",
        "asset_consistency_review": "asset_consistency_review.json",
        "real_asset_test_report": "real_asset_test_report.json",
        "review_screen_selected_files": "review_screen_selected_files.json",
    }
    return {
        key: store.register_artifact(output_dir / filename, role=key)
        for key, filename in names.items()
        if (output_dir / filename).exists()
    }


def two_round_artifacts(store: RuntimeStore, output_dir: Path) -> dict[str, Any]:
    return {
        "two_round_context_runtime_report": store.register_artifact(
            output_dir / "two_round_context_runtime_report.json",
            role="two_round_context_runtime_report",
        ),
        "asset_profile_context_projection": store.register_artifact(
            output_dir / "asset_profile_context_projection.json",
            role="asset_profile_context_projection",
        ),
        "asset_consistency_review": store.register_artifact(
            output_dir / "asset_consistency_review.json",
            role="asset_consistency_review",
        ),
    }


def provider_artifacts(store: RuntimeStore, output_dir: Path) -> dict[str, Any]:
    return {
        "provider_validation_plan": store.register_artifact(
            output_dir / "provider_validation_plan.json",
            role="provider_validation_plan",
        ),
        "provider_validation_result": store.register_artifact(
            output_dir / "provider_validation_result.json",
            role="provider_validation_result",
        ),
        "provider_safe_manifest": store.register_artifact(
            output_dir / "provider_safe_manifest.json",
            role="provider_safe_manifest",
        ),
    }


def script_provider_artifacts(store: RuntimeStore, output_dir: Path) -> dict[str, Any]:
    return {
        "llm_script_request_plan": store.register_artifact(
            output_dir / "llm_script_request_plan.json",
            role="llm_script_request_plan",
        ),
        "script_storyboard_safe_artifact": store.register_artifact(
            output_dir / "script_storyboard_safe_artifact.json",
            role="script_storyboard_safe_artifact",
        ),
        "script_provider_safe_manifest": store.register_artifact(
            output_dir / "script_provider_safe_manifest.json",
            role="script_provider_safe_manifest",
        ),
    }


def prompt_memory_artifacts(store: RuntimeStore, output_dir: Path) -> dict[str, Any]:
    return {
        "creative_brief": store.register_artifact(
            output_dir / "creative_brief.json",
            role="creative_brief",
        ),
        "prompt_assembly_trace": store.register_artifact(
            output_dir / "prompt_assembly_trace.json",
            role="prompt_assembly_trace",
        ),
        "prompt_optimization_safe_manifest": store.register_artifact(
            output_dir / "prompt_optimization_safe_manifest.json",
            role="prompt_optimization_safe_manifest",
        ),
    }


def update_project_after_asset_run(
    store: RuntimeStore,
    project_id: str,
    job_id: str,
    report: dict[str, Any],
    artifacts: dict[str, Any],
) -> None:
    status = "blocked" if report.get("blocks") else "ready_for_next_round"
    store.update_project_manifest(
        project_id,
        {
            "runs": [_run_ref(job_id, "round_1", status, artifacts["real_asset_test_report"])],
            "packages": [_artifact_list_ref(artifacts["asset_test_package"])],
            "feedback_refs": [_artifact_list_ref(artifacts["asset_feedback_event"])],
            "profile_version_refs": [_artifact_list_ref(artifacts["asset_profile_version"])],
        },
        status=status,
    )


def round_2_run_ref(job_id: str, status: str, artifact: dict[str, Any]) -> dict[str, Any]:
    return _run_ref(job_id, "round_2", status, artifact)


def feedback_ref(artifact: dict[str, Any], feedback_id: str) -> dict[str, Any]:
    return {**_artifact_list_ref(artifact), "feedback_id": str(feedback_id)}


def _run_ref(job_id: str, round_label: str, status: str, artifact: dict[str, Any]) -> dict[str, Any]:
    return {"job_id": job_id, "round": round_label, "status": status, "artifact_id": artifact["artifact_id"]}


def _artifact_list_ref(artifact: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifact_id": artifact["artifact_id"],
        "artifact_type": artifact["artifact_type"],
        "filename": artifact["filename"],
    }


__all__ = (
    "asset_run_artifacts",
    "feedback_ref",
    "prompt_memory_artifacts",
    "provider_artifacts",
    "round_2_run_ref",
    "script_provider_artifacts",
    "two_round_artifacts",
    "update_project_after_asset_run",
)
