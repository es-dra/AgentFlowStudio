from __future__ import annotations

import json
from pathlib import Path

from agentflow.algorithms.content_quality_evaluation import evaluate_storyboard_content_quality
from apps.api.runtime_asset_graph import build_asset_graph
from apps.api.runtime_storyboard_local import local_storyboard_shots


BENCHMARK_PATH = Path("examples/agentflow/content_quality_benchmark_scripts.example.json")


def test_content_quality_benchmark_scripts_cover_dynamic_storyboard_and_assets() -> None:
    payload = json.loads(BENCHMARK_PATH.read_text(encoding="utf-8"))

    assert payload["artifact_type"] == "agentflow_content_quality_benchmark_scripts"
    assert len(payload["cases"]) >= 6

    shot_counts: list[int] = []
    for case in payload["cases"]:
        shots = local_storyboard_shots(case["script_text"])
        graph = build_asset_graph(shots, source_text=case["script_text"], graph_source=f"benchmark:{case['id']}")
        report = evaluate_storyboard_content_quality(
            project_id="benchmark_project",
            node_id=case["id"],
            script_text=case["script_text"],
            shots=shots,
            asset_graph=graph,
            provider_calls_started=False,
            shot_count_hint=None,
        )
        checks = {item["id"]: item for item in report["checks"]}
        labels_by_type = {
            (asset["label"], asset["asset_type"])
            for asset in graph["assets"]
        }
        low, high = case["expected_shot_range"]

        shot_counts.append(len(shots))
        assert low <= len(shots) <= high, case["id"]
        assert checks["script_source_grounding"]["status"] == "passed", case["id"]
        assert checks["dynamic_shot_count"]["status"] == "passed", case["id"]
        assert checks["dynamic_shot_count"]["details"]["fixed_template_claimed"] is False
        assert checks["asset_evidence"]["status"] == "passed", case["id"]
        assert checks["keyframe_and_video_intent"]["status"] == "passed", case["id"]
        assert report["summary"]["human_review_needed"] is True
        for expected in case["expected_assets"]:
            assert (expected["label"], expected["asset_type"]) in labels_by_type, case["id"]

    assert len(set(shot_counts)) >= 3

