from __future__ import annotations

import re
from typing import Any
from uuid import uuid4


ALGORITHM_ID = "afs.human_gate.v0.1"
INPUT_CONTRACT = "safe operator decision for a local asset/keyframe/plan contract artifact"
OUTPUT_CONTRACT = "runtime human gate decision event without provider calls, promotion, or durable memory writes"
FAILURE_MODES = ("unsupported_target_type", "unsupported_decision", "unsafe_decision_payload")
EVIDENCE_BOUNDARY = (
    "local step-gate evidence only; not creative quality acceptance, provider smoke, business validation, "
    "or fixed-asset promotion"
)

SUPPORTED_TARGET_TYPES = {"asset_card_candidate", "keyframe_generation_bridge", "accepted_generation_plan_packet"}
SUPPORTED_DECISIONS = {"accepted_for_next_step", "needs_revision", "rejected"}
NON_CLAIMS = [
    "not creative quality acceptance",
    "not generated media acceptance",
    "not fixed asset promotion",
    "not provider smoke",
    "not business validation",
    "not durable memory promotion",
]

SAFE_TOKEN_RE = re.compile(r"[^0-9A-Za-z\u4e00-\u9fff_.:-]+")


def build_human_gate_decision(
    *,
    project_id: str,
    target_type: str,
    target_id: str,
    decision: str,
    reviewed_at: str,
    note: str = "",
    artifact_id: str | None = None,
    node_id: str | None = None,
    scope: str | None = None,
) -> dict[str, Any]:
    if target_type not in SUPPORTED_TARGET_TYPES:
        raise ValueError("unsupported human gate target_type")
    if decision not in SUPPORTED_DECISIONS:
        raise ValueError("unsupported human gate decision")
    human_gate_id = f"runtime-human-gate:{_safe_token(project_id)}:{uuid4().hex[:12]}"
    return {
        "artifact_type": "agentflow_runtime_human_gate_decision",
        "schema_version": "0.1.0",
        "algorithm_id": ALGORITHM_ID,
        "human_gate_id": human_gate_id,
        "project_id": project_id,
        "decision": {
            "target_type": target_type,
            "target_id": _safe_token(target_id),
            "artifact_id": _safe_token(artifact_id),
            "node_id": _safe_token(node_id),
            "scope": _safe_token(scope) or _default_scope(target_type),
            "decision": decision,
            "note": _safe_note(note),
            "reviewed_at": reviewed_at,
            "human_acceptance_scope": "local_step_gate_only",
            "provider_calls_started": False,
            "provider_smoked": False,
            "opens_provider_gate": False,
            "blocks_provider_step": decision in {"needs_revision", "rejected"},
            "promotes_fixed_asset": False,
            "requires_separate_promotion": True,
            "writes_long_term_memory": False,
        },
        "safety_boundary": {
            "raw_provider_response_stored": False,
            "external_private_link_stored": False,
            "absolute_path_stored": False,
            "media_bytes_stored": False,
        },
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "non_claims": NON_CLAIMS,
    }


def _default_scope(target_type: str) -> str:
    if target_type == "asset_card_candidate":
        return "asset_card_candidate_review"
    if target_type == "keyframe_generation_bridge":
        return "keyframe_generation_bridge_review"
    if target_type == "accepted_generation_plan_packet":
        return "accepted_generation_plan_packet_review"
    return "runtime_human_gate"


def _safe_token(value: Any) -> str:
    return SAFE_TOKEN_RE.sub("_", str(value or "")).strip("_")[:160]


def _safe_note(value: Any) -> str:
    return " ".join(str(value or "").split())[:600]


__all__ = (
    "ALGORITHM_ID",
    "EVIDENCE_BOUNDARY",
    "FAILURE_MODES",
    "INPUT_CONTRACT",
    "NON_CLAIMS",
    "OUTPUT_CONTRACT",
    "SUPPORTED_DECISIONS",
    "SUPPORTED_TARGET_TYPES",
    "build_human_gate_decision",
)
