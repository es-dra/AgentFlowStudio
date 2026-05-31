from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from apps.cli.main import app
from agentflow.memory.loulan_package import build_loulan_memory_package


def test_loulan_memory_package_blocks_candidates_and_builtin_image_route(tmp_path: Path) -> None:
    root = _loulan_fixture(tmp_path)

    package = build_loulan_memory_package(root, created_at="2026-06-01T09:00:00+08:00")

    assert package["artifact_type"] == "agentflow_loulan_memory_package"
    assert package["project"]["project_id"] == "loulan_scene_assets"
    assert package["provider_calls_started"] is False
    assert package["writes_long_term_memory"] is False
    assert package["project"]["source_root_label"] == root.name
    assert package["shot_summary"]["total_shots"] == 2
    assert package["shot_summary"]["status_counts"]["keyframe_candidate_pending_review"] == 1
    assert package["asset_summary"]["status_counts"]["approved"] == 1
    assert package["asset_summary"]["status_counts"]["candidate_pending_human_review"] == 1
    assert package["asset_summary"]["missing_sha256_count"] == 1
    assert package["asset_summary"]["rejected_asset_count"] == 1
    assert package["provider_route_safety"]["image_generation"] == "blocked_until_api_workbench"
    assert package["provider_route_safety"]["unsafe_builtin_image_route_detected"] is True
    assert package["promotion_gates"]["overall_status"] == "blocked"
    assert package["next_context_bundle_draft"]["eligible_memory_refs"] == ["character:zhou_tong_school_v1"]
    assert {
        "character:guan_pingping_v2",
        "human/rejected/guan_pingping_v1.png",
    } <= set(package["next_context_bundle_draft"]["blocked_memory_refs"])
    assert [node["label"] for node in package["canvas_nodes"]] == [
        "Project",
        "Shots",
        "Assets",
        "Memory Loaded",
        "Baseline Plan",
        "Memory-backed Plan",
        "Review",
        "Feedback",
        "Next Pass",
    ]

    serialized = json.dumps(package, ensure_ascii=False)
    assert str(root) not in serialized
    assert "D:\\" not in serialized
    assert "api_key" not in serialized
    assert ".mp4" not in serialized


