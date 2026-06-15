from __future__ import annotations

from pathlib import Path


def test_internal_studio_launcher_keeps_asr_off_and_uses_explicit_live_gates() -> None:
    script = Path("tools/run_studio_internal_test.ps1")
    assert script.is_file()
    source = script.read_text(encoding="utf-8")

    assert "param(" in source
    assert "[switch]$AllowLLM" in source
    assert "[switch]$AllowImage" in source
    assert "[switch]$AllowVideo" in source
    assert "AllowASR" not in source
    assert '$env:AFS_ALLOW_REMOTE_ASR = "false"' in source
    assert '$env:AFS_ALLOW_EXTERNAL_DOWNLOAD = "false"' in source
    assert '$env:AFS_ALLOW_REMOTE_LLM = $(if ($AllowLLM) { "true" } else { "false" })' in source
    assert '$env:AFS_ALLOW_REMOTE_IMAGE = $(if ($AllowImage) { "true" } else { "false" })' in source
    assert '$env:AFS_ALLOW_REMOTE_VIDEO = $(if ($AllowVideo) { "true" } else { "false" })' in source


def test_internal_studio_launcher_uses_runtime_8790_and_does_not_echo_provider_config_contents() -> None:
    source = Path("tools/run_studio_internal_test.ps1").read_text(encoding="utf-8")

    assert "[int]$Port = 8790" in source
    assert "--host 127.0.0.1 --port $Port" in source
    assert "Get-Content $ProviderConfig" not in source
    assert "Write-Host $ProviderConfig" not in source
    assert "Test-Path -LiteralPath $ProviderConfig" in source
    assert "Provider config present:" in source
    assert "DOWNLOAD=$($env:AFS_ALLOW_EXTERNAL_DOWNLOAD)" in source
