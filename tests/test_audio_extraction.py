from __future__ import annotations

import json
import subprocess

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
    assert manifest["metadata"]["executed"] is False
    assert manifest["metadata"]["ffmpeg_command"] == []
    assert manifest["metadata"]["absolute_audio_path"] == str(tmp_path / "run" / "audio" / "audio.wav")


def test_ffmpeg_audio_extraction_executes_command_and_records_manifest(tmp_path, monkeypatch) -> None:
    source_video = tmp_path / "input.mp4"
    source_video.write_text("not real video bytes", encoding="utf-8")
    calls: list[list[str]] = []

    def fake_run(command, capture_output, text, check):
        calls.append(command)
        output_path = tmp_path / "run" / "audio" / "audio.wav"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"fake wav")
        return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

    monkeypatch.setattr("narratocut.audio_sop.extractor.subprocess.run", fake_run)

    artifact = extract_audio_from_video(
        input_video=source_video,
        output_dir=tmp_path / "run",
        config=AudioExtractionConfig(ffmpeg_executable="ffmpeg-test", execution_mode="ffmpeg"),
    )

    manifest = json.loads((tmp_path / "run" / "audio_manifest.json").read_text(encoding="utf-8"))

    assert artifact.status == "succeeded"
    assert calls == [manifest["metadata"]["ffmpeg_command"]]
    assert manifest["extraction_mode"] == "ffmpeg"
    assert manifest["metadata"]["executed"] is True
    assert manifest["metadata"]["returncode"] == 0
    assert (tmp_path / "run" / "audio" / "audio.wav").is_file()


def test_ffmpeg_audio_extraction_records_failed_execution_metadata(tmp_path, monkeypatch) -> None:
    source_video = tmp_path / "input.mp4"
    source_video.write_text("not real video bytes", encoding="utf-8")

    def fake_run(command, capture_output, text, check):
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="bad input")

    monkeypatch.setattr("narratocut.audio_sop.extractor.subprocess.run", fake_run)

    artifact = extract_audio_from_video(
        input_video=source_video,
        output_dir=tmp_path / "run",
        config=AudioExtractionConfig(ffmpeg_executable="ffmpeg-test", execution_mode="ffmpeg"),
    )

    manifest = json.loads((tmp_path / "run" / "audio_manifest.json").read_text(encoding="utf-8"))

    assert artifact.status == "failed"
    assert "ffmpeg_audio_extract_failed_exit_1" in str(artifact.error)
    assert manifest["metadata"]["executed"] is True
    assert manifest["metadata"]["returncode"] == 1
    assert manifest["metadata"]["stderr"] == "bad input"


def test_audio_extraction_config_rejects_unknown_execution_mode() -> None:
    with pytest.raises(ValueError, match="execution_mode must be ffmpeg or mock"):
        AudioExtractionConfig(execution_mode="remote")  # type: ignore[arg-type]
