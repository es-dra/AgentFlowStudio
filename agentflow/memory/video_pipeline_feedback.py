from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentflow.harness.json_io import write_json

from agentflow.memory.video_pipeline import SCHEMA_VERSION
from agentflow.memory.video_pipeline_observation import OBSERVATION_TYPE


FEEDBACK_EVENT_TYPE = "agentflow_feedback_event"
UNSAFE_FRAGMENTS = (
    "D:\\",
    "C:\\",
    "file://",
    "data:image/",
    "Bearer ",
    "signed_url",
    "signature=",
    "token=",
    "api_key",
    "secret_key",
    "https://",
    "http://",
    ".mp4",
    ".mov",
)


def build_memory_video_pipeline_feedback_event_draft(
    observation: dict[str, Any],
    *,
    created_at: str,
) -> dict[str, Any]:
    """Build a raw feedback-event draft from bounded observation evidence."""
    _validate_observation(observation)
    summary = observation["observed_signal_summary"]
    event = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": FEEDBACK_EVENT_TYPE,
        "feedback_id": f"{observation['protocol_id']}_feedback_draft",
        "source": "human",
        "target_type": "run",
        "target_id": observation["protocol_id"],
        "decision": "note",
        "reason_tags": _reason_tags(summary),
        "user_note": _user_note(summary),
        "created_at": created_at,
        "draft_status": "draft_not_persisted",
        "source_observation_artifact_type": observation["artifact_type"],
        "writes_long_term_memory": False,
        "claim_boundaries": observation["claim_boundaries"],
    }
    _reject_unsafe_refs(event)
    return event


def write_memory_video_pipeline_feedback_event_draft(
    event: dict[str, Any],
    output_dir: str | Path,
) -> list[Path]:
    output_root = Path(output_dir)
    json_path = write_json(output_root / "memory_video_pipeline_feedback_event_draft.json", event)

    jsonl_path = output_root / "memory_video_pipeline_feedback_event_draft.jsonl"
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    jsonl_path.write_text(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")

    report_path = output_root / "memory_video_pipeline_feedback_event_draft.md"
    report_path.write_text(render_feedback_event_draft_report(event), encoding="utf-8")
    return [json_path, jsonl_path, report_path]


def render_feedback_event_draft_report(event: dict[str, Any]) -> str:
    tags = ", ".join(event["reason_tags"])
    return "\n".join(
        [
            "# Memory Video Pipeline Feedback Event Draft",
            "",
            f"- Feedback id: `{event['feedback_id']}`",
            f"- Target: `{event['target_type']}:{event['target_id']}`",
            f"- Decision: `{event['decision']}`",
            "- Draft status: not persisted",
            "- Durable Memory runtime: not implemented",
            "- Human acceptance: not acceptance",
            "- Business validation: not validated",
            "",
            "## Reason Tags",
            "",
            tags,
            "",
            "## User Note",
            "",
            event["user_note"],
            "",
        ]
    )


def _validate_observation(observation: dict[str, Any]) -> None:
    if observation.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("feedback event draft requires observation schema_version 0.1.0")
    if observation.get("artifact_type") != OBSERVATION_TYPE:
        raise ValueError(f"feedback event draft requires source observation artifact_type {OBSERVATION_TYPE}")
    if observation.get("provider_calls_started_by_observation") is not False:
        raise ValueError("source observation must not start provider calls")
    if observation.get("writes_long_term_memory") is not False:
        raise ValueError("source observation must not write long-term memory")
    boundaries = observation.get("claim_boundaries") or {}
    if boundaries.get("human_acceptance") != "not_acceptance":
        raise ValueError("feedback event draft requires human_acceptance not_acceptance")
    if boundaries.get("business_validation") != "not_validated":
        raise ValueError("feedback event draft requires business_validation not_validated")


def _reason_tags(summary: dict[str, Any]) -> list[str]:
    tags = ["bounded_visual_signal", "not_human_acceptance"]
    if summary.get("baseline_more_variable"):
        tags.append("baseline_more_variable")
    if summary.get("memory_backed_more_stable"):
        tags.append("memory_backed_more_stable")
    residual_risk = summary.get("residual_risk")
    if residual_risk:
        tags.append(str(residual_risk))
    return sorted(set(tags))


def _user_note(summary: dict[str, Any]) -> str:
    return (
        "Bounded visual observation: baseline repeat runs were more variable "
        f"({bool(summary.get('baseline_more_variable'))}); memory-backed repeat runs were more stable "
        f"({bool(summary.get('memory_backed_more_stable'))}); residual risk: {summary.get('residual_risk')}."
    )


def _reject_unsafe_refs(value: Any) -> None:
    serialized = str(value)
    if any(fragment.lower() in serialized.lower() for fragment in UNSAFE_FRAGMENTS):
        raise ValueError("memory video feedback draft contains unsafe path, provider URL, secret, or generated media reference")
