from __future__ import annotations

from typing import Any

from fastapi import FastAPI


def company_os_gfr_projection_payload() -> dict[str, Any]:
    return {
        "projection_id": "afs-company-os-gfr-projection-v0",
        "version": "2026-06-18.v0",
        "status": "candidate_runtime_projection",
        "source_boundary": {
            "company_os_source": "10-Startup",
            "afs_repo_role": "execution_projection_only",
            "private_material_policy": "excluded_from_runtime_payload",
        },
        "gfr_packet_fields": [
            "identity",
            "task_type",
            "context_pack",
            "required_reads",
            "write_scope",
            "non_goals",
            "evidence_standard",
            "tool_provider_gates",
            "verification_route",
            "feedback_route",
            "human_decisions_required",
        ],
        "context_packs": [
            "universal_kernel",
            "engineering_delivery",
            "afs_project",
            "rule_steward",
        ],
        "provider_gates": [
            {"id": "llm", "default": "closed"},
            {"id": "image", "default": "closed"},
            {"id": "video", "default": "closed"},
            {"id": "vision", "default": "closed"},
            {"id": "asr", "default": "closed"},
            {"id": "external_download", "default": "closed"},
        ],
        "evidence_states": [
            {
                "id": "structure_verification",
                "does_not_prove": ["runtime_verification", "human_acceptance", "business_validation"],
            },
            {
                "id": "runtime_verification",
                "does_not_prove": ["human_acceptance", "business_validation", "durable_memory_promotion"],
            },
            {
                "id": "provider_smoke",
                "does_not_prove": ["product_quality", "human_acceptance", "business_validation"],
            },
            {
                "id": "human_acceptance",
                "does_not_prove": ["business_validation", "durable_memory_promotion"],
            },
            {
                "id": "business_validation",
                "does_not_prove": ["legal_approval", "durable_memory_promotion"],
            },
            {
                "id": "durable_memory_promotion",
                "does_not_prove": ["business_validation"],
            },
        ],
        "feedback_routes": [
            "project_record_only",
            "company_os_feedback_packet",
            "candidate_rule_ledger",
            "secure_local_note",
            "no_feedback_needed",
        ],
        "runtime_recording": {
            "supported_now": [
                "read safe COS/GFR projection",
                "record raw project feedback through existing feedback endpoint",
            ],
            "not_supported_yet": [
                "automatic rule promotion",
                "COS UI console",
                "provider execution from COS registry",
            ],
        },
        "non_claim_boundary": (
            "This endpoint is a safe projection for AFS. It does not expose source-KB raw material, "
            "provider secrets, local absolute paths, customer material, human acceptance, business "
            "validation, or durable rule promotion."
        ),
    }


def register_runtime_company_os_routes(app: FastAPI) -> None:
    @app.get("/company-os/gfr-projection")
    def company_os_gfr_projection() -> dict[str, Any]:
        return company_os_gfr_projection_payload()


__all__ = ("company_os_gfr_projection_payload", "register_runtime_company_os_routes")
