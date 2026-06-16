from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


ALGORITHM_ID = "afs.provider_gate_manifest.v0.1"
INPUT_CONTRACT = "capability, required gate, provider outcome metadata"
OUTPUT_CONTRACT = "safe provider gate state and manifest without provider raw data"
FAILURE_MODES = ("remote_gate_closed", "provider_failed", "unsafe_manifest_rejected")
EVIDENCE_BOUNDARY = "safe summary only; no secrets, signed URLs, provider raw response, local paths, or media bytes"

TRUE_VALUES = {"1", "true", "yes", "on"}
CAPABILITY_GATES = {
    "llm": "AFS_ALLOW_REMOTE_LLM",
    "image": "AFS_ALLOW_REMOTE_IMAGE",
    "video": "AFS_ALLOW_REMOTE_VIDEO",
    "vision": "AFS_ALLOW_REMOTE_VISION",
    "asr": "AFS_ALLOW_REMOTE_ASR",
}


@dataclass(frozen=True)
class GateStatus:
    capability: str
    required_gate: str
    status: str

    def public(self) -> dict[str, str]:
        return {
            "capability": self.capability,
            "required_gate": self.required_gate,
            "status": self.status,
        }


def required_gate_for(capability: str) -> str:
    return CAPABILITY_GATES.get(str(capability), "AFS_ALLOW_REMOTE_IMAGE")


def provider_gate_status(
    capability: str,
    *,
    enabled: bool | None = None,
    env: dict[str, str] | None = None,
) -> GateStatus:
    gate = required_gate_for(capability)
    if enabled is None:
        source = env if env is not None else os.environ
        enabled = str(source.get(gate, "")).strip().lower() in TRUE_VALUES
    return GateStatus(capability=str(capability), required_gate=gate, status="open" if enabled else "blocked")


def blocked_manifest(
    *,
    action: str,
    capability: str,
    required_gate: str,
    failure_class: str,
    provider_service_id: str | None = None,
) -> dict[str, Any]:
    return {
        "artifact_type": "agentflow_provider_safe_manifest",
        "schema_version": "0.1.0",
        "action": action,
        "status": "blocked",
        "capability": capability,
        "provider_service_id": provider_service_id or "not_selected",
        "failure_class": failure_class,
        "blocks": [
            {
                "block_id": failure_class,
                "reason": "remote provider gate is closed",
                "required_gate": required_gate,
            }
        ],
        "provider_calls_started": False,
        "provider_raw_response_stored": False,
        "media_bytes_returned_by_api": False,
        "credentialed_urls_returned_by_api": False,
        "local_paths_returned_by_api": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "claim_boundary": "provider_gate_block_not_runtime_failure",
    }


def succeeded_manifest(
    *,
    action: str,
    capability: str,
    provider_service_id: str,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "artifact_type": "agentflow_provider_safe_manifest",
        "schema_version": "0.1.0",
        "action": action,
        "status": "succeeded",
        "capability": capability,
        "provider_service_id": provider_service_id,
        "safe_evidence": evidence or {},
        "provider_calls_started": True,
        "provider_raw_response_stored": False,
        "media_bytes_returned_by_api": False,
        "credentialed_urls_returned_by_api": False,
        "local_paths_returned_by_api": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "claim_boundary": "normalized_provider_result_not_human_acceptance",
    }


__all__ = (
    "ALGORITHM_ID",
    "CAPABILITY_GATES",
    "EVIDENCE_BOUNDARY",
    "FAILURE_MODES",
    "GateStatus",
    "INPUT_CONTRACT",
    "OUTPUT_CONTRACT",
    "blocked_manifest",
    "provider_gate_status",
    "required_gate_for",
    "succeeded_manifest",
)
