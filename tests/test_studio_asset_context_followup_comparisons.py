from __future__ import annotations

import json

from tools import studio_asset_context_followup_comparisons as followup
from tools.studio_asset_context_sample_reference import write_sample_scene_reference


def test_followup_runner_gate_closed_builds_dual_asset_and_lock_reports(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_IMAGE", raising=False)
    monkeypatch.delenv("AFS_PROVIDER_CONFIG", raising=False)
    report_path = tmp_path / "followup.json"

    exit_code = followup.main(
        [
            "--runtime-root",
            str(tmp_path / "runtime"),
            "--output-dir",
            str(tmp_path / "runs"),
            "--report",
            str(report_path),
        ]
    )

    assert exit_code == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    group2 = report["scenarios"]["group2_character_scene"]
    group3 = report["scenarios"]["group3_lock_conflict"]
    arms = {item["arm_id"]: item for item in group2["report"]["arms"]}

    assert report["provider_calls_started"] is False
    assert report["status"] == "blocked"
    assert arms["C"]["reference_image_count"] == 1
    assert {item["asset_type"] for item in arms["C"]["context_bundle"]["included_assets"]} == {"character", "scene"}
    assert arms["B"]["context_bundle"]["included_assets"] == []
    assert group3["locked"]["status"] == "blocked"
    assert group3["temporary_unlocked"]["context_bundle"]["temporary_lock_overrides"][0]["lock_text"] == followup.HAIR_LOCK


def test_followup_runner_refuses_ready_gate_without_explicit_flag(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")
    monkeypatch.delenv("AFS_PROVIDER_CONFIG", raising=False)
    report_path = tmp_path / "followup.json"

    exit_code = followup.main(["--report", str(report_path)])

    assert exit_code == 2
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert report["runner_mode"] == "preflight"
    assert report["provider_gate"]["status"] == "ready_not_run"
    assert report["provider_calls_started"] is False
    assert report["blocks"][0]["block_id"] == "live_provider_flag_missing"


def test_sample_scene_reference_writer_creates_real_png(tmp_path) -> None:
    output = write_sample_scene_reference(tmp_path / "observatory-reference.png")

    payload = output.read_bytes()

    assert output.is_file()
    assert payload.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(payload) > 1000
