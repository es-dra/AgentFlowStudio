from __future__ import annotations

import subprocess

from narratocut.slicing_sop.ffmpeg_probe import check_ffmpeg_available


class _CompletedProcess:
    returncode = 0
    stdout = "ffmpeg version 6.1 Copyright\nconfiguration: fake"
    stderr = ""


def test_check_ffmpeg_available_success(monkeypatch) -> None:
    calls: list[list[str]] = []

    def fake_run(args, **kwargs):
        calls.append(args)
        assert kwargs["capture_output"] is True
        assert kwargs["text"] is True
        assert kwargs["timeout"] == 5
        assert kwargs["check"] is False
        return _CompletedProcess()

    monkeypatch.setattr(subprocess, "run", fake_run)

    info = check_ffmpeg_available("ffmpeg-test")

    assert calls == [["ffmpeg-test", "-version"]]
    assert info.available is True
    assert info.executable == "ffmpeg-test"
    assert info.version == "ffmpeg version 6.1 Copyright"
    assert info.error is None


def test_check_ffmpeg_available_handles_missing_executable(monkeypatch) -> None:
    def fake_run(*args, **kwargs):
        raise FileNotFoundError("missing")

    monkeypatch.setattr(subprocess, "run", fake_run)

    info = check_ffmpeg_available("missing-ffmpeg")

    assert info.available is False
    assert info.version is None
    assert "not found" in str(info.error)


def test_check_ffmpeg_available_handles_timeout(monkeypatch) -> None:
    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=["ffmpeg", "-version"], timeout=5)

    monkeypatch.setattr(subprocess, "run", fake_run)

    info = check_ffmpeg_available()

    assert info.available is False
    assert info.version is None
    assert "timed out" in str(info.error)
