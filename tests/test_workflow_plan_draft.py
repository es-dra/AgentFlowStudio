from __future__ import annotations

import json

from narratocut.utils import write_json
from narratocut.workflow_engine.planner import draft_workflow_plan, write_workflow_plan


def test_draft_workflow_plan_from_workflow_yaml() -> None:
    plan = draft_workflow_plan(
        workflow_path="workflows/mock_text_to_slices.yaml",
        input_path="examples/demo_text/story.txt",
    )

    assert plan["schema_version"] == "0.1"
    assert plan["plan_id"].startswith("plan_")
    assert plan["status"] == "draft"
    assert plan["workflow"] == {
        "path": "workflows/mock_text_to_slices.yaml",
        "name": "mock_text_to_slices",
    }
    assert plan["input"] == {
        "path": "examples/demo_text/story.txt",
        "type": "file",
    }
    assert [step["step_id"] for step in plan["steps"]] == [
        "analyze_hooks",
        "generate_scripts",
        "generate_clip_plans",
        "mock_slice",
    ]
    assert all(step["execution_status"] == "not_started" for step in plan["steps"])
    assert plan["steps"][0]["tool"] == "analyze_hooks"
    assert plan["steps"][0]["expected_outputs"] == ["hooks.json"]
    assert "run_manifest.json" in plan["artifacts"]["expected"]
    assert "no_execution" in plan["constraints"]
    assert "no_ffmpeg" in plan["constraints"]
    assert plan["created_by"] == "ncut draft-plan"
    assert "\\" not in json.dumps(plan, ensure_ascii=False)


def test_write_workflow_plan_only_writes_plan_file(tmp_path) -> None:
    output_path = tmp_path / "reports" / "workflow_plan.json"

    written_path = write_workflow_plan(
        output_path=output_path,
        workflow_path="workflows/mock_text_to_slices.yaml",
        input_path="examples/demo_text/story.txt",
    )

    assert written_path == output_path
    plan = json.loads(output_path.read_text(encoding="utf-8"))
    assert plan["status"] == "draft"
    assert not (tmp_path / "reports" / "run_manifest.json").exists()
    assert not (tmp_path / "reports" / "trace.json").exists()
    assert not (tmp_path / "reports" / "quality_report.json").exists()


def test_draft_workflow_plan_returns_invalid_for_invalid_workflow(tmp_path) -> None:
    workflow_path = tmp_path / "invalid_workflow.yaml"
    workflow_path.write_text("name: broken\nsteps: []\n", encoding="utf-8")

    plan = draft_workflow_plan(
        workflow_path=workflow_path,
        input_path="examples/demo_text/story.txt",
    )

    assert plan["status"] == "invalid"
    assert plan["steps"] == []
    assert plan["errors"]
    assert plan["constraints"] == [
        "draft_only",
        "no_execution",
        "no_ffmpeg",
        "no_file_mutation_except_plan_output",
    ]


def test_draft_workflow_plan_uses_tool_catalog_when_available(tmp_path) -> None:
    catalog_path = tmp_path / "tool_catalog.yaml"
    catalog_path.write_text(
        """
tools:
  - name: analyze_hooks
    description: Custom hook analyzer purpose.
    entrypoints:
      workflow_node: analyze_hooks
    input_artifacts:
      - text_file
    output_artifacts:
      - custom_hooks.json
""".strip(),
        encoding="utf-8",
    )

    plan = draft_workflow_plan(
        workflow_path="workflows/mock_roi_to_script.yaml",
        input_path="examples/demo_text/story.txt",
        tool_catalog_path=catalog_path,
    )

    assert plan["steps"][0]["purpose"] == "Custom hook analyzer purpose."
    assert plan["steps"][0]["expected_outputs"] == ["hooks.json"]


def test_write_workflow_plan_accepts_prebuilt_invalid_plan(tmp_path) -> None:
    output_path = tmp_path / "workflow_plan.json"
    plan = {
        "schema_version": "0.1",
        "status": "invalid",
        "steps": [],
    }

    write_workflow_plan(
        output_path=output_path,
        workflow_path="missing.yaml",
        input_path="missing.txt",
        plan=plan,
    )

    saved = json.loads(output_path.read_text(encoding="utf-8"))
    assert saved["status"] == "invalid"


def test_draft_workflow_plan_lists_real_clip_outputs() -> None:
    plan = draft_workflow_plan(
        workflow_path="workflows/clip_plan_to_real_clips.yaml",
        input_path="examples/demo_slicing/clip_plan_to_real_clips_input.example.json",
    )

    assert plan["status"] == "draft"
    assert [step["tool"] for step in plan["steps"]] == [
        "load_video",
        "load_clip_plan",
        "probe_video_metadata",
        "validate_clip_plan",
        "real_slice_video",
    ]
    expected = plan["artifacts"]["expected"]
    assert "video_metadata.json" in expected
    assert "clip_plan_validation.json" in expected
    assert "real_slice_manifest.json" in expected
    assert "clips" in expected