def test_loulan_memory_package_cli_writes_safe_dry_run_artifacts(tmp_path: Path) -> None:
    root = _loulan_fixture(tmp_path)
    output = tmp_path / "out"

    result = CliRunner().invoke(
        app,
        [
            "loulan-memory-package",
            "--project-root",
            str(root),
            "--created-at",
            "2026-06-01T09:00:00+08:00",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Loulan memory package" in result.output
    assert "Provider calls: not started" in result.output
    assert "Overall gate: blocked" in result.output
    assert str(root) not in result.output

    package_path = output / "loulan_memory_package.json"
    report_path = output / "loulan_memory_package.md"
    assert package_path.exists()
    assert report_path.exists()
    package = json.loads(package_path.read_text(encoding="utf-8"))
    assert package["artifact_type"] == "agentflow_loulan_memory_package"
    assert package["provider_route_safety"]["request_preview_only"] is True
    assert "durable Memory runtime: not implemented" in report_path.read_text(encoding="utf-8")


def test_loulan_memory_package_example_is_contract_safe() -> None:
    payload = json.loads(Path("examples/agentflow/loulan_memory_package.example.json").read_text(encoding="utf-8"))

    assert payload["schema_version"] == "0.1.0"
    assert payload["artifact_type"] == "agentflow_loulan_memory_package"
    assert payload["provider_calls_started"] is False
    assert payload["writes_long_term_memory"] is False
    assert payload["provider_route_safety"]["image_generation"] == "blocked_until_api_workbench"
    assert payload["promotion_gates"]["overall_status"] in {"ready", "blocked"}
    assert payload["api_workbench_skeleton"]["live_provider_calls"] == "blocked_by_default"
    assert "character:zhou_tong_school_v1" in payload["next_context_bundle_draft"]["eligible_memory_refs"]
    serialized = json.dumps(payload, ensure_ascii=False)
    assert "D:\\" not in serialized
    assert ".mp4" not in serialized
    assert "signed_url" not in serialized


def _loulan_fixture(tmp_path: Path) -> Path:
    root = tmp_path / "LoulanSceneAssets"
    (root / "manifests").mkdir(parents=True)
    (root / "docs").mkdir()
    (root / "human" / "rejected").mkdir(parents=True)
    (root / "asset_library" / "director_notes").mkdir(parents=True)
    (root / "reviews" / "B01-S01").mkdir(parents=True)
    (root / "runs" / "image2" / "failed" / "bad_route").mkdir(parents=True)
    (root / "prompts" / "image2").mkdir(parents=True)
    (root / "prompts" / "kling_i2v").mkdir(parents=True)

    _write_json(
        root / "project_manifest.json",
        {
            "schema_version": "0.1.0",
            "project_id": "loulan_scene_assets",
            "title": "Loulan time-control scene asset project",
            "target_format": "horizontal_16_9",
            "image_model_requested": "ChatGPT image2 built-in image generation tool",
            "video_model_requested": "Kling I2V",
            "current_phase": "keyframe_only_horizontal_16_9",
            "current_claim_level": "horizontal_keyframe_candidates_pending_human_review",
            "video_generation_status": "deferred_until_keyframe_approval",
        },
    )
    _write_json(
        root / "manifests" / "shot_list.json",
        {
            "shots": [
                {
                    "shot_id": "B01-S01",
                    "generation_block": 1,
                    "scene": "Loulan ruins",
                    "quality_status": "approved_keyframe",
                    "image2_prompt_path": "prompts/image2/B01-S01.txt",
                    "kling_i2v_prompt_path": "prompts/kling_i2v/B01-S01.txt",
                },
                {
                    "shot_id": "B01-S02",
                    "generation_block": 1,
                    "scene": "Loulan ruins",
                    "quality_status": "keyframe_candidate_pending_review",
                    "image2_prompt_path": "prompts/image2/B01-S02.txt",
                    "kling_i2v_prompt_path": "prompts/kling_i2v/B01-S02.txt",
                },
            ]
        },
    )
    _write_json(
        root / "manifests" / "character_assets.json",
        {
            "schema_version": "0.1.0",
            "artifact_type": "loulan_character_asset_manifest",
            "assets": [
                {
                    "asset_id": "zhou_tong_school_v1",
                    "character": "Zhou Tong",
                    "phase": "school_uniform",
                    "output_path": "human/zhou_tong_school_v1.png",
                    "asset_card": "asset_library/characters/zhou_tong_school_v1.md",
                    "review_card": "reviews/zhou_tong_school_v1/refinement_card.md",
                    "status": "approved",
                    "sha256": "sha-approved",
                },
                {
                    "asset_id": "guan_pingping_v2",
                    "character": "Guan Pingping",
                    "phase": "school_uniform",
                    "output_path": "human/guan_pingping_v2.png",
                    "asset_card": "asset_library/characters/guan_pingping_v2.md",
                    "review_card": "reviews/guan_pingping_v2/refinement_card.md",
                    "status": "candidate_pending_human_review",
                },
            ],
        },
    )
    (root / "human" / "rejected" / "guan_pingping_v1.png").write_text("not-image", encoding="utf-8")
    (root / "asset_library" / "director_notes" / "B01-S01_feedback.md").write_text("feedback", encoding="utf-8")
    (root / "reviews" / "B01-S01" / "director_art_card.md").write_text("review", encoding="utf-8")
    (root / "runs" / "image2" / "failed" / "bad_route" / "provider_failure_note.md").write_text("failed", encoding="utf-8")
    (root / "docs" / "image2_route_failure_and_workbench_plan_v0.md").write_text("route failure", encoding="utf-8")
    (root / "BACKLOG.md").write_text("Build API-backed Loulan image workbench", encoding="utf-8")
    return root


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
