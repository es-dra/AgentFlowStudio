from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from agentflow_studio.schemas import (
    Asset,
    ClipPlan,
    ClipSegment,
    CostRecord,
    EvidenceCard,
    ExportPackage,
    GateResult,
    GeneratedVideo,
    Hook,
    Project,
    ShortVideoScript,
    StepResult,
    TaskPacket,
    WorkflowRun,
)


def roundtrip(model):
    dumped = model.model_dump_json()
    return type(model).model_validate_json(dumped)


def test_major_schemas_create_and_roundtrip_json() -> None:
    created_at = datetime(2026, 5, 16, tzinfo=timezone.utc)
    project = Project(project_id="proj_001", project_name="Demo Drama", project_type="ai_drama")
    asset = Asset(asset_id="asset_001", project_id="proj_001", asset_type="subtitle", path="data/raw/demo.srt")
    hook = Hook(
        hook_id="hook_001",
        project_id="proj_001",
        hook_type="身份反转",
        plot_summary="女主身份反转。",
        core_conflict="众人误判她的身份。",
        user_trigger="身份反差",
        recommended_opening="所有人都看错了她。",
        recommended_ending="更大的反转还在后面。",
        score=0.82,
    )
    script = ShortVideoScript(
        script_id="script_001",
        project_id="proj_001",
        hook_id="hook_001",
        title="她被所有人看轻",
        cover_text="身份反转",
        opening_3s="所有人都以为她输了。",
        cta="点进去看完整反转。",
    )
    segment = ClipSegment(source_video="data/raw/demo.mp4", start_sec=10, end_sec=70)
    clip_plan = ClipPlan(
        clip_plan_id="clip_001",
        project_id="proj_001",
        hook_id="hook_001",
        title="她被所有人看轻",
        cover_text="身份反转",
        segments=[segment],
    )
    video = GeneratedVideo(
        video_id="video_001",
        project_id="proj_001",
        file_path="data/outputs/run/videos/video_001.mp4",
        duration_sec=60,
        width=1080,
        height=1920,
    )
    package = ExportPackage(
        package_id="pkg_001",
        run_id="run_001",
        project_id="proj_001",
        output_dir="data/outputs/run_001",
        videos=[video],
        metadata_path="data/outputs/run_001/metadata.json",
    )
    cost = CostRecord(cost_id="cost_001", run_id="run_001", provider="mock", status="recorded")
    step = StepResult(step_id="analyze_hooks", step_type="hook_analysis", status="success")
    run = WorkflowRun(
        run_id="run_001",
        workflow_name="demo_ai_drama_promo",
        status="success",
        steps=[step],
    )
    task = TaskPacket(
        task_id="task_001",
        task_type="hook_analysis",
        run_id="run_001",
        input_refs=["data/raw/demo.srt"],
        expected_outputs=["hooks.json"],
    )
    evidence = EvidenceCard(
        evidence_id="ev_001",
        task_id="task_001",
        run_id="run_001",
        step_id="analyze_hooks",
        input_refs=["data/raw/demo.srt"],
        output_refs=["hooks.json"],
    )
    gate = GateResult(gate_id="gate_001", task_id="task_001", passed=True, score=0.9)
    models = [
        project,
        asset,
        hook,
        script,
        segment,
        clip_plan,
        video,
        package,
        cost,
        run,
        step,
        task,
        evidence,
        gate,
    ]

    for model in models:
        assert roundtrip(model) == model


def test_clip_segment_requires_end_after_start() -> None:
    with pytest.raises(ValidationError):
        ClipSegment(source_video="data/raw/demo.mp4", start_sec=10, end_sec=10)


def test_hook_score_must_be_between_zero_and_one() -> None:
    with pytest.raises(ValidationError):
        Hook(
            hook_id="hook_bad",
            project_id="proj_001",
            hook_type="身份反转",
            plot_summary="summary",
            core_conflict="conflict",
            user_trigger="trigger",
            recommended_opening="opening",
            recommended_ending="ending",
            score=1.2,
        )


def test_gate_score_must_be_between_zero_and_one() -> None:
    with pytest.raises(ValidationError):
        GateResult(gate_id="gate_bad", task_id="task_001", passed=False, score=-0.1)


def test_workflow_run_rejects_invalid_status() -> None:
    with pytest.raises(ValidationError):
        WorkflowRun(run_id="run_bad", workflow_name="demo", status="done")


def test_step_result_rejects_invalid_status() -> None:
    with pytest.raises(ValidationError):
        StepResult(step_id="step_bad", step_type="mock", status="done")
