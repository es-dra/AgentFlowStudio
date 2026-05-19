from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from narratocut.candidate_sop import HIGHLIGHT_SCORE_REPORT, score_candidate_windows
from narratocut.ocr_sop import OCR_TRANSCRIPT_MANIFEST, build_ocr_transcript_from_frames
from narratocut.schemas import Transcript
from narratocut.utils import write_json
from narratocut.workflow_engine.context import WorkflowContext
from narratocut.workflow_engine.definitions import WorkflowStepDefinition


def build_ocr_transcript_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    frames_ref = _require_input(step, "ocr_frames")
    frames_path = Path(str(context.resolve_input(str(frames_ref))))
    frames = _load_ocr_frames(frames_path)
    video_path = _optional_text_input(step, context, "video") or str(context.state.get("source_video") or "")
    transcript, manifest = build_ocr_transcript_from_frames(
        frames,
        video_path=video_path or None,
        language=_optional_text_input(step, context, "language"),
        frame_interval_sec=_optional_float(step, context, "frame_interval_sec") or 1.0,
        dedupe_similarity=_optional_float(step, context, "dedupe_similarity") or 0.85,
        merge_gap_sec=_optional_float(step, context, "merge_gap_sec") or 0.8,
        min_text_chars=_optional_int(step, context, "min_text_chars") or 2,
    )

    context.state["ocr_transcript"] = transcript
    context.state["transcript"] = transcript
    context.state["ocr_transcript_manifest"] = manifest
    return []


def write_ocr_transcript_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    transcript = _state_transcript(context, "ocr_transcript")
    manifest = _state_dict(context, "ocr_transcript_manifest")
    transcript_ref = str(step.outputs.get("transcript") or "ocr_transcript.json")
    manifest_ref = str(step.outputs.get("manifest") or OCR_TRANSCRIPT_MANIFEST)

    write_json(context.output_path(transcript_ref), transcript)
    write_json(context.output_path(manifest_ref), {**manifest, "transcript_path": transcript_ref, "manifest_path": manifest_ref})
    context.artifacts["ocr_transcript"] = transcript_ref
    context.artifacts["transcript"] = transcript_ref
    context.artifacts["ocr_transcript_manifest"] = manifest_ref
    return [transcript_ref, manifest_ref]


def score_candidate_windows_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    manifest = _state_dict(context, str(step.inputs.get("candidate_windows") or "candidate_windows"))
    report, plan = score_candidate_windows(
        manifest,
        max_selected=_optional_int(step, context, "max_selected") or 4,
        max_overlap_ratio=_optional_float(step, context, "max_overlap_ratio") or 0.5,
    )
    context.state["highlight_score_report"] = report
    context.state["highlight_plan"] = plan
    return []


def write_highlight_score_report_node(step: WorkflowStepDefinition, context: WorkflowContext) -> list[str]:
    report = _state_dict(context, str(step.inputs.get("highlight_score_report") or "highlight_score_report"))
    output_ref = str(step.outputs.get("highlight_score_report") or HIGHLIGHT_SCORE_REPORT)
    write_json(context.output_path(output_ref), {**report, "manifest_path": output_ref})
    context.artifacts["highlight_score_report"] = output_ref
    return [output_ref]


def _load_ocr_frames(path: Path) -> list[dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"ocr_frames_path does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"OCR frames JSON is invalid: {path}") from exc

    frames = payload.get("frames") if isinstance(payload, dict) else payload
    if not isinstance(frames, list) or not all(isinstance(item, dict) for item in frames):
        raise ValueError("ocr_frames must be a JSON array or an object with a frames array")
    return frames


def _require_input(step: WorkflowStepDefinition, name: str) -> object:
    if name not in step.inputs:
        raise ValueError(f"Step {step.id} missing required input: {name}")
    return step.inputs[name]


def _optional_text_input(step: WorkflowStepDefinition, context: WorkflowContext, name: str) -> str | None:
    value = _optional_resolved_input(step, context, name)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_int(step: WorkflowStepDefinition, context: WorkflowContext, name: str) -> int | None:
    raw = _optional_resolved_input(step, context, name)
    if raw is None:
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        if isinstance(raw, str) and raw not in context.inputs and raw not in context.state:
            return None
        raise ValueError(f"{name} must be an integer") from exc
    if value <= 0:
        raise ValueError(f"{name} must be greater than 0")
    return value


def _optional_float(step: WorkflowStepDefinition, context: WorkflowContext, name: str) -> float | None:
    raw = _optional_resolved_input(step, context, name)
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError) as exc:
        if isinstance(raw, str) and raw not in context.inputs and raw not in context.state:
            return None
        raise ValueError(f"{name} must be a number") from exc


def _optional_resolved_input(step: WorkflowStepDefinition, context: WorkflowContext, name: str) -> object | None:
    if name not in step.inputs:
        return None
    value = step.inputs[name]
    if value == name and name not in context.inputs and name not in context.state:
        return None
    if isinstance(value, str) and value not in context.inputs and value not in context.state:
        return value
    return context.resolve_input(str(value))


def _state_transcript(context: WorkflowContext, key: str) -> Transcript:
    value = context.state.get(key)
    if isinstance(value, Transcript):
        return value
    raise ValueError(f"{key} must be generated before this node")


def _state_dict(context: WorkflowContext, key: str) -> dict[str, Any]:
    value = context.state.get(key)
    if isinstance(value, dict):
        return value
    raise ValueError(f"{key} must be generated before this node")
