from __future__ import annotations

import json

import pytest

from narratocut.audio_sop import (
    AudioExtractionConfig,
    build_ffmpeg_audio_extract_command,
    extract_audio_from_video,
)


def test_build_ffmpeg_audio_extract_command_uses_phase11_audio_contract() -> None:
    command = build_ffmpeg_audio_extract_command(
        input_video="input.mp4",
        output_audio="audio.wav",
        config=AudioExtractionConfig(ffmpeg_executable="ffmpeg-test", overwrite=False),
    )

    assert command == [
        "ffmpeg-test",
        "-n",
        "-i",
        "input.mp4",
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        "audio.wav",
    ]


def test_mock_audio_extraction_writes_audio_artifact_and_manifest(tmp_path) -> None:
    source_video = tmp_path / "input.mp4"
    source_video.write_text("not real video bytes", encoding="utf-8")

    artifact = extract_audio_from_video(
        input_video=source_video,
        output_dir=tmp_path / "run",
        config=AudioExtractionConfig(execution_mode="mock"),
    )

    assert artifact.status == "mocked"
    assert artifact.extraction_mode == "mock"
    assert artifact.audio_path == "audio/audio.wav"
    assert (tmp_path / "run" / "audio" / "audio.wav").is_file()

    manifest = json.loads((tmp_path / "run" / "audio_manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "mocked"
    assert manifest["source_video"] == str(source_video)
    assert manifest["audio_path"] == "audio/audio.wav"


def test_audio_extraction_config_rejects_unknown_execution_mode() -> None:
    with pytest.raises(ValueError, match="execution_mode must be ffmpeg or mock"):
        AudioExtractionConfig(execution_mode="remote")  # type: ignore[arg-type]
