from __future__ import annotations

from pathlib import Path
from typing import Any

from agentflow_studio.utils import write_json

from agentflow.memory.video_pipeline import SCHEMA_VERSION
from agentflow.memory.video_pipeline_review import REVIEW_TYPE


OBSERVATION_TYPE = "agentflow_memory_video_pipeline_human_observation"
OBSERVATION_NOTES_TYPE = "agentflow_memory_video_pipeline_human_observation_notes"
SUPPORTED_VERDICTS = frozenset(
    {
        "memory_backed_stronger",
        "baseline_stronger",
        "mixed",
        "no_clear_difference",
    }
)
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


def build_memory_video_pipeline_observation(
    review: dict[str, Any],
    notes: dict[str, Any],
) -> dict[str, Any]:
    """Build a bounded human visual observation from a review artifact."""
    _validate_review(review)
    _validate_notes(notes)
    _reject_unsafe_refs(notes)
    observations = list(notes["observations"])
    _validate_observation_coverage(review, observations)
    claim_boundaries = _claim_boundaries(notes)
    summary = notes["observed_signal_summary"]
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": OBSERVATION_TYPE,
        "protocol_id": review["protocol_id"],
        "source_review_artifact_type": review["artifact_type"],
        "provider_calls_started_by_observation": False,
        "writes_long_term_memory": False,
        "observation_status": "visual_observation_recorded",
        "reviewer": notes.get("reviewer"),
        "review_inputs": review["review_inputs"],
        "lane_parity": review["lane_parity"],
        "storyboard": review["storyboard"],
        "observations": observations,
        "observed_signal_summary": {
            "baseline_more_variable": bool(summary.get("baseline_more_variable")),
            "memory_backed_more_stable": bool(summary.get("memory_backed_more_stable")),
            "residual_risk": summary.get("residual_risk"),
        },
        "claim_boundaries": claim_boundaries,
    }


def write_memory_video_pipeline_observation(
    observation: dict[str, Any],
    output_dir: str | Path,
) -> list[Path]:
    output_root = Path(output_dir)
    paths = [
        write_json(output_root / "memory_video_pipeline_human_observation.json", observation),
    ]
    report_path = output_root / "memory_video_pipeline_human_observation.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_memory_video_pipeline_observation_report(observation), encoding="utf-8")
    paths.append(report_path)
    return paths


def render_memory_video_pipeline_observation_report(observation: dict[str, Any]) -> str:
    observation_lines = "\n".join(
        f"- {item['criterion']}: {item['verdict']} - {item['note']}"
        for item in observation["observations"]
    )
    return "\n".join(
        [
            "# Memory Video Pipeline Human Observation",
            "",
            f"- Protocol: `{observation['protocol_id']}`",
            "- Provider calls: not started by observation",
            "- Human acceptance: not acceptance",
            "- Business validation: not validated",
            "- Quality improvement claim: bounded visual signal only",
            "- Durable Memory runtime: not implemented",
            "",
            "## Observed Signal",
            "",
            f"- Baseline more variable: {observation['observed_signal_summary']['baseline_more_variable']}",
            f"- Memory-backed more stable: {observation['observed_signal_summary']['memory_backed_more_stable']}",
            f"- Residual risk: {observation['observed_signal_summary']['residual_risk']}",
            "",
            "## Observations",
            "",
            observation_lines,
            "",
        ]
    )


def _validate_review(review: dict[str, Any]) -> None:
    if review.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("memory video review schema_version must be 0.1.0")
    if review.get("artifact_type") != REVIEW_TYPE:
        raise ValueError(f"memory video observation requires source review artifact_type {REVIEW_TYPE}")
    if review.get("provider_calls_started_by_review") is not False:
        raise ValueError("source review must not start provider calls")
    if review.get("writes_long_term_memory") is not False:
        raise ValueError("source review must not write long-term memory")


def _validate_notes(notes: dict[str, Any]) -> None:
    if notes.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("memory video observation notes schema_version must be 0.1.0")
    if notes.get("artifact_type") != OBSERVATION_NOTES_TYPE:
        raise ValueError(f"memory video observation notes artifact_type must be {OBSERVATION_NOTES_TYPE}")
    observations = notes.get("observations")
    if not isinstance(observations, list) or not observations:
        raise ValueError("memory video observation notes require observations")
    for item in observations:
        if item.get("verdict") not in SUPPORTED_VERDICTS:
            raise ValueError(f"unsupported observation verdict: {item.get('verdict')}")
        if not item.get("criterion") or not item.get("note"):
            raise ValueError("observation entries require criterion and note")
    summary = notes.get("observed_signal_summary")
    if not isinstance(summary, dict):
        raise ValueError("observation notes require observed_signal_summary")


def _validate_observation_coverage(review: dict[str, Any], observations: list[dict[str, Any]]) -> None:
    expected = set(review.get("cross_run_stability", {}).get("review_fields", []))
    seen = {item["criterion"] for item in observations}
    missing = sorted(expected - seen)
    if missing:
        raise ValueError(f"missing observation criteria: {missing}")


def _claim_boundaries(notes: dict[str, Any]) -> dict[str, str]:
    boundaries = notes.get("claim_boundaries") or {}
    required = {
        "human_acceptance": "not_acceptance",
        "business_validation": "not_validated",
        "quality_improvement_claim": "bounded_visual_signal_only",
        "durable_memory_runtime": "not_implemented",
    }
    for key, expected in required.items():
        if boundaries.get(key) != expected:
            raise ValueError(f"claim boundary {key} must be {expected}")
    return required


def _reject_unsafe_refs(value: Any) -> None:
    serialized = str(value)
    if any(fragment.lower() in serialized.lower() for fragment in UNSAFE_FRAGMENTS):
        raise ValueError("memory video observation contains unsafe path, provider URL, secret, or generated media reference")
