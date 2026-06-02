from __future__ import annotations

import json
from pathlib import Path

from apps.cli.workflow_commands import run_workflow_from_cli
from agentflow_studio.harness.inspection import inspect_run
from agentflow_studio.harness.reviewer import review_run, write_review_report
from agentflow_studio.package_sop import write_package_report
from agentflow_studio.utils import write_json
from agentflow_studio.workflow_engine import load_workflow
from agentflow_studio.workflow_engine.planner import draft_workflow_plan


WORKFLOW = Path("workflows/final_video_package.yaml")


def test_final_video_package_workflow_definition_is_manifest_only() -> None:
    workflow = load_workflow(WORKFLOW)

    assert workflow.mode == "final_video_package"
    assert workflow.quality_profile == "finished_package"
    assert workflow.metadata["kind"] == "component"
    step_types = [step.type for step in workflow.steps]
    assert step_types == ["write_finished_package", "write_package_report"]
    forbidden_fragments = [
        "ffmpeg",
        "probe",
        "assemble",
        "concat",
        "burn",
        "mix",
        "subtitle",
        "bgm",
        "cover",
        "remote_asr",
        "openai",
        "multimodal",
    ]
    assert not any(fragment in step for step in step_types for fragment in forbidden_fragments)


def test_final_video_package_workflow_writes_package_manifest(tmp_path) -> None:
    input_path = _write_input_bundle(tmp_path, include_optional=True)
    output_dir = tmp_path / "package_run"

    status, _ = run_workflow_from_cli(
        workflow_path=WORKFLOW,
        input_path=input_path,
        output_dir=output_dir,
    )

    assert status == "success"
    for artifact in [
        "finished_package_manifest.json",
        "package_report.md",
        "manifest.json",
        "run_manifest.json",
        "trace.json",
    ]:
        assert (output_dir / artifact).is_file()

    package = json.loads((output_dir / "finished_package_manifest.json").read_text(encoding="utf-8"))
    run_manifest = json.loads((output_dir / "run_manifest.json").read_text(encoding="utf-8"))

    assert package["status"] == "succeeded"
    assert package["package_id"] == "demo_package"
    assert package["primary_video"]["role"] == "final_video"
    assert package["primary_video"]["path"].endswith("final_video.mp4")
    assert {item["role"] for item in package["assets"]} >= {
        "final_video",
        "subtitled_video",
        "bgm_video",
        "cover_image",
        "review_report",
    }
    assert all(item["exists"] is True for item in package["assets"])
    assert run_manifest["workflow_mode"] == "final_video_package"
    assert run_manifest["quality_profile"] == "finished_package"
    assert run_manifest["artifacts"]["finished_package_manifest"] == "finished_package_manifest.json"
    assert run_manifest["artifacts"]["package_report"] == "package_report.md"
    report_text = (output_dir / "package_report.md").read_text(encoding="utf-8")
    assert "# AgentFlow Studio Package Report" in report_text
    assert "demo_package" in report_text
    assert "- Workflow: workflows/final_video_package.yaml" in report_text
    assert "final_video" in report_text

    inspection = inspect_run(output_dir)
    review = review_run(output_dir)
    write_review_report(output_dir, review)
    write_package_report(output_dir)
    refreshed_report = (output_dir / "package_report.md").read_text(encoding="utf-8")
    assert inspection["status"] == "pass"
    assert review["status"] == "passed"
    assert "- Quality status: pass" in refreshed_report
    assert "- Review status: passed" in refreshed_report
    assert "finished_package_outputs" in {section["name"] for section in review["sections"]}


def test_finished_package_records_quality_evidence_paths(tmp_path) -> None:
    real_slice = tmp_path / "real_slice_manifest.json"
    clip_plan = tmp_path / "clip_plan.json"
    subtitle_manifest = tmp_path / "subtitle_manifest.json"
    audio_mix_manifest = tmp_path / "audio_mix_manifest.json"
    final_video_manifest = tmp_path / "final_video_manifest.json"
    for path in [real_slice, clip_plan, subtitle_manifest, audio_mix_manifest, final_video_manifest]:
        write_json(path, {"status": "succeeded"})
    input_path = _write_input_bundle(
        tmp_path,
        include_optional=True,
        evidence={
            "real_slice_manifest_path": real_slice,
            "clip_plan_path": clip_plan,
            "subtitle_manifest_path": subtitle_manifest,
            "audio_mix_manifest_path": audio_mix_manifest,
            "final_video_manifest_path": final_video_manifest,
        },
    )
    output_dir = tmp_path / "package_run"

    status, _ = run_workflow_from_cli(
        workflow_path=WORKFLOW,
        input_path=input_path,
        output_dir=output_dir,
    )

    assert status == "success"
    package = json.loads((output_dir / "finished_package_manifest.json").read_text(encoding="utf-8"))
    assert package["evidence"] == {
        "real_slice_manifest": str(real_slice).replace("\\", "/"),
        "clip_plan": str(clip_plan).replace("\\", "/"),
        "subtitle_manifest": str(subtitle_manifest).replace("\\", "/"),
        "audio_mix_manifest": str(audio_mix_manifest).replace("\\", "/"),
        "final_video_manifest": str(final_video_manifest).replace("\\", "/"),
    }


