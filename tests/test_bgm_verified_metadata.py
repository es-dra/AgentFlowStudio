from __future__ import annotations

import json
from pathlib import Path

from narratocut.workflow_engine.bgm_nodes import mix_bgm_node
from narratocut.workflow_engine.context import WorkflowContext
from narratocut.workflow_engine.definitions import WorkflowStepDefinition
from narratocut.utils import write_json


def test_mix_bgm_node_records_verified_local_bgm_metadata(tmp_path: Path, monkeypatch) -> None:
    final_video = tmp_path / "final_video.mp4"
    bgm = tmp_path / "bgm.mp3"
    final_video.write_bytes(b"video")
    bgm.write_bytes(b"bgm")
    metadata_path = tmp_path / "bgm.metadata.json"
    write_json(
        metadata_path,
        {
            "quality_verified": True,
            "verification_method": "manual_local_review",
            "license": "local_test_asset",
            "mood": "cinematic",
        },
    )
    context = WorkflowContext(
        run_id="run",
        workflow_name="wf",
        output_dir=tmp_path / "run",
        inputs={
            "final_video_path": str(final_video),
            "bgm_path": str(bgm),
            "bgm_metadata_path": str(metadata_path),
        },
    )
    step = WorkflowStepDefinition(
        id="mix_bgm",
        type="mix_bgm",
        inputs={"video": "final_video_path", "bgm": "bgm_path", "bgm_metadata": "bgm_metadata_path"},
        outputs={"audio_mix_manifest": "audio_mix_manifest.json", "final_video": "final_video_with_bgm.mp4"},
    )

    def fake_mix_bgm_into_video(**kwargs):  # noqa: ANN003, ANN202
        output = context.output_dir / "final_video_with_bgm.mp4"
        output.write_bytes(b"mixed")
        return {
            "status": "succeeded",
            "source_video": str(final_video),
            "bgm_path": str(bgm),
            "output_video": "final_video_with_bgm.mp4",
            "errors": [],
        }

    monkeypatch.setattr("narratocut.workflow_engine.bgm_nodes.check_ffmpeg_available", lambda executable="ffmpeg": _ffmpeg_info())
    monkeypatch.setattr("narratocut.workflow_engine.bgm_nodes.mix_bgm_into_video", fake_mix_bgm_into_video)

    mix_bgm_node(step, context)

    manifest = json.loads((context.output_dir / "audio_mix_manifest.json").read_text(encoding="utf-8"))
    assert manifest["quality_verified"] is True
    assert manifest["bgm_metadata"]["verification_method"] == "manual_local_review"
    assert manifest["bgm_metadata"]["license"] == "local_test_asset"


def _ffmpeg_info():
    from narratocut.slicing_sop.ffmpeg_probe import FFmpegInfo

    return FFmpegInfo(available=True, executable="ffmpeg", version="test", raw_output="test", error=None)
