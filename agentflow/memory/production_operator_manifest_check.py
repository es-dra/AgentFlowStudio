from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentflow.harness.constants import FAILED, PASSED
from agentflow.memory.production_loop import SCHEMA_VERSION
from agentflow.memory.production_operator_outputs import OPERATOR_LOOP_KIND
from agentflow_studio.utils import write_json

OPERATOR_MANIFEST_CHECK_KIND = "agentflow_production_memory_operator_manifest_check"
NODE_FAILURE_STATUSES = frozenset({"blocked", "failed", "missing", "error", "unknown"})


def load_operator_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("operator manifest must be a JSON object")
    return payload


def check_operator_manifest(
    manifest_path: str | Path,
    *,
    artifact_root: str | Path | None = None,
) -> dict[str, Any]:
    manifest_ref = Path(manifest_path)
    manifest = load_operator_manifest(manifest_ref)
    root = Path(artifact_root) if artifact_root is not None else manifest_ref.parent
    checked_refs, missing_refs, mismatched_refs, unsafe_refs = _check_output_refs(manifest, root)
    failed_nodes = _failed_nodes(manifest)
    failed_controls = _failed_controls(manifest)
    check_status = (
        FAILED
        if (
            manifest.get("kind") != OPERATOR_LOOP_KIND
            or missing_refs
            or mismatched_refs
            or unsafe_refs
            or failed_nodes
            or failed_controls
            or manifest.get("provider_calls_started") is True
            or manifest.get("writes_long_term_memory") is True
            or manifest.get("writes_company_kb") is True
        )
        else PASSED
    )
    return {
        "kind": OPERATOR_MANIFEST_CHECK_KIND,
        "artifact_type": OPERATOR_MANIFEST_CHECK_KIND,
        "schema_version": manifest.get("schema_version", SCHEMA_VERSION),
        "manifest_kind": manifest.get("kind", "unknown"),
        "manifest_path": _display_path(manifest_ref),
        "artifact_root": _display_path(root),
        "check_status": check_status,
        "chain_status": manifest.get("chain_status", "unknown"),
        "provider_mode": manifest.get("provider_mode", "unknown"),
        "provider_calls_started": manifest.get("provider_calls_started") is True,
        "writes_long_term_memory": manifest.get("writes_long_term_memory") is True,
        "writes_company_kb": manifest.get("writes_company_kb") is True,
        "ready_for_next_pass": check_status == PASSED and manifest.get("chain_status") == "ready",
        "node_count": len(manifest.get("operator_loop_nodes", [])),
        "control_count": len(manifest.get("controls", [])),
        "checked_ref_count": len(checked_refs),
        "checked_refs": checked_refs,
        "missing_refs": missing_refs,
        "mismatched_refs": mismatched_refs,
        "unsafe_refs": unsafe_refs,
        "failed_nodes": failed_nodes,
        "failed_controls": failed_controls,
        "claim_boundaries": {
            "structure_verification": "machine_checked",
            "runtime_verification": "artifact_refs_checked",
            "human_acceptance": "not_claimed",
            "business_validation": "not_claimed",
            "durable_memory": "not_written",
            "company_kb_write": "not_written",
        },
    }


def write_operator_manifest_check(check: dict[str, Any], output_path: str | Path) -> Path:
    return write_json(output_path, check)


def _check_output_refs(
    manifest: dict[str, Any],
    artifact_root: Path,
) -> tuple[list[dict[str, str]], list[str], list[dict[str, str]], list[str]]:
    checked_refs: list[dict[str, str]] = []
    missing_refs: list[str] = []
    mismatched_refs: list[dict[str, str]] = []
    unsafe_refs: list[str] = []
    for artifact in manifest.get("output_artifacts", []):
        path_ref = str(artifact.get("path", "")).replace("\\", "/")
        expected_type = str(artifact.get("artifact_type", "unknown"))
        if _unsafe_ref(path_ref):
            unsafe_refs.append(path_ref)
            continue
        full_path = artifact_root / path_ref
        if not full_path.exists():
            missing_refs.append(path_ref)
            continue
        checked_refs.append({"path": path_ref, "artifact_type": expected_type})
        if expected_type == "markdown_report":
            continue
        actual_type = _artifact_type(full_path)
        if actual_type != expected_type:
            mismatched_refs.append(
                {
                    "path": path_ref,
                    "expected_artifact_type": expected_type,
                    "actual_artifact_type": actual_type,
                }
            )
    return checked_refs, missing_refs, mismatched_refs, unsafe_refs


def _artifact_type(path: Path) -> str:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return "invalid_json"
    if not isinstance(payload, dict):
        return "non_object_json"
    return str(payload.get("kind") or payload.get("artifact_type") or "missing_artifact_type")


def _failed_controls(manifest: dict[str, Any]) -> list[dict[str, str]]:
    failed: list[dict[str, str]] = []
    for control in manifest.get("controls", []):
        status = str(control.get("status", "unknown"))
        if status != PASSED:
            failed.append({"control_id": str(control.get("control_id", "unknown")), "status": status})
    return failed


def _failed_nodes(manifest: dict[str, Any]) -> list[dict[str, str]]:
    failed: list[dict[str, str]] = []
    for node in manifest.get("operator_loop_nodes", []):
        status = str(node.get("status", "unknown"))
        if status in NODE_FAILURE_STATUSES:
            failed.append({"node_id": str(node.get("node_id", "unknown")), "status": status})
    return failed


def _unsafe_ref(path_ref: str) -> bool:
    path = Path(path_ref)
    return path.is_absolute() or path_ref.startswith("../") or "/../" in path_ref


def _display_path(path: Path) -> str:
    return str(path).replace("\\", "/")


__all__ = (
    "OPERATOR_MANIFEST_CHECK_KIND",
    "check_operator_manifest",
    "load_operator_manifest",
    "write_operator_manifest_check",
)
