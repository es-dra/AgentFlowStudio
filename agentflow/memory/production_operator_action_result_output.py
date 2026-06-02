from __future__ import annotations

from pathlib import Path
from typing import Any

from agentflow.memory.production_next_operator_action_result import (
    NEXT_OPERATOR_ACTION_RESULT_KIND,
    build_next_operator_action_result,
    write_next_operator_action_result_report,
)
from narratocut.utils import write_json


NEXT_OPERATOR_ACTION_RESULT_ARTIFACTS = [
    {
        "artifact_type": NEXT_OPERATOR_ACTION_RESULT_KIND,
        "path": "next_operator_action_result/next_operator_action_result.json",
        "required": True,
    },
    {
        "artifact_type": "markdown_report",
        "path": "next_operator_action_result/next_operator_action_result.md",
        "required": True,
    },
]


def write_next_operator_action_result_from_operator_loop(
    result: dict[str, Any],
    output_root: str | Path,
    *,
    decision: str,
    summary: str,
    result_refs: list[str] | None,
    operator_role: str,
    recorded_at: str,
) -> list[Path]:
    """Write a post-check next-operator action result and keep it outside output_artifacts."""
    root = Path(output_root)
    start_event = _dict(result.get("next_operator_start_event"))
    if not start_event:
        raise ValueError("write_next_operator_action_result requires next_operator_start_event")
    action_result = build_next_operator_action_result(
        start_event,
        decision=decision,
        summary=summary,
        result_refs=result_refs,
        operator_role=operator_role,
        recorded_at=recorded_at,
        start_event_path="next_operator_start_event/next_operator_start_event.json",
    )
    written_paths = write_next_operator_action_result_report(action_result, root / "next_operator_action_result")
    result["next_operator_action_result"] = action_result
    manifest = result["manifest"]
    manifest["next_operator_action_result"] = _action_result_summary(action_result)
    manifest["post_check_artifacts"] = _post_check_artifacts(manifest.get("post_check_artifacts"))
    write_json(root / "production_memory_operator_loop_run.json", manifest)
    return written_paths


def _action_result_summary(action_result: dict[str, Any]) -> dict[str, Any]:
    refs = _list(action_result.get("result_refs"))
    return {
        "kind": action_result.get("kind", NEXT_OPERATOR_ACTION_RESULT_KIND),
        "result_status": action_result.get("result_status", "unknown"),
        "action_decision": action_result.get("action_decision", "unknown"),
        "path": "next_operator_action_result/next_operator_action_result.json",
        "markdown_path": "next_operator_action_result/next_operator_action_result.md",
        "source_start_event_status": action_result.get("source_start_event_status", "unknown"),
        "source_next_operator_action": action_result.get("source_next_operator_action", "unknown"),
        "result_refs": refs,
        "result_ref_count": len(refs),
        "summary": action_result.get("summary", ""),
        "operator_role": action_result.get("operator_role", "unknown"),
        "provider_calls_started": action_result.get("provider_calls_started") is True,
        "writes_long_term_memory": action_result.get("writes_long_term_memory") is True,
        "writes_company_kb": action_result.get("writes_company_kb") is True,
        "action_result_is_memory": action_result.get("action_result_is_memory") is True,
        "action_result_is_acceptance": action_result.get("action_result_is_acceptance") is True,
        "action_result_is_execution": action_result.get("action_result_is_execution") is True,
        "creates_memory_candidate": action_result.get("creates_memory_candidate") is True,
        "creates_promotion_decision": action_result.get("creates_promotion_decision") is True,
    }


def _post_check_artifacts(existing: Any) -> list[dict[str, Any]]:
    by_path = {
        str(_dict(item).get("path", "")): _dict(item)
        for item in _list(existing)
        if _dict(item).get("path")
    }
    for artifact in NEXT_OPERATOR_ACTION_RESULT_ARTIFACTS:
        by_path[artifact["path"]] = dict(artifact)
    return list(by_path.values())


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


__all__ = (
    "NEXT_OPERATOR_ACTION_RESULT_ARTIFACTS",
    "write_next_operator_action_result_from_operator_loop",
)
