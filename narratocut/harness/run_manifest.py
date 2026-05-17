from __future__ import annotations

from typing import TYPE_CHECKING, Any

from narratocut.schemas import WorkflowRun
from narratocut.utils import write_json

if TYPE_CHECKING:
    from narratocut.workflow_engine.context import WorkflowContext


PROJECT_NAME = "NarratoCut"


def write_run_manifest(run: WorkflowRun, context: WorkflowContext) -> dict[str, Any]:
    manifest = build_run_manifest(run, context)
    write_json(context.output_path("run_manifest.json"), manifest)
    return manifest


def build_run_manifest(run: WorkflowRun, context: WorkflowContext) -> dict[str, Any]:
    artifacts = _contract_artifacts(context.artifacts)
    return {
        "project": PROJECT_NAME,
        "run_id": run.run_id,
        "workflow": _display_ref(context.workflow_path or run.workflow_name),
        "mode": context.mode,
        "created_at": run.started_at.isoformat(),
        "status": run.status,
        "inputs": _contract_inputs(context.inputs),
        "artifacts": artifacts,
        "environment": {
            "ffmpeg_required": context.ffmpeg_required,
            "network_required": context.network_required,
        },
    }


def _contract_inputs(inputs: dict[str, Any]) -> dict[str, Any]:
    if "input_text_file" not in inputs:
        return {key: _normalize_value(value) for key, value in inputs.items()}

    normalized = {"text": _normalize_value(inputs["input_text_file"])}
    for key, value in inputs.items():
        if key != "input_text_file":
            normalized[key] = _normalize_value(value)
    return normalized


def _contract_artifacts(artifacts: dict[str, str]) -> dict[str, str]:
    normalized = dict(artifacts)
    normalized["manifest"] = "manifest.json"
    if "clips" in normalized:
        normalized["clips_dir"] = _as_directory_ref(normalized["clips"])
    return normalized


def _as_directory_ref(path: str) -> str:
    return path if path.endswith("/") else f"{path}/"


def _display_ref(path: str) -> str:
    return path.replace("\\", "/")


def _normalize_value(value: Any) -> Any:
    if isinstance(value, str):
        return _display_ref(value)
    return value
