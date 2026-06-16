from __future__ import annotations

from typing import Any


ALGORITHM_ID = "afs.creative_intent_control.v0.1"
INPUT_CONTRACT = "user intent, context bundle, director parameters, provider capability descriptor"
OUTPUT_CONTRACT = "canonical creative brief, provider prompt, constraints, candidate scoring hints"
FAILURE_MODES = ("missing_user_intent", "provider_constraint_conflict", "unsafe_prompt_boundary")
EVIDENCE_BOUNDARY = "canonical brief is safe product semantics, not provider raw response"


def canonical_brief(*, prompt_text: str, context_bundle: dict[str, Any] | None = None, constraints: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "schema_version": "0.1.0",
        "prompt_text": str(prompt_text or "").strip(),
        "context_bundle_ref": "inline_safe_bundle" if context_bundle else "not_provided",
        "constraint_layers": constraints or {},
        "claim_boundary": "creative_brief_not_provider_execution",
    }


__all__ = (
    "ALGORITHM_ID",
    "EVIDENCE_BOUNDARY",
    "FAILURE_MODES",
    "INPUT_CONTRACT",
    "OUTPUT_CONTRACT",
    "canonical_brief",
)
