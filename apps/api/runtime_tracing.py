from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from agentflow.contracts.agentops import validate_agentops_artifact
from agentflow.harness.json_io import write_json


DEFAULT_TOOL_GATE_STATE = {
    "remote_llm": "blocked_by_default",
    "remote_asr": "blocked_by_default",
    "remote_image": "blocked_by_default",
    "remote_video": "blocked_by_default",
    "remote_vision": "blocked_by_default",
}
PROVIDER_PLAN_TOOL_GATE_STATE = {
    "remote_llm": "blocked_by_default",
    "remote_asr": "blocked_by_default",
    "remote_image": "plan_only",
    "remote_video": "plan_only",
    "remote_vision": "blocked_by_default",
}
DEFAULT_NON_CLAIMS = [
    "not human acceptance",
    "not business validation",
    "not durable memory",
]


def write_run_trace(
    output_dir: Path,
    *,
    project_id: str,
    job_id: str,
    action: str,
    status: str,
    input_refs: list[dict[str, Any]],
    generated_artifact_refs: list[dict[str, Any]],
    blocked_refs: list[dict[str, Any]] | None = None,
    tester_feedback: dict[str, Any] | None = None,
    tool_gate_state: dict[str, str] | None = None,
) -> Path:
    trace = {
        "schema_version": "0.1.0",
        "artifact_type": "agentflow_run_trace",
        "trace_id": f"trace:{job_id}:{uuid4().hex[:8]}",
        "project_id": project_id,
        "job_id": job_id,
        "action": action,
        "status": status,
        "input_refs": input_refs,
        "tool_gate_state": tool_gate_state or DEFAULT_TOOL_GATE_STATE,
        "generated_artifact_refs": generated_artifact_refs,
        "blocked_refs": blocked_refs or [],
        "tester_feedback": tester_feedback or {"status": "not_recorded"},
        "non_claims": DEFAULT_NON_CLAIMS,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
    }
    validate_agentops_artifact(trace)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "agentflow_run_trace.json"
    write_json(path, trace)
    return path


def safe_request_ref(role: str, value: str | None) -> dict[str, str]:
    if not value:
        return {"role": role, "ref": "not_provided"}
    return {"role": role, "ref": Path(value).name}


def artifact_refs(artifacts: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "artifact_id": str(artifact.get("artifact_id", "")),
            "artifact_type": str(artifact.get("artifact_type", "")),
            "role": role,
        }
        for role, artifact in artifacts.items()
    ]


def blocked_refs_from_blocks(blocks: list[Any]) -> list[dict[str, str]]:
    return [
        {"ref": str(block.get("block_id") or block.get("ref") or "block"), "reason": str(block.get("reason", "blocked"))}
        for block in blocks
        if isinstance(block, dict)
    ]


__all__ = (
    "PROVIDER_PLAN_TOOL_GATE_STATE",
    "artifact_refs",
    "blocked_refs_from_blocks",
    "safe_request_ref",
    "write_run_trace",
)
