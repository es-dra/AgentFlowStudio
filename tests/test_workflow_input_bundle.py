from __future__ import annotations

from narratocut.workflow_engine.input_bundle import load_workflow_inputs
from narratocut.utils import write_json


def test_load_workflow_inputs_keeps_text_files_as_legacy_input(tmp_path) -> None:
    text_path = tmp_path / "story.txt"
    text_path.write_text("story", encoding="utf-8")

    inputs = load_workflow_inputs(text_path)

    assert inputs == {"input_text_file": str(text_path)}


def test_load_workflow_inputs_flattens_real_video_bundle(tmp_path) -> None:
    bundle_path = tmp_path / "input.json"
    write_json(
        bundle_path,
        {
            "project": {"project_id": "demo_real_video", "name": "Demo"},
            "video": {"path": "data/raw/demo_real_video/input.mp4"},
            "roi": {"path": "examples/demo_real_video/roi_config.json"},
            "clip_plan": {"path": "examples/demo_real_video/clip_plan.json"},
            "output": {"clips_dir": "clips"},
        },
    )

    inputs = load_workflow_inputs(bundle_path)

    assert inputs["project_id"] == "demo_real_video"
    assert inputs["project_name"] == "Demo"
    assert inputs["input_video_file"] == "data/raw/demo_real_video/input.mp4"
    assert inputs["roi_config"] == "examples/demo_real_video/roi_config.json"
    assert inputs["clip_plan"] == "examples/demo_real_video/clip_plan.json"
    assert inputs["output_clips_dir"] == "clips"
