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


def render_human_review_markdown(report: dict[str, Any]) -> str:
    packet = report.get("human_review_packet") or {}
    lines = [
        "# AFS Internal Beta Human Review",
        "",
        f"Report status: `{_safe_inline(report.get('status'))}`",
        f"Review status: `{_safe_inline(packet.get('status'))}`",
        f"Human acceptance claim: `{_safe_inline(report.get('human_acceptance_claim'))}`",
        "",
        "Human acceptance is not claimed until this checklist is completed by an operator.",
        "",
        "## Required Review Sections",
        "",
    ]
    for section in packet.get("required_sections") or []:
        lines.extend(_section_markdown(section))
    lines.extend([
        "## Decision",
        "",
        f"Decision: `{_decision_options(packet)}`",
        "",
        "Operator notes:",
        "",
        "```text",
        "",
        "```",
        "",
        "## Boundaries",
        "",
    ])
    for claim in packet.get("forbidden_claims") or []:
        lines.append(f"- Do not claim {_safe_text(claim)} from this report alone.")
    lines.extend([
        "- Do not paste credentials, local paths, signed URLs, provider raw responses, or media bytes into this checklist.",
        "- Keep provider smoke, human acceptance, business validation, and durable-memory promotion as separate evidence states.",
        "",
    ])
    return "\n".join(lines)


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


def _section_markdown(section: dict[str, Any]) -> list[str]:
    title = _safe_text(section.get("title"))
    condition = _safe_text(section.get("pass_condition"))
    step_ids = ", ".join(f"`{_safe_inline(step_id)}`" for step_id in section.get("evidence_step_ids") or [])
    evidence = "yes" if section.get("evidence_available") else "no"
    return [
        f"- [ ] {title}",
        f"  - Evidence steps: {step_ids}",
        f"  - Evidence available: `{evidence}`",
        f"  - Pass condition: {condition}",
        "  - Score (1-5): ____",
        "  - Notes: ____",
        "",
    ]


def _decision_options(packet: dict[str, Any]) -> str:
    return "` / `".join(_safe_inline(item) for item in packet.get("decision_options") or [])


def _safe_inline(value: Any) -> str:
    return _safe_text(value).replace("`", "'")


def _safe_text(value: Any) -> str:
    text = str(value or "")
    replacements = {
        "session_token": "session credential",
        "signed_url": "signed link",
        "provider_raw_response": "provider raw payload",
        "invite": "credential",
    }
    for old, new in replacements.items():
        text = text.replace(old, new).replace(old.upper(), new).replace(old.title(), new)
    return text
