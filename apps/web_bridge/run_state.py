from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentflow_studio.schemas import WorkflowRun
from agentflow_studio.workflow_engine import WorkflowContext

from apps.web_bridge.utils import display_ref, duration_ms, load_json_object, value_from


BRIDGE_STATUS_FILE = "bridge_status.json"
SAFE_ARTIFACT_SUFFIXES = {".json", ".md", ".srt", ".txt", ".mp4", ".webm", ".mov", ".jpg", ".jpeg", ".png", ".wav", ".mp3"}


def run_status(run_dir: Path) -> dict[str, Any]:
    manifest = load_json_object(run_dir / "manifest.json")
    run_manifest = load_json_object(run_dir / "run_manifest.json")
    trace = load_json_object(run_dir / "trace.json")
    bridge_status = load_json_object(run_dir / BRIDGE_STATUS_FILE)
    steps = _run_steps(manifest, trace, bridge_status)
    status = _status_from_sources(manifest, run_manifest, bridge_status)
    return {
        "run_id": run_dir.name,
        "run_dir": display_ref(run_dir),
        "status": status,
        "workflow": _workflow_from_sources(manifest, run_manifest, bridge_status),
        "current_step": bridge_status.get("current_step"),
        "event": bridge_status.get("event"),
        "bridge_status_path": display_ref(run_dir / BRIDGE_STATUS_FILE) if bridge_status else "",
        "steps": steps,
        "artifact_index": run_manifest.get("artifact_index", {}) if isinstance(run_manifest, dict) else {},
        "files": _artifact_files(run_dir),
        "errors": _run_errors(manifest, steps, bridge_status),
        "next_actions": _run_next_actions(status, run_dir),
    }


def initial_steps(definition: Any) -> list[dict[str, Any]]:
    return [
        {
            "id": step.id,
            "type": step.type,
            "status": "pending",
            "outputs": list(step.outputs.values()),
            "error": None,
        }
        for step in definition.steps
    ]


def steps_from_context(definition: Any, context: WorkflowContext, current_step: str | None = None) -> list[dict[str, Any]]:
    results = {result.step_id: result for result in context.step_results}
    steps: list[dict[str, Any]] = []
    for step in definition.steps:
        result = results.get(step.id)
        if result is None:
            status = "running" if step.id == current_step else "pending"
            steps.append(
                {
                    "id": step.id,
                    "type": step.type,
                    "status": status,
                    "outputs": list(step.outputs.values()),
                    "error": None,
                    "started_at": None,
                    "ended_at": None,
                    "duration_ms": None,
                }
            )
            continue
        steps.append(
            {
                "id": result.step_id,
                "type": result.step_type,
                "status": result.status,
                "outputs": result.artifacts,
                "error": result.error,
                "started_at": result.started_at.isoformat() if result.started_at else None,
                "ended_at": result.ended_at.isoformat() if result.ended_at else None,
                "duration_ms": duration_ms(result.started_at, result.ended_at),
            }
        )
    return steps


def write_bridge_status(run_dir: Path, payload: dict[str, Any]) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    status_path = run_dir / BRIDGE_STATUS_FILE
    temp_path = run_dir / f"{BRIDGE_STATUS_FILE}.tmp"
    temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(status_path)


def bridge_progress(
    definition: Any,
    run: WorkflowRun,
    context: WorkflowContext,
    step: Any | None,
    event: str,
) -> None:
    current_step = step.id if step is not None and event == "step_started" else None
    status = "running" if run.status in {"pending", "running"} and not run.ended_at else run.status
    write_bridge_status(
        context.output_dir,
        {
            "run_id": run.run_id,
            "run_dir": display_ref(context.output_dir),
            "workflow": display_ref(context.workflow_path or run.workflow_name),
            "status": status,
            "steps": steps_from_context(definition, context, current_step=current_step),
            "current_step": current_step,
            "event": event,
            "errors": [run.error] if run.error else [],
        },
    )


def _run_steps(manifest: dict[str, Any], trace: dict[str, Any], bridge_status: dict[str, Any]) -> list[dict[str, Any]]:
    bridge_steps = bridge_status.get("steps")
    if isinstance(bridge_steps, list) and bridge_steps:
        return [_normalize_step(raw) for raw in bridge_steps if isinstance(raw, dict)]
    raw_steps = manifest.get("steps")
    if not isinstance(raw_steps, list):
        raw_steps = trace.get("steps") if isinstance(trace.get("steps"), list) else []
    return [_normalize_step(raw) for raw in raw_steps if isinstance(raw, dict)]


def _normalize_step(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(raw.get("step_id") or raw.get("id") or "unknown"),
        "type": str(raw.get("step_type") or raw.get("type") or ""),
        "status": str(raw.get("status") or "unknown"),
        "outputs": raw.get("artifacts") if isinstance(raw.get("artifacts"), list) else raw.get("outputs", []),
        "error": raw.get("error"),
        "started_at": raw.get("started_at"),
        "ended_at": raw.get("ended_at"),
        "duration_ms": raw.get("duration_ms"),
    }


def _artifact_files(run_dir: Path) -> list[str]:
    if not run_dir.exists():
        return []
    files: list[str] = []
    for path in sorted(run_dir.rglob("*")):
        if path.is_file() and path.suffix.lower() in SAFE_ARTIFACT_SUFFIXES:
            files.append(display_ref(path.relative_to(run_dir)))
    return files


def _run_errors(manifest: dict[str, Any], steps: list[dict[str, Any]], bridge_status: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if manifest.get("error"):
        errors.append(str(manifest["error"]))
    for error in bridge_status.get("errors", []):
        if error:
            errors.append(str(error))
    for step in steps:
        if step.get("error"):
            errors.append(f"{step['id']}: {step['error']}")
    return errors


def _run_next_actions(status: str, run_dir: Path) -> list[str]:
    if status == "success":
        actions = ["refresh_review", "open_review_mode", "inspect_artifacts"]
        if not (run_dir / "review_report.json").exists():
            actions.insert(0, "run_review")
        return actions
    if status == "failed":
        return ["inspect_failed_step", "adjust_inputs", "rerun_workflow"]
    return ["check_bridge", "select_workflow", "create_plan"]


def _status_from_sources(manifest: dict[str, Any], run_manifest: dict[str, Any], bridge_status: dict[str, Any]) -> str:
    bridge_value = value_from(bridge_status, "status", "")
    if bridge_value in {"pending", "running"}:
        return bridge_value
    return value_from(manifest, "status", value_from(run_manifest, "status", value_from(bridge_status, "status", "unknown")))


def _workflow_from_sources(manifest: dict[str, Any], run_manifest: dict[str, Any], bridge_status: dict[str, Any]) -> str:
    return value_from(manifest, "workflow_name", value_from(run_manifest, "workflow", value_from(bridge_status, "workflow", "unknown")))
