from __future__ import annotations

import json
from pathlib import Path


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
        root / "reviews" / "manifest_reference_audit.json",
        {
            "artifact_type": "loulan_manifest_reference_audit",
            "status": "pass",
            "summary": {
                "json_files_checked": 14,
                "registry_assets": 87,
                "errors": 0,
                "missing_sha256": 0,
                "missing_files": 0,
                "absolute_refs": 0,
                "secret_like_refs": 0,
                "manifest_string_issues": 0,
                "invalid_asset_types": 0,
                "invalid_statuses": 0,
            },
        },
    )
    _write_json(
        root / "reviews" / "text_encoding_audit.json",
        {
            "artifact_type": "loulan_text_encoding_audit",
            "status": "pass",
            "summary": {
                "text_files_checked": 268,
                "decode_errors": 0,
                "marker_hits": 0,
                "errors": 0,
            },
        },
    )
    _write_json(
        root / "reviews" / "asset_governance_phase_audit.json",
        {
            "artifact_type": "loulan_asset_governance_phase_audit",
            "status": "blocked_until_b01_human_review",
            "summary": {
                "phases": 5,
                "passed": 4,
                "blocked_expected": 1,
                "failures": 0,
                "registry_assets": 87,
                "eligible_context_refs": 3,
                "blocked_context_refs": 84,
                "pending_b01_decisions": 5,
            },
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
                {"shot_id": "B01-S01", "generation_block": 1, "scene": "Loulan ruins", "quality_status": "approved_keyframe", "image2_prompt_path": "prompts/image2/B01-S01.txt", "kling_i2v_prompt_path": "prompts/kling_i2v/B01-S01.txt"},
                {"shot_id": "B01-S02", "generation_block": 1, "scene": "Loulan ruins", "quality_status": "keyframe_candidate_pending_review", "image2_prompt_path": "prompts/image2/B01-S02.txt", "kling_i2v_prompt_path": "prompts/kling_i2v/B01-S02.txt"},
            ]
        },
    )
    _write_json(
        root / "manifests" / "character_assets.json",
        {
            "schema_version": "0.1.0",
            "artifact_type": "loulan_character_asset_manifest",
            "assets": [
                {"asset_id": "zhou_tong_school_v1", "character": "Zhou Tong", "phase": "school_uniform", "output_path": "human/zhou_tong_school_v1.png", "asset_card": "asset_library/characters/zhou_tong_school_v1.md", "review_card": "reviews/zhou_tong_school_v1/refinement_card.md", "status": "approved", "sha256": "sha-approved"},
                {"asset_id": "guan_pingping_v2", "character": "Guan Pingping", "phase": "school_uniform", "output_path": "human/guan_pingping_v2.png", "asset_card": "asset_library/characters/guan_pingping_v2.md", "review_card": "reviews/guan_pingping_v2/refinement_card.md", "status": "candidate_pending_human_review"},
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