def test_final_video_package_fails_when_primary_final_video_missing(tmp_path) -> None:
    input_path = _write_input_bundle(tmp_path, missing_final_video=True)
    output_dir = tmp_path / "package_run"

    status, _ = run_workflow_from_cli(
        workflow_path=WORKFLOW,
        input_path=input_path,
        output_dir=output_dir,
    )

    assert status == "failed"
    package = json.loads((output_dir / "finished_package_manifest.json").read_text(encoding="utf-8"))
    assert package["status"] == "failed"
    assert any("final_video_missing" in error for error in package["errors"])


def test_finished_package_review_fails_when_declared_optional_asset_missing(tmp_path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "final_video.mp4").write_bytes(b"fake final video")
    _write_package_run_manifest(run_dir)
    write_json(run_dir / "manifest.json", {"run_id": "run", "status": "success"})
    write_json(run_dir / "trace.json", {"steps": [{"step_id": "write_finished_package", "status": "success"}]})
    write_json(
        run_dir / "finished_package_manifest.json",
        {
            "schema_version": "0.1",
            "status": "succeeded",
            "package_id": "pkg",
            "primary_video": {"role": "final_video", "path": "final_video.mp4", "exists": True},
            "assets": [
                {"role": "final_video", "path": "final_video.mp4", "required": True, "exists": True},
                {"role": "cover_image", "path": "cover.jpg", "required": False, "exists": True},
            ],
            "errors": [],
            "warnings": [],
            "manifest_path": "finished_package_manifest.json",
        },
    )

    inspection = inspect_run(run_dir)
    review = review_run(run_dir)

    assert inspection["status"] == "fail"
    assert review["status"] == "failed"
    package_section = next(section for section in review["sections"] if section["name"] == "finished_package_outputs")
    failed_ids = {check["id"] for check in package_section["checks"] if check["status"] == "failed"}
    assert "finished_package_asset_cover_image_exists" in failed_ids


def test_draft_workflow_plan_lists_finished_package_outputs() -> None:
    plan = draft_workflow_plan(
        workflow_path=WORKFLOW,
        input_path="examples/demo_package/final_video_package_input.example.json",
    )

    assert plan["status"] == "draft"
    assert [step["tool"] for step in plan["steps"]] == ["write_finished_package", "write_package_report"]
    expected = plan["artifacts"]["expected"]
    assert "finished_package_manifest.json" in expected
    assert "package_report.md" in expected


def _write_input_bundle(
    tmp_path: Path,
    *,
    include_optional: bool = False,
    missing_final_video: bool = False,
    evidence: dict[str, Path] | None = None,
) -> Path:
    final_video = tmp_path / "final_video.mp4"
    if not missing_final_video:
        final_video.write_bytes(b"fake final video")
    payload = {
        "package_id": "demo_package",
        "final_video_path": str(final_video),
    }
    if include_optional:
        subtitled = tmp_path / "final_video_with_subtitles.mp4"
        bgm = tmp_path / "final_video_with_bgm.mp4"
        cover = tmp_path / "cover.jpg"
        review = tmp_path / "review_report.json"
        subtitled.write_bytes(b"fake subtitled video")
        bgm.write_bytes(b"fake bgm video")
        cover.write_bytes(b"fake cover")
        write_json(review, {"status": "passed"})
        payload.update(
            {
                "subtitled_video_path": str(subtitled),
                "bgm_video_path": str(bgm),
                "cover_path": str(cover),
                "review_report_path": str(review),
            }
        )
    for key, path in (evidence or {}).items():
        payload[key] = str(path)
    input_path = tmp_path / "final_video_package_input.json"
    write_json(input_path, payload)
    return input_path


def _write_package_run_manifest(run_dir: Path) -> None:
    write_json(
        run_dir / "run_manifest.json",
        {
            "run_id": "run",
            "workflow": "workflows/final_video_package.yaml",
            "workflow_mode": "final_video_package",
            "quality_profile": "finished_package",
            "artifacts": {
                "finished_package_manifest": "finished_package_manifest.json",
            },
        },
    )
