from __future__ import annotations

from typer.testing import CliRunner

from apps.cli import main as cli_main
from apps.cli import media_commands
from narratocut.slicing_sop import FFmpegInfo


def test_ffmpeg_check_command_reports_available(monkeypatch) -> None:
    def fake_check(executable: str) -> FFmpegInfo:
        return FFmpegInfo(
            available=True,
            executable=executable,
            version="ffmpeg version test",
            raw_output="ffmpeg version test",
            error=None,
        )

    monkeypatch.setattr(media_commands, "check_ffmpeg_available", fake_check)

    result = CliRunner().invoke(cli_main.app, ["ffmpeg-check", "--executable", "ffmpeg-test"])

    assert result.exit_code == 0, result.output
    assert "FFmpeg available: ffmpeg-test" in result.output


def test_ffmpeg_check_command_reports_unavailable(monkeypatch) -> None:
    def fake_check(executable: str) -> FFmpegInfo:
        return FFmpegInfo(
            available=False,
            executable=executable,
            version=None,
            raw_output=None,
            error="not found",
        )

    monkeypatch.setattr(media_commands, "check_ffmpeg_available", fake_check)

    result = CliRunner().invoke(cli_main.app, ["ffmpeg-check"])

    assert result.exit_code == 0, result.output
    assert "FFmpeg unavailable: not found" in result.output
