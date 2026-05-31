from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "0.1.0"


def feedback_loop_gates(root: Path) -> dict[str, Any]:
    return {
        "b01": _b01_feedback_loop_gate(root),
        "b01_decision_crosswalk": _b01_decision_crosswalk(root),
    }


def _b01_feedback_loop_gate(root: Path) -> dict[str, Any]:
    gate_path = root / "manifests" / "afs_b01_feedback_loop_gate.json"
    if not gate_path.exists():
        return _not_supplied_gate("manifests/afs_b01_feedback_loop_gate.json")
    gate = _read_json(gate_path)
    _validate_safe_gate(
        gate,
        artifact_type="loulan_afs_b01_feedback_loop_gate",
        label="Loulan feedback loop gate",
    )
    summary = gate.get("current_gate_summary") or {}
    return {
        "status": str(gate.get("status") or "unknown"),
        "source_ref": "manifests/afs_b01_feedback_loop_gate.json",
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "human_acceptance_recorded": False,
        "media_generation_started": False,
        "decision_items": _int(summary.get("b01_decision_items")),
        "pending_decisions": _int(summary.get("pending_decisions")),
        "approved_decisions": _int(summary.get("approved_decisions")),
        "repair_requested": _int(summary.get("repair_requested")),
        "rejected_decisions": _int(summary.get("rejected_decisions")),
        "validation_status": str(summary.get("validation_status") or "unknown"),
        "apply_status": str(summary.get("apply_status") or "unknown"),
        "afs_import_ready": summary.get("afs_import_ready") is True,
        "context_projection_ready": summary.get("context_projection_ready") is True,
        "next_step": str(gate.get("next_step") or ""),
    }


def _b01_decision_crosswalk(root: Path) -> dict[str, Any]:
    crosswalk_path = root / "manifests" / "afs_b01_decision_crosswalk.json"
    if not crosswalk_path.exists():
        return _not_supplied_gate("manifests/afs_b01_decision_crosswalk.json")
    crosswalk = _read_json(crosswalk_path)
    _validate_safe_gate(
        crosswalk,
        artifact_type="loulan_afs_b01_decision_crosswalk",
        label="Loulan decision crosswalk",
    )
    layers = {
        str(layer.get("layer_id") or ""): layer
        for layer in crosswalk.get("decision_layers") or []
        if isinstance(layer, dict)
    }
    return {
        "status": str(crosswalk.get("status") or "unknown"),
        "source_ref": "manifests/afs_b01_decision_crosswalk.json",
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "human_acceptance_recorded": False,
        "media_generation_started": False,
        "local_shot_gate": _decision_layer(layers.get("loulan_local_b01_shot_gate")),
        "afs_b01_import_gate": _decision_layer(layers.get("afs_b01_import_gate")),
        "afs_broader_decision_review_gate": _decision_layer(layers.get("afs_broader_decision_review_gate")),
        "next_step": str(crosswalk.get("next_step") or ""),
    }


def _decision_layer(layer: dict[str, Any] | None) -> dict[str, Any]:
    if not layer:
        return {
            "decision_count": 0,
            "pending_count": 0,
            "target_ref_count": 0,
            "target_refs_sample": [],
            "current_blocker": "not_supplied",
        }
    target_refs = layer.get("target_refs")
    target_summary = layer.get("target_refs_summary") or {}
    target_ref_count = len(target_refs) if isinstance(target_refs, list) else _int(target_summary.get("shot_slots")) + _int(target_summary.get("asset_slots"))
    return {
        "decision_count": _int(layer.get("decision_count")),
        "pending_count": _int(layer.get("pending_count")),
        "target_ref_count": target_ref_count,
        "target_refs_sample": [str(ref) for ref in target_refs[:8]] if isinstance(target_refs, list) else [],
        "current_blocker": str(layer.get("current_blocker") or "unknown"),
    }


def _not_supplied_gate(source_ref: str) -> dict[str, Any]:
    return {
        "status": "not_supplied",
        "source_ref": source_ref,
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "human_acceptance_recorded": False,
        "media_generation_started": False,
        "pending_decisions": 0,
        "context_projection_ready": False,
    }


def _validate_safe_gate(payload: dict[str, Any], *, artifact_type: str, label: str) -> None:
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"{label} requires schema_version 0.1.0")
    if payload.get("artifact_type") != artifact_type:
        raise ValueError(f"{label} has unexpected artifact_type")
    if payload.get("provider_calls_started") is not False:
        raise ValueError(f"{label} must not have provider calls started")
    if payload.get("writes_long_term_memory") is not False:
        raise ValueError(f"{label} must not write long-term memory")
    if payload.get("human_acceptance_recorded") is not False:
        raise ValueError(f"{label} must not record human acceptance")
    if payload.get("media_generation_started") is not False:
        raise ValueError(f"{label} must not start media generation")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0
