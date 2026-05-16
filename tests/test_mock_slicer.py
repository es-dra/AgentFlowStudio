from __future__ import annotations

import json

from narratocut.slicing_sop import generate_clip_plans_from_scripts, mock_slice_clip_plans

from tests.test_clip_plan_generation import make_scripts


def test_mock_slice_clip_plans_writes_manifest_and_clip_files(tmp_path) -> None:
    plans = generate_clip_plans_from_scripts(make_scripts())

    manifest = mock_slice_clip_plans(plans, tmp_path)

    manifest_path = tmp_path / "slice_manifest.json"
    clips_dir = tmp_path / "clips"
    assert manifest_path.is_file()
    assert clips_dir.is_dir()
    assert manifest["status"] == "success"
    assert manifest["clip_count"] == 3
    assert len(manifest["clips"]) == 3

    for clip in manifest["clips"]:
        clip_path = tmp_path / clip["file_path"]
        assert clip_path.suffix == ".txt"
        assert clip_path.is_file()
        assert "MOCK CLIP" in clip_path.read_text(encoding="utf-8")

    loaded_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert loaded_manifest["clip_count"] == len(plans)
    assert loaded_manifest["clips"][0]["clip_plan_id"] == "clip_plan_script_001"
