from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentflow.memory.production_operator_outputs import OPERATOR_LOOP_KIND
from agentflow.memory.production_operator_run_package import OPERATOR_RUN_PACKAGE_KIND


def load_operator_context(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("operator artifact must be a JSON object")
    kind = payload.get("kind")
    if kind not in {OPERATOR_LOOP_KIND, OPERATOR_RUN_PACKAGE_KIND}:
        raise ValueError("operator artifact must be an operator manifest or run package")
    root = path.parent if kind == OPERATOR_LOOP_KIND else path.parent.parent
    return {
        "artifact": payload,
        "artifact_kind": kind,
        "root": root,
        "context_bundle": _load_optional_json(root / "run" / "context_bundle.json"),
        "next_task_packet": _load_optional_json(root / "next_task_packet" / "next_task_packet.json"),
    }


def profile_blocked_refs(profile: dict[str, Any], operator_context: dict[str, Any]) -> list[dict[str, str]]:
    context = context_index(operator_context)
    blockers = []
    for ref_id in _list(profile.get("evidence_refs")):
        ref_text = str(ref_id)
        if ref_text in context["allowed"]:
            continue
        blocked_reason = context["blocked"].get(ref_text)
        blockers.append({"ref_id": ref_text, "reason": blocked_reason or "missing_reference"})
    for ref_id in _list(profile.get("promotion_decision_refs")):
        ref_text = str(ref_id)
        if ref_text not in context["decisions"]:
            blockers.append({"ref_id": ref_text, "reason": "missing_promotion_decision_ref"})
    status = str(profile.get("profile_status", "candidate"))
    if status != "promoted" or profile.get("context_eligibility") != "included":
        blockers.append({"ref_id": str(profile.get("profile_id")), "reason": f"profile_status_{status}_not_context_eligible"})
    return blockers


def context_index(operator_context: dict[str, Any]) -> dict[str, Any]:
    context_bundle = _dict(operator_context.get("context_bundle"))
    next_task_packet = _dict(operator_context.get("next_task_packet"))
    included = _list(context_bundle.get("included_refs"))
    blocked = _list(context_bundle.get("blocked_refs")) + _list(next_task_packet.get("blocked_refs"))
    allowed = {str(item.get("ref_id")) for item in included if item.get("ref_id")}
    allowed.update(str(item.get("ref_id")) for item in _list(next_task_packet.get("allowed_context_refs")) if item.get("ref_id"))
    decisions = {str(item.get("decision_id")) for item in included if item.get("decision_id")}
    return {
        "allowed": allowed,
        "blocked": {str(item.get("ref_id")): str(item.get("reason", "blocked")) for item in blocked if item.get("ref_id")},
        "decisions": decisions,
    }


def profiles_have_promotion_refs_for_memory(profiles: list[dict[str, Any]]) -> bool:
    for profile in profiles:
        evidence_refs = [str(ref) for ref in _list(profile.get("evidence_refs"))]
        if any(ref.startswith("memory:") for ref in evidence_refs) and not profile.get("promotion_decision_refs"):
            return False
    return True


def _load_optional_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    return payload if isinstance(payload, dict) else {}


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


__all__ = (
    "context_index",
    "load_operator_context",
    "profile_blocked_refs",
    "profiles_have_promotion_refs_for_memory",
)
