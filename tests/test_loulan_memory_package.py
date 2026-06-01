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
    assert package["project_audits"] == {
        "manifest_reference": {
            "status": "pass",
            "artifact_ref": "reviews/manifest_reference_audit.json",
            "report_ref": "reviews/manifest_reference_audit.md",
        },
        "text_encoding": {
            "status": "pass",
            "artifact_ref": "reviews/text_encoding_audit.json",
            "report_ref": "reviews/text_encoding_audit.md",
        },
        "phase_gate": {
            "status": "blocked_until_b01_human_review",
            "artifact_ref": "reviews/asset_governance_phase_audit.json",
            "report_ref": "reviews/asset_governance_phase_audit.md",
        },
    }
    assert package["feedback_loop_gates"]["b01"]["status"] == "blocked_pending_human_review"
    assert package["feedback_loop_gates"]["b01"]["pending_decisions"] == 5
    assert package["feedback_loop_gates"]["b01"]["context_projection_ready"] is False
    assert package["feedback_loop_gates"]["b01"]["source_ref"] == "manifests/afs_b01_feedback_loop_gate.json"
    crosswalk = package["feedback_loop_gates"]["b01_decision_crosswalk"]
    assert crosswalk["status"] == "blocked_pending_human_review"
    assert crosswalk["local_shot_gate"]["decision_count"] == 5
    assert crosswalk["afs_b01_import_gate"]["decision_count"] == 7
    assert crosswalk["afs_broader_decision_review_gate"]["decision_count"] == 47
    assert crosswalk["afs_broader_decision_review_gate"]["target_ref_count"] == 47
    assert crosswalk["source_ref"] == "manifests/afs_b01_decision_crosswalk.json"
    entrypoint = package["feedback_loop_gates"]["b01_operator_entrypoint"]
    assert entrypoint["status"] == "blocked_pending_human_review"
    assert entrypoint["source_ref"] == "manifests/b01_operator_entrypoint.json"
    assert (entrypoint["pending_decisions"], entrypoint["operator_steps"], entrypoint["blocked_until_count"]) == (5, 6, 4)
    assert (entrypoint["recommendations"], entrypoint["pending_operator_decisions"]) == (5, 5)
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
    assert package["feedback_loop_gates"]["b01"]["status"] == "blocked_pending_human_review"
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
    assert payload["project_audits"]["manifest_reference"]["status"] == "pass"
    assert payload["project_audits"]["text_encoding"]["status"] == "pass"
    assert payload["project_audits"]["phase_gate"]["status"] == "blocked_until_b01_human_review"
    assert payload["feedback_loop_gates"]["b01"]["provider_calls_started"] is False
    assert payload["feedback_loop_gates"]["b01_decision_crosswalk"]["afs_b01_import_gate"]["pending_count"] == 7
    assert payload["feedback_loop_gates"]["b01_operator_entrypoint"]["pending_operator_decisions"] == 5
    assert "asset:character_zhou_tong_school_v1" in payload["next_context_bundle_draft"]["eligible_memory_refs"]
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
            "manifest_reference_audit": "reviews/manifest_reference_audit.json",
            "manifest_reference_audit_report": "reviews/manifest_reference_audit.md",
            "manifest_reference_audit_status": "pass",
            "text_encoding_audit": "reviews/text_encoding_audit.json",
            "text_encoding_audit_report": "reviews/text_encoding_audit.md",
            "text_encoding_audit_status": "pass",
            "asset_governance_phase_audit": "reviews/asset_governance_phase_audit.json",
            "asset_governance_phase_audit_report": "reviews/asset_governance_phase_audit.md",
            "asset_governance_phase_audit_status": "blocked_until_b01_human_review",
        },
    )
    _write_json(
        root / "manifests" / "afs_b01_feedback_loop_gate.json",
        {
            "schema_version": "0.1.0",
            "artifact_type": "loulan_afs_b01_feedback_loop_gate",
            "status": "blocked_pending_human_review",
            "provider_calls_started": False,
            "writes_long_term_memory": False,
            "human_acceptance_recorded": False,
            "media_generation_started": False,
            "current_gate_summary": {
                "b01_decision_items": 5,
                "pending_decisions": 5,
                "approved_decisions": 0,
                "repair_requested": 0,
                "rejected_decisions": 0,
                "validation_status": "blocked_pending_human_review",
                "apply_status": "blocked_validation_not_ready",
                "afs_import_ready": False,
                "context_projection_ready": False,
            },
            "claim_boundary": {
                "human_acceptance": "not_recorded",
                "durable_memory_runtime": "not_implemented",
                "provider_smoke": "not_run",
            },
        },
    )
    _write_json(
        root / "manifests" / "afs_b01_decision_crosswalk.json",
        {
            "schema_version": "0.1.0",
            "artifact_type": "loulan_afs_b01_decision_crosswalk",
            "status": "blocked_pending_human_review",
            "provider_calls_started": False,
            "writes_long_term_memory": False,
            "human_acceptance_recorded": False,
            "media_generation_started": False,
            "decision_layers": [
                {
                    "layer_id": "loulan_local_b01_shot_gate",
                    "decision_count": 5,
                    "pending_count": 5,
                    "target_refs": ["shot:B01-S01", "shot:B01-S02", "shot:B01-S03", "shot:B01-S04", "shot:B01-S05"],
                    "current_blocker": "all five decisions are pending_human_review",
                },
                {
                    "layer_id": "afs_b01_import_gate",
                    "decision_count": 7,
                    "pending_count": 7,
                    "target_refs": ["shot:B01-S01", "shot:B01-S02", "shot:B01-S03", "shot:B01-S04", "shot:B01-S05", "character:zhou_tong_school_v1", "character:zhou_tong_qipao_front_v1"],
                    "current_blocker": "two Zhou Tong character slots still need explicit disposition",
                },
                {
                    "layer_id": "afs_broader_decision_review_gate",
                    "decision_count": 47,
                    "pending_count": 47,
                    "target_refs_summary": {"shot_slots": 5, "asset_slots": 42},
                    "current_blocker": "full review pack covers broad asset governance",
                },
            ],
            "next_step": "Human operator fills the five local B01 shot decisions first.",
        },
    )
    _write_json(
        root / "manifests" / "b01_operator_entrypoint.json",
        {
            "schema_version": "0.1.0",
            "artifact_type": "loulan_b01_operator_entrypoint",
            "status": "blocked_pending_human_review",
            "provider_calls_started": False,
            "writes_long_term_memory": False,
            "human_acceptance_recorded": False,
            "media_generation_started": False,
            "current_gate_summary": {"decision_items": 5, "pending_decisions": 5, "validation_status": "blocked_pending_human_review", "apply_status": "blocked_validation_not_ready", "next_context_status": "blocked_until_b01_human_review"},
            "ai_recommendation_summary": {"recommendations": 5, "operator_decisions_still_pending": 5},
            "operator_sequence": [{"step_id": "open_review_packet"}, {"step_id": "compare_ai_suggestions"}, {"step_id": "fill_decision_template"}, {"step_id": "validate_decisions"}, {"step_id": "dry_run_apply"}, {"step_id": "apply_after_ready"}],
            "blocked_until": ["all five B01 decision_items are filled by the human operator", "Loulan validation returns ready_for_apply", "Loulan apply dry-run returns ready_dry_run", "operator explicitly requests apply"],
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
