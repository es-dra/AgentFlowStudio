from __future__ import annotations

import json
from pathlib import Path

from agentflow.algorithms.asset_card_candidates import build_asset_card_candidates
from agentflow.algorithms.content_quality_evaluation import evaluate_storyboard_content_quality
from agentflow.algorithms.production_graph import build_storyboard_production_graph
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
        candidates = build_asset_card_candidates(project_id="benchmark_project", asset_graph=graph)
        production_graph = build_storyboard_production_graph(
            project_id="benchmark_project",
            script_node_id=case["id"],
            script_text=case["script_text"],
            shots=shots,
            asset_graph=graph,
            content_quality_report=report,
        )
        checks = {item["id"]: item for item in report["checks"]}
        labels_by_type = {
            (asset["label"], asset["asset_type"])
            for asset in graph["assets"]
        }
        assets_by_key = {(asset["label"], asset["asset_type"]): asset for asset in graph["assets"]}
        candidates_by_key = {
            (candidate["draft_fields"]["display_name"], candidate["asset_type"]): candidate
            for candidate in candidates["candidates"]
        }
        low, high = case["expected_shot_range"]

        shot_counts.append(len(shots))
        assert low <= len(shots) <= high, case["id"]
        assert len(shots) not in case.get("forbidden_shot_counts", []), case["id"]
        assert checks["script_source_grounding"]["status"] == "passed", case["id"]
        assert checks["dynamic_shot_count"]["status"] == "passed", case["id"]
        assert checks["dynamic_shot_count"]["details"]["fixed_template_claimed"] is False
        assert checks["asset_evidence"]["status"] == "passed", case["id"]
        assert checks["keyframe_and_video_intent"]["status"] == "passed", case["id"]
        assert report["summary"]["human_review_needed"] is True
        assert candidates["summary"]["candidate_count"] == len(graph["assets"]), case["id"]
        assert production_graph["summary"]["shot_count"] == len(shots), case["id"]
        assert production_graph["summary"]["asset_count"] == len(graph["assets"]), case["id"]
        assert _relationship_types(production_graph) >= {"script_contains_shot", "shot_contains_asset", "quality_report_evaluates_storyboard"}
        for expected in case["expected_assets"]:
            key = (expected["label"], expected["asset_type"])
            assert key in labels_by_type, case["id"]
            assert key in candidates_by_key, case["id"]

        _assert_story_requirements(case, shots, assets_by_key, candidates_by_key)

    assert len(set(shot_counts)) >= 4


def _assert_story_requirements(case: dict, shots: list[dict], assets_by_key: dict, candidates_by_key: dict) -> None:
    combined_source = "\n".join(str((shot.get("source_span") or {}).get("text") or "") for shot in shots)

    for labels in case.get("expected_relationship_shots", []):
        assert any(_shot_has_labels(shot, labels) for shot in shots), case["id"]

    scene_indices = [_first_asset_shot_index(assets_by_key[(label, "scene")]) for label in case.get("expected_scene_sequence", [])]
    assert scene_indices == sorted(scene_indices), case["id"]

    for expected in case.get("expected_reused_assets", []):
        key = (expected["label"], expected["asset_type"])
        asset = assets_by_key[key]
        candidate = candidates_by_key[key]
        assert len(asset["shot_refs"]) >= expected["min_shot_refs"], case["id"]
        assert candidate["reuse_policy"]["suggested_reuse_scope"] == "project_reuse_candidate", case["id"]
        assert candidate["asset_memory_policy"]["writes_fixed_asset"] is False

    for terms in case.get("expected_story_terms", {}).values():
        for term in terms:
            assert term in combined_source, (case["id"], term)


def _shot_has_labels(shot: dict, labels: list[str]) -> bool:
    shot_labels = {str(ref.get("label") or "") for ref in shot.get("asset_refs", []) if isinstance(ref, dict)}
    return set(labels) <= shot_labels


def _first_asset_shot_index(asset: dict) -> int:
    first = str(asset["shot_refs"][0])
    return int(first.rsplit("_", 1)[1])


def _relationship_types(production_graph: dict) -> set[str]:
    return {str(item.get("relationship_type") or "") for item in production_graph["relationships"]}

