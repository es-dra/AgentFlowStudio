from __future__ import annotations

from pathlib import Path
from typing import Any

from agentflow.harness.json_io import write_json
from apps.api.runtime_store import RuntimeStore


def write_storyboard_artifacts(store: RuntimeStore, output_dir: Path, result: dict[str, Any]) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "storyboard_breakdown_request_plan.json", result["request_plan"])
    write_json(output_dir / "storyboard_breakdown_safe_artifact.json", result["safe_artifact"])
    write_json(output_dir / "storyboard_breakdown_safe_manifest.json", result["safe_manifest"])
    write_json(output_dir / "asset_graph.json", result["asset_graph"])
    write_json(output_dir / "asset_auto_binding_graph.json", result["asset_auto_binding_graph"])
    write_json(output_dir / "content_quality_report.json", result["content_quality_report"])
    write_json(output_dir / "production_graph_snapshot.json", result["production_graph"])
    write_json(output_dir / "asset_card_candidates.json", result["asset_card_candidates"])
    write_json(output_dir / "evidence_ledger.json", result["evidence_ledger"])
    return {
        "storyboard_breakdown_request_plan": store.register_artifact(
            output_dir / "storyboard_breakdown_request_plan.json",
            role="storyboard_breakdown_request_plan",
        ),
        "storyboard_breakdown_safe_artifact": store.register_artifact(
            output_dir / "storyboard_breakdown_safe_artifact.json",
            role="storyboard_breakdown_safe_artifact",
        ),
        "storyboard_breakdown_safe_manifest": store.register_artifact(
            output_dir / "storyboard_breakdown_safe_manifest.json",
            role="storyboard_breakdown_safe_manifest",
        ),
        "asset_graph": store.register_artifact(
            output_dir / "asset_graph.json",
            role="asset_graph",
        ),
        "asset_auto_binding_graph": store.register_artifact(
            output_dir / "asset_auto_binding_graph.json",
            role="asset_auto_binding_graph",
        ),
        "content_quality_report": store.register_artifact(
            output_dir / "content_quality_report.json",
            role="content_quality_report",
        ),
        "production_graph_snapshot": store.register_artifact(
            output_dir / "production_graph_snapshot.json",
            role="production_graph_snapshot",
        ),
        "asset_card_candidates": store.register_artifact(
            output_dir / "asset_card_candidates.json",
            role="asset_card_candidates",
        ),
        "evidence_ledger": store.register_artifact(
            output_dir / "evidence_ledger.json",
            role="evidence_ledger",
        ),
    }


__all__ = ("write_storyboard_artifacts",)
