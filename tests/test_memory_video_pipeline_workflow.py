from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from apps.cli.main import app


PROTOCOL_PATH = Path("examples/agentflow/memory_video_pipeline_protocol.example.json")


def test_cli_help_promotes_memory_video_pipeline_over_legacy_demo_surface() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0, result.output
    assert "memory-video-pipeline-package" in result.output
    assert "memory-evidence-reuse-review" in result.output
    assert "memory-advantage-demo-012-plan" not in result.output
    assert "memory-advantage-demo-015-plan" not in result.output
    assert "kling-i2v-smoke" not in result.output
    assert "minimax-image-smoke" not in result.output


def test_workflow_package_runs_no_call_chain_and_writes_feedback_event_draft(tmp_path) -> None:
    protocol_path = tmp_path / "protocol.json"
    artifacts_path = tmp_path / "artifacts.json"
    notes_path = tmp_path / "notes.json"
    protocol_path.write_text(PROTOCOL_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    artifacts_path.write_text(
        json.dumps(_artifact_manifest(tmp_path, run_count=2), ensure_ascii=False),
        encoding="utf-8",
    )
    notes_path.write_text(json.dumps(_notes(), ensure_ascii=False), encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "memory-video-pipeline-package",
            "--protocol",
            str(protocol_path),
            "--artifacts",
            str(artifacts_path),
            "--notes",
            str(notes_path),
            "--created-at",
            "2026-05-30T09:00:00+08:00",
            "--output",
            str(tmp_path / "package"),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Memory video pipeline package" in result.output
    assert "Provider calls: not started" in result.output
    assert "Feedback event draft: written" in result.output
    assert str(protocol_path) not in result.output
    assert str(artifacts_path) not in result.output
    assert str(notes_path) not in result.output

    expected = {
        "plan/protocol_summary.json",
        "plan/request_plan.json",
        "plan/review_plan.json",
        "plan/run_plan.json",
        "plan/memory_video_pipeline_report.md",
        "review/memory_video_pipeline_review.json",
        "review/memory_video_pipeline_review.md",
        "observation/memory_video_pipeline_human_observation.json",
        "observation/memory_video_pipeline_human_observation.md",
        "presentation/memory_video_pipeline_presentation_package.json",
        "presentation/memory_video_pipeline_presentation_brief.md",
        "presentation/slidev_insert.md",
        "feedback/memory_video_pipeline_feedback_event_draft.json",
        "feedback/memory_video_pipeline_feedback_event_draft.jsonl",
        "feedback/memory_video_pipeline_feedback_event_draft.md",
        "memory_video_pipeline_package_summary.json",
    }
    actual = {
        path.relative_to(tmp_path / "package").as_posix()
        for path in (tmp_path / "package").rglob("*")
        if path.is_file()
    }
    assert expected <= actual

    feedback = json.loads(
        (tmp_path / "package" / "feedback" / "memory_video_pipeline_feedback_event_draft.json").read_text(
            encoding="utf-8"
        )
    )
    assert feedback["artifact_type"] == "agentflow_feedback_event"
    assert feedback["feedback_id"] == "memory_video_pipeline_neon_rain_turnback_v1_feedback_draft"
    assert feedback["source"] == "human"
    assert feedback["target_type"] == "run"
    assert feedback["target_id"] == "memory_video_pipeline_neon_rain_turnback_v1"
    assert feedback["decision"] == "note"
    assert feedback["draft_status"] == "draft_not_persisted"
    assert feedback["writes_long_term_memory"] is False
    assert feedback["created_at"] == "2026-05-30T09:00:00+08:00"
    assert {
        "baseline_more_variable",
        "memory_backed_more_stable",
        "bounded_visual_signal",
        "not_human_acceptance",
    } <= set(feedback["reason_tags"])

    summary = json.loads(
        (tmp_path / "package" / "memory_video_pipeline_package_summary.json").read_text(encoding="utf-8")
    )
    assert summary["artifact_type"] == "agentflow_memory_video_pipeline_package"
    assert summary["provider_calls_started"] is False
    assert summary["writes_long_term_memory"] is False
    assert summary["feedback_event_draft_ref"] == "feedback/memory_video_pipeline_feedback_event_draft.json"

    serialized = "\n".join(path.read_text(encoding="utf-8") for path in (tmp_path / "package").rglob("*") if path.is_file())
    assert "D:\\Projects" not in serialized
    assert "https://" not in serialized
    assert "Bearer " not in serialized
    assert "data:image/" not in serialized
    assert "signed_url" not in serialized


def _artifact_manifest(root: Path, run_count: int) -> dict:
    artifacts = []
    for index in range(1, run_count + 1):
        run_id = f"recording_016_run_{index}"
        for lane_id in ["baseline", "memory_backed"]:
            manifest_path = root / run_id / lane_id / "kling_i2v_smoke_manifest.json"
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            manifest_path.write_text(
                json.dumps(_kling_manifest(run_id, lane_id), ensure_ascii=False),
                encoding="utf-8",
            )
            artifacts.append(
                {
                    "run_id": run_id,
                    "lane_id": lane_id,
                    "i2v_manifest_path": str(manifest_path),
                }
            )
    return {
        "schema_version": "0.1.0",
        "artifact_type": "agentflow_memory_video_pipeline_artifact_manifest",
        "artifacts": artifacts,
    }


def _kling_manifest(run_id: str, lane_id: str) -> dict:
    return {
        "schema_version": "kling_i2v_smoke_manifest.v1",
        "status": "succeeded",
        "service_id": "kling_i2v",
        "provider": "kling",
        "api_family": "i2v",
        "model": "kling-v3",
        "capability": "video",
        "task": {
            "task_id": f"{run_id}_{lane_id}",
            "task_status": "succeed",
        },
        "outputs": [
            {
                "candidate_id": "candidate_001",
                "video_path": "video_candidates/candidate_001.mp4",
                "byte_count": 30_000_000 + len(run_id) + len(lane_id),
                "sha256": f"sha256-{run_id}-{lane_id}",
                "content_type": "video/mp4",
                "provider_url_persisted": False,
            }
        ],
        "input_image": {
            "path_persisted": False,
            "byte_count": 242_694,
            "sha256": "same-source-keyframe-sha256",
        },
    }


def _notes() -> dict:
    return {
        "schema_version": "0.1.0",
        "artifact_type": "agentflow_memory_video_pipeline_human_observation_notes",
        "reviewer": "operator_visual_review",
        "observations": [
            {
                "criterion": "shot_structure_consistency",
                "verdict": "memory_backed_stronger",
                "note": "Baseline repeats varied more in camera path; memory-backed repeats kept the five checkpoints closer.",
            },
            {
                "criterion": "identity_anchor_retention",
                "verdict": "memory_backed_stronger",
                "note": "Memory-backed repeats recovered the same face and high ponytail more consistently after motion.",
            },
            {
                "criterion": "wardrobe_anchor_retention",
                "verdict": "memory_backed_stronger",
                "note": "Memory-backed repeats retained the white top, blue jeans, and white sneakers with less drift.",
            },
            {
                "criterion": "scene_anchor_retention",
                "verdict": "mixed",
                "note": "Both lanes kept neon rain, but memory-backed repeats aligned reflections and sign-light timing more closely.",
            },
            {
                "criterion": "occlusion_recovery_repeatability",
                "verdict": "memory_backed_stronger",
                "note": "After rain and light sweep occlusion, memory-backed repeats returned to a more similar readable character.",
            },
            {
                "criterion": "motion_physics_repeatability",
                "verdict": "mixed",
                "note": "Both lanes have model drift; memory-backed repeats were steadier, but this remains subjective visual evidence.",
            },
        ],
        "observed_signal_summary": {
            "baseline_more_variable": True,
            "memory_backed_more_stable": True,
            "residual_risk": "subjective_visual_review",
        },
        "claim_boundaries": {
            "human_acceptance": "not_acceptance",
            "business_validation": "not_validated",
            "quality_improvement_claim": "bounded_visual_signal_only",
            "durable_memory_runtime": "not_implemented",
        },
    }
