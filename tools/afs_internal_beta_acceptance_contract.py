from __future__ import annotations

from typing import Any

from tools.afs_internal_beta_acceptance_config import AcceptanceConfig
from tools.afs_internal_beta_acceptance_generation_steps import (
    asset_confirmation_step,
    feedback_step,
    fixed_asset_context_reuse_step,
    fixed_assets_not_polluted_step,
    video_gate_step,
    vision_gate_step,
)
from tools.afs_internal_beta_acceptance_scope_steps import (
    artifact_scope_step,
    auth_registration_step,
    health_step,
    image_asset_step,
    project_isolation_step,
    studio_state_step,
)
from tools.afs_internal_beta_acceptance_review import build_human_review_packet


def run_acceptance_contract(
    client,
    *,
    config: AcceptanceConfig | None = None,
    mode: str = "inprocess_deterministic",
) -> dict[str, Any]:
    active_config = config or AcceptanceConfig.deterministic()
    steps: list[dict[str, Any]] = []
    health = health_step(client, steps)
    alpha_headers, beta_headers = auth_registration_step(client, steps, active_config)
    manifest_artifact_id = project_isolation_step(client, steps, alpha_headers, beta_headers, active_config)
    studio_state_step(client, steps, alpha_headers, beta_headers, active_config)
    image_asset_id, image_artifact_id = image_asset_step(client, steps, alpha_headers, beta_headers, active_config)
    vision_gate_step(client, steps, alpha_headers, image_asset_id, active_config)
    fixed_assets_not_polluted_step(client, steps, alpha_headers, active_config)
    visual_asset_id = asset_confirmation_step(client, steps, alpha_headers, image_asset_id, active_config)
    fixed_asset_context_reuse_step(client, steps, alpha_headers, visual_asset_id, active_config)
    feedback_artifact_id = feedback_step(client, steps, alpha_headers, active_config)
    artifact_scope_step(client, steps, alpha_headers, beta_headers, [
        manifest_artifact_id,
        image_artifact_id,
        feedback_artifact_id,
    ])
    video_gate_step(client, steps, alpha_headers, health, image_asset_id, active_config)
    return _report(steps, mode=mode)


def _report(steps: list[dict[str, Any]], *, mode: str) -> dict[str, Any]:
    return {
        "artifact_type": "afs_internal_beta_acceptance_report",
        "schema_version": "0.1.0",
        "mode": mode,
        "status": _report_status(steps),
        "summary": _summary(steps),
        "steps": steps,
        "human_review_packet": build_human_review_packet(steps),
        "provider_calls_started": any(bool(step.get("provider_calls_started")) for step in steps),
        "human_acceptance_claim": "not_claimed",
        "business_validation_claim": "not_claimed",
        "writes_company_kb": False,
        "writes_long_term_memory": False,
        "non_claims": [
            "deterministic runtime contract only",
            "not live provider smoke",
            "not human acceptance",
            "not business validation",
            "not durable memory",
        ],
        "next_actions": [
            "Run the same user journey against the deployed server with disposable invite codes.",
            "Open LLM/image/vision live checks only after explicit provider capability approval.",
            "Keep video gate closed until the Seedance relay is configured and explicitly authorized.",
        ],
    }


def _report_status(steps: list[dict[str, Any]]) -> str:
    allowed = {"passed", "expected_blocked"}
    return "contract_verified_pending_human_acceptance" if all(step["status"] in allowed for step in steps) else "needs_fixes"


def _summary(steps: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "step_count": len(steps),
        "passed_step_count": sum(1 for step in steps if step["status"] == "passed"),
        "expected_blocked_step_count": sum(1 for step in steps if step["status"] == "expected_blocked"),
        "failed_step_count": sum(1 for step in steps if step["status"] == "failed"),
    }
