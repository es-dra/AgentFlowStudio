from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentflow.harness.constants import AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS


AGENTOPS_SCHEMA_VERSION = "0.1.0"
AGENTOPS_ARTIFACT_TYPES = frozenset(
    {
        "agentflow_run_trace",
        "agentflow_quality_report",
        "agentflow_guardrail_result",
        "agentflow_handoff_record",
        "agentflow_maintenance_audit_report",
    }
)
REQUIRED_NON_CLAIMS = (
    "not human acceptance",
    "not business validation",
    "not durable memory",
)


def load_agentops_artifact(path: Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("AgentOps artifact must be a JSON object")
    validate_agentops_artifact(payload)
    return payload


def validate_agentops_artifact(payload: dict[str, Any]) -> None:
    if payload.get("schema_version") != AGENTOPS_SCHEMA_VERSION:
        raise ValueError(f"AgentOps artifact schema_version must be {AGENTOPS_SCHEMA_VERSION}")
    if payload.get("artifact_type") not in AGENTOPS_ARTIFACT_TYPES:
        raise ValueError("unsupported AgentOps artifact_type")
    non_claims = payload.get("non_claims")
    if not isinstance(non_claims, list):
        raise ValueError("AgentOps artifact requires non_claims list")
    missing = [claim for claim in REQUIRED_NON_CLAIMS if claim not in non_claims]
    if missing:
        raise ValueError(f"AgentOps artifact missing non_claims: {', '.join(missing)}")
    if payload.get("writes_long_term_memory") is not False:
        raise ValueError("AgentOps artifact must keep writes_long_term_memory false")
    if payload.get("writes_company_kb") is not False:
        raise ValueError("AgentOps artifact must keep writes_company_kb false")
    _reject_private_or_secret_fragments(payload)


def _reject_private_or_secret_fragments(payload: dict[str, Any]) -> None:
    raw = json.dumps(payload, ensure_ascii=False).lower()
    for fragment in AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS:
        if fragment.lower() in raw:
            raise ValueError("AgentOps artifact contains private path, media ref, or secret-like fragment")


__all__ = (
    "AGENTOPS_ARTIFACT_TYPES",
    "AGENTOPS_SCHEMA_VERSION",
    "REQUIRED_NON_CLAIMS",
    "load_agentops_artifact",
    "validate_agentops_artifact",
)
