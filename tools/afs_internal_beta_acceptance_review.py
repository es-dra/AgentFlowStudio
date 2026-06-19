from __future__ import annotations

from typing import Any


def build_human_review_packet(steps: list[dict[str, Any]]) -> dict[str, Any]:
    step_ids = {str(step.get("step_id", "")) for step in steps}
    return {
        "schema_version": "0.1.0",
        "status": "pending_human_review",
        "reviewer_role": "internal_beta_operator",
        "acceptance_claim": "not_claimed",
        "score_scale": {"min": 1, "max": 5, "pass_threshold": 4},
        "required_sections": _required_sections(step_ids),
        "manual_artifacts_required": [
            {
                "artifact_id": "browser_session_notes",
                "description": "Record the tested user, project, actions, visible result, and residual issue without secrets or local paths.",
            },
            {
                "artifact_id": "media_quality_scores",
                "description": "Score generated image/video quality, identity continuity, text/watermark risk, and whether the next iteration is usable.",
            },
        ],
        "decision_options": [
            "accepted_for_next_beta_round",
            "needs_fix_before_next_beta_round",
            "blocked_by_provider_or_configuration",
        ],
        "forbidden_claims": [
            "human acceptance",
            "business validation",
            "durable memory promotion",
            "live provider quality approval",
        ],
    }


def _required_sections(step_ids: set[str]) -> list[dict[str, Any]]:
    sections = [
        _section(
            "account_project_isolation",
            "Account and project isolation",
            ["auth_registration", "project_owner_isolation", "studio_state_isolation"],
            "Both alpha and beta users can operate without seeing or mutating each other's projects or artifacts.",
        ),
        _section(
            "asset_context_continuity",
            "Asset confirmation and context continuity",
            ["asset_confirmation", "fixed_asset_context_reuse"],
            "A confirmed visual asset is visible to the next model-call context while draft/rejected assets stay out by default.",
        ),
        _section(
            "generated_media_quality",
            "Generated media quality",
            ["video_gate_closed"],
            "Generated image/video output is visually usable, maintains subject/scene continuity, and does not show unacceptable text or watermark artifacts.",
        ),
        _section(
            "feedback_revision_loop",
            "Feedback and revision loop",
            ["feedback_raw_evidence"],
            "User feedback is captured as raw evidence and can guide the next revision without silently overwriting durable assets.",
        ),
        _section(
            "privacy_boundary",
            "Privacy and provider boundary",
            ["artifact_scope", "vision_draft_gate_closed", "video_gate_closed"],
            "Reports and UI summaries expose no secret, credential, session token, local absolute path, signed URL, provider raw response, or media bytes.",
        ),
    ]
    for section in sections:
        section["evidence_available"] = all(step_id in step_ids for step_id in section["evidence_step_ids"])
    return sections


def _section(section_id: str, title: str, evidence_step_ids: list[str], pass_condition: str) -> dict[str, Any]:
    return {
        "section_id": section_id,
        "title": title,
        "evidence_step_ids": evidence_step_ids,
        "requires_human_score": True,
        "required_score": 4,
        "pass_condition": pass_condition,
        "reviewer_notes": "",
    }
