from __future__ import annotations

from pathlib import Path
from typing import Any

from narratocut.utils import write_json

from agentflow.memory.video_pipeline import (
    SCHEMA_VERSION,
    build_memory_video_pipeline_plan,
    write_memory_video_pipeline_plan,
)
from agentflow.memory.video_pipeline_feedback import (
    build_memory_video_pipeline_feedback_event_draft,
    write_memory_video_pipeline_feedback_event_draft,
)
from agentflow.memory.video_pipeline_observation import (
    build_memory_video_pipeline_observation,
    write_memory_video_pipeline_observation,
)
from agentflow.memory.video_pipeline_presentation import (
    build_memory_video_pipeline_presentation,
    write_memory_video_pipeline_presentation,
)
from agentflow.memory.video_pipeline_review import (
    build_memory_video_pipeline_review,
    write_memory_video_pipeline_review,
)


PACKAGE_TYPE = "agentflow_memory_video_pipeline_package"


def build_memory_video_pipeline_package(
    protocol: dict[str, Any],
    artifact_manifest: dict[str, Any],
    observation_notes: dict[str, Any],
    *,
    created_at: str,
) -> dict[str, Any]:
    """Build a no-call package that links plan, review, observation, presentation, and feedback."""
    plan = build_memory_video_pipeline_plan(protocol)
    review = build_memory_video_pipeline_review(protocol, artifact_manifest)
    observation = build_memory_video_pipeline_observation(review, observation_notes)
    presentation = build_memory_video_pipeline_presentation(protocol, review, observation)
    feedback_event = build_memory_video_pipeline_feedback_event_draft(
        observation,
        created_at=created_at,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": PACKAGE_TYPE,
        "protocol_id": protocol["protocol_id"],
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "plan": plan,
        "review": review,
        "observation": observation,
        "presentation": presentation,
        "feedback_event_draft": feedback_event,
        "claim_boundaries": {
            "runtime_verification": "manifest_status_only",
            **observation["claim_boundaries"],
        },
    }


def write_memory_video_pipeline_package(package: dict[str, Any], output_dir: str | Path) -> list[Path]:
    output_root = Path(output_dir)
    paths: list[Path] = []
    paths.extend(write_memory_video_pipeline_plan(package["plan"], output_root / "plan"))
    paths.extend(write_memory_video_pipeline_review(package["review"], output_root / "review"))
    paths.extend(write_memory_video_pipeline_observation(package["observation"], output_root / "observation"))
    paths.extend(write_memory_video_pipeline_presentation(package["presentation"], output_root / "presentation"))
    paths.extend(write_memory_video_pipeline_feedback_event_draft(package["feedback_event_draft"], output_root / "feedback"))
    paths.append(write_json(output_root / "memory_video_pipeline_package_summary.json", _summary(package)))
    return paths


def _summary(package: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": PACKAGE_TYPE,
        "protocol_id": package["protocol_id"],
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "plan_ref": "plan/run_plan.json",
        "review_ref": "review/memory_video_pipeline_review.json",
        "observation_ref": "observation/memory_video_pipeline_human_observation.json",
        "presentation_ref": "presentation/memory_video_pipeline_presentation_package.json",
        "feedback_event_draft_ref": "feedback/memory_video_pipeline_feedback_event_draft.json",
        "claim_boundaries": package["claim_boundaries"],
    }
