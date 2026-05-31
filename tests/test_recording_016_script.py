from __future__ import annotations

from pathlib import Path


SCRIPT = Path("tools/run_memory_advantage_recording_016.ps1")


def test_recording_016_script_requires_provider_config_for_live_path() -> None:
    script = SCRIPT.read_text(encoding="utf-8")

    assert "[string]$ProviderConfig" in script
    assert "NARRATOCUT_PROVIDER_CONFIG" in script
    assert "Provider config is required" in script
    assert "--provider-config" in script
    assert script.count("@ProviderConfigArgs") >= 2


def test_recording_016_script_keeps_remote_video_gate_and_dry_run_boundary() -> None:
    script = SCRIPT.read_text(encoding="utf-8")

    assert "NARRATOCUT_ALLOW_REMOTE_VIDEO" in script
    assert "Dry run complete; provider calls were not made" in script
    assert "-AllowRemoteVideo" in script
    assert "Claim boundary" in script
