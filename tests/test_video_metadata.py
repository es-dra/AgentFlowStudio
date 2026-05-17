from __future__ import annotations

import subprocess

from narratocut.slicing_sop.video_metadata import (
    parse_ffprobe_video_metadata,
    probe_video_metadata,
)


def test_parse_ffprobe_video_metadata_reads_primary_video_stream() -> None:
    metadata = parse_ffprobe_video_metadata(
        "input.mp4",
        {
            "format": {"duration": "12.5", "bit_rate": "900000"},
            "streams": [
                {"codec_type": "audio", "codec_name": "aac"},
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1920,
                    "height": 1080,
                    "r_frame_rate": "30000/1001",
                },
            ],
        },
    )

    assert metadata.probe_status == "succeeded"
    assert metadata.duration_sec == 12.5
    assert metadata.width == 1920
    assert metadata.height == 1080
    assert metadata.codec == "h264"
    assert round(metadata.fps or 0, 3) == 29.97
    assert metadata.bitrate == 900000


def test_probe_video_metadata_reports_missing_ffprobe(tmp_path, monkeypatch) -> None:
    video = tmp_path / "input.mp4"
    video.write_bytes(b"fake")

    def fake_run(*args, **kwargs):
        raise FileNotFoundError("ffprobe missing")

    monkeypatch.setattr("narratocut.slicing_sop.video_metadata.subprocess.run", fake_run)

    metadata = probe_video_metadata(video, ffprobe_executable="missing-ffprobe")

    assert metadata.probe_status == "failed"
    assert metadata.duration_sec is None
    assert any("ffprobe_unavailable" in error for error in metadata.errors)


def test_probe_video_metadata_uses_ffprobe_json(tmp_path, monkeypatch) -> None:
    video = tmp_path / "input.mp4"
    video.write_bytes(b"fake")

    def fake_run(command, capture_output, text, timeout, check):
        assert command[:4] == [
            "ffprobe-test",
            "-v",
            "error",
            "-print_format",
        ]
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=(
                '{"format":{"duration":"3","bit_rate":"1000"},'
                '"streams":[{"codec_type":"video","codec_name":"h264","width":640,"height":360}]}'
            ),
            stderr="",
        )

    monkeypatch.setattr("narratocut.slicing_sop.video_metadata.subprocess.run", fake_run)

    metadata = probe_video_metadata(video, ffprobe_executable="ffprobe-test")

    assert metadata.probe_status == "succeeded"
    assert metadata.duration_sec == 3
    assert metadata.width == 640
    assert metadata.height == 360