def test_draft_workflow_plan_lists_video_to_real_clip_outputs() -> None:
    plan = draft_workflow_plan(
        workflow_path="workflows/video_to_real_clips.yaml",
        input_path="examples/demo_asr/video_to_real_clips_input.example.json",
    )

    assert plan["status"] == "draft"
    assert [step["tool"] for step in plan["steps"]] == [
        "load_video",
        "extract_audio",
        "transcribe_audio_mock",
        "write_transcript",
        "load_roi_config",
        "detect_highlights",
        "rank_highlights_by_roi",
        "generate_clip_plan_from_highlights",
        "write_highlight_plan",
        "write_clip_plan",
        "probe_video_metadata",
        "validate_clip_plan",
        "real_slice_video",
    ]
    expected = plan["artifacts"]["expected"]
    for artifact in [
        "audio_manifest.json",
        "transcript.json",
        "highlight_plan.json",
        "clip_plan.json",
        "video_metadata.json",
        "clip_plan_validation.json",
        "real_slice_manifest.json",
        "clips",
    ]:
        assert artifact in expected


def test_draft_workflow_plan_lists_final_video_outputs() -> None:
    plan = draft_workflow_plan(
        workflow_path="workflows/clips_to_final_video.yaml",
        input_path="examples/demo_assembly/clips_to_final_video_input.example.json",
    )

    assert plan["status"] == "draft"
    assert [step["tool"] for step in plan["steps"]] == [
        "load_real_slice_manifest",
        "generate_assembly_plan",
        "concat_clips",
        "probe_final_video",
    ]
    expected = plan["artifacts"]["expected"]
    for artifact in [
        "real_slice_manifest.json",
        "assembly_plan.json",
        "concat_list.txt",
        "final_video_manifest.json",
        "final_video.mp4",
    ]:
        assert artifact in expected


def test_draft_workflow_plan_lists_subtitle_outputs() -> None:
    plan = draft_workflow_plan(
        workflow_path="workflows/transcript_to_subtitles.yaml",
        input_path="examples/demo_subtitles/transcript_to_subtitles_input.example.json",
    )

    assert plan["status"] == "draft"
    assert [step["tool"] for step in plan["steps"]] == [
        "load_transcript",
        "write_subtitles",
    ]
    expected = plan["artifacts"]["expected"]
    assert "subtitles.srt" in expected
    assert "subtitle_manifest.json" in expected


def test_draft_workflow_plan_lists_candidate_window_outputs() -> None:
    plan = draft_workflow_plan(
        workflow_path="workflows/transcript_to_candidate_windows.yaml",
        input_path="examples/demo_highlight/transcript_candidate_windows_input.example.json",
    )

    assert plan["status"] == "draft"
    assert [step["tool"] for step in plan["steps"]] == [
        "load_transcript",
        "generate_candidate_windows",
    ]
    assert "candidate_windows.json" in plan["artifacts"]["expected"]


def test_draft_workflow_plan_lists_ocr_scoring_outputs() -> None:
    plan = draft_workflow_plan(
        workflow_path="workflows/video_subtitle_ocr_to_highlight_plan.yaml",
        input_path="examples/demo_ocr/video_subtitle_ocr_to_highlight_plan_input.example.json",
    )

    assert plan["status"] == "draft"
    assert [step["tool"] for step in plan["steps"]] == [
        "load_video",
        "build_ocr_transcript",
        "write_ocr_transcript",
        "generate_candidate_windows",
        "score_candidate_windows",
        "write_highlight_score_report",
        "write_selection_diagnostics",
        "write_highlight_plan",
    ]
    expected = plan["artifacts"]["expected"]
    for artifact in [
        "ocr_transcript.json",
        "ocr_transcript_manifest.json",
        "candidate_windows.json",
        "highlight_score_report.json",
        "selection_diagnostics.json",
        "highlight_plan.json",
    ]:
        assert artifact in expected


def test_draft_workflow_plan_lists_cover_outputs() -> None:
    plan = draft_workflow_plan(
        workflow_path="workflows/final_video_to_cover.yaml",
        input_path="examples/demo_cover/final_video_to_cover_input.example.json",
    )

    assert plan["status"] == "draft"
    assert [step["tool"] for step in plan["steps"]] == ["export_cover"]
    expected = plan["artifacts"]["expected"]
    assert "cover_manifest.json" in expected
    assert "cover.jpg" in expected


def test_draft_workflow_plan_lists_bgm_mix_outputs() -> None:
    plan = draft_workflow_plan(
        workflow_path="workflows/final_video_with_bgm.yaml",
        input_path="examples/demo_bgm/final_video_with_bgm_input.example.json",
    )

    assert plan["status"] == "draft"
    assert [step["tool"] for step in plan["steps"]] == ["mix_bgm", "probe_bgm_mix"]
    expected = plan["artifacts"]["expected"]
    assert "audio_mix_manifest.json" in expected
    assert "final_video_with_bgm.mp4" in expected


def test_draft_workflow_plan_lists_finished_package_outputs() -> None:
    plan = draft_workflow_plan(
        workflow_path="workflows/final_video_package.yaml",
        input_path="examples/demo_package/final_video_package_input.example.json",
    )

    assert plan["status"] == "draft"
    assert [step["tool"] for step in plan["steps"]] == ["write_finished_package", "write_package_report"]
    expected = plan["artifacts"]["expected"]
    assert "finished_package_manifest.json" in expected
    assert "package_report.md" in expected
