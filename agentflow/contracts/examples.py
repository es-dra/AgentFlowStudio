from __future__ import annotations

import json
from pathlib import Path
from typing import Any


AGENTFLOW_CONTRACT_SCHEMA_VERSION = "0.1.0"

AGENTFLOW_SKILL_ROUTER_EXAMPLES = (
    Path("examples/agentflow/skill_invocation.example.json"),
    Path("examples/agentflow/skill_result.example.json"),
    Path("examples/agentflow/router_decision.example.json"),
)

AGENTFLOW_ASSET_EXAMPLES = (
    Path("examples/agentflow/intermediate_asset.example.json"),
    Path("examples/agentflow/reusable_asset_profile.example.json"),
    Path("examples/agentflow/asset_reuse_decision.example.json"),
    Path("examples/agentflow/narratostudio_asset_feedback_review.example.json"),
    Path("examples/agentflow/narratostudio_asset_feedback_review_validation.example.json"),
    Path("examples/agentflow/narratostudio_asset_feedback_review_gate.example.json"),
    Path("examples/agentflow/narratostudio_asset_reuse_dry_run_plan.example.json"),
    Path("examples/agentflow/narratostudio_asset_reuse_review.example.json"),
)

AGENTFLOW_EXAMPLE_PATHS = (
    Path("examples/agentflow/project_manifest.example.json"),
    Path("examples/agentflow/artifact_map.example.json"),
    Path("examples/agentflow/feedback_event.example.jsonl"),
    Path("examples/agentflow/memory_candidate.example.json"),
    Path("examples/agentflow/memory_promotion_decision.example.json"),
    Path("examples/agentflow/memory_evidence_reuse_review.example.json"),
    Path("examples/agentflow/memory_video_pipeline_protocol.example.json"),
    Path("examples/agentflow/memory_video_pipeline_review.example.json"),
    Path("examples/agentflow/memory_video_pipeline_human_observation.example.json"),
    Path("examples/agentflow/memory_video_pipeline_presentation_package.example.json"),
    Path("examples/agentflow/memory_video_pipeline_package.example.json"),
    Path("examples/agentflow/loulan_memory_package.example.json"),
    Path("examples/agentflow/loulan_api_workbench_plan.example.json"),
    Path("examples/agentflow/loulan_human_review_pack.example.json"),
    *AGENTFLOW_SKILL_ROUTER_EXAMPLES,
    *AGENTFLOW_ASSET_EXAMPLES,
)

AGENTFLOW_EXAMPLE_TYPES = frozenset(
    {
        "agentflow_project_manifest",
        "agentflow_artifact_map",
        "agentflow_feedback_event",
        "agentflow_memory_candidate",
        "agentflow_memory_promotion_decision",
        "agentflow_memory_evidence_reuse_review",
        "agentflow_memory_video_pipeline_protocol",
        "agentflow_memory_video_pipeline_review",
        "agentflow_memory_video_pipeline_human_observation",
        "agentflow_memory_video_pipeline_presentation_package",
        "agentflow_memory_video_pipeline_package",
        "agentflow_loulan_memory_package",
        "agentflow_loulan_api_workbench_plan",
        "agentflow_loulan_human_review_pack",
        "agentflow_skill_invocation",
        "agentflow_skill_result",
        "agentflow_router_decision",
        "agentflow_intermediate_asset",
        "agentflow_reusable_asset_profile",
        "agentflow_asset_reuse_decision",
        "agentflow_narratostudio_asset_feedback_review",
        "agentflow_narratostudio_asset_feedback_review_validation",
        "agentflow_narratostudio_asset_feedback_review_gate",
        "agentflow_narratostudio_asset_reuse_dry_run_plan",
        "agentflow_narratostudio_asset_reuse_review",
    }
)


def load_agentflow_example(path: Path) -> dict[str, Any] | list[dict[str, Any]]:
    if path.suffix == ".jsonl":
        return [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    return json.loads(path.read_text(encoding="utf-8"))


def load_agentflow_examples() -> list[tuple[Path, dict[str, Any] | list[dict[str, Any]]]]:
    return [(path, load_agentflow_example(path)) for path in AGENTFLOW_EXAMPLE_PATHS]


__all__ = (
    "AGENTFLOW_ASSET_EXAMPLES",
    "AGENTFLOW_CONTRACT_SCHEMA_VERSION",
    "AGENTFLOW_EXAMPLE_PATHS",
    "AGENTFLOW_EXAMPLE_TYPES",
    "AGENTFLOW_SKILL_ROUTER_EXAMPLES",
    "load_agentflow_example",
    "load_agentflow_examples",
)
