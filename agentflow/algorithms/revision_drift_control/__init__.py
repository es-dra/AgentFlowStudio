from __future__ import annotations

from typing import Any


ALGORITHM_ID = "afs.revision_drift_control.v0.1"
INPUT_CONTRACT = "base output refs, revision intent, preserve/change boundaries, temporal scope"
OUTPUT_CONTRACT = "revision control plan and drift-risk summary"
FAILURE_MODES = ("missing_base_reference", "unsupported_temporal_scope", "preserve_change_conflict")
EVIDENCE_BOUNDARY = "revision plan references safe artifacts only and never stores media bytes"


def revision_plan(*, intent: str, preserve: list[str], change: list[str], temporal_scope: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "0.1.0",
        "revision_intent": str(intent or "").strip(),
        "preserve_boundaries": [str(item).strip() for item in preserve if str(item).strip()],
        "change_boundaries": [str(item).strip() for item in change if str(item).strip()],
        "temporal_scope": temporal_scope or {},
        "drift_risks": ["identity drift", "motion drift"],
        "claim_boundary": "revision_plan_not_provider_validation",
    }


__all__ = (
    "ALGORITHM_ID",
    "EVIDENCE_BOUNDARY",
    "FAILURE_MODES",
    "INPUT_CONTRACT",
    "OUTPUT_CONTRACT",
    "revision_plan",
)
