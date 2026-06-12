from __future__ import annotations

import json

from tools import studio_asset_context_live_comparison as live_runner
from tools.studio_asset_context_sample_reference import write_sample_reference


def test_live_comparison_runner_writes_gate_closed_no_call_report(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_IMAGE", raising=False)
    monkeypatch.delenv("AFS_PROVIDER_CONFIG", raising=False)
    report_path = tmp_path / "live_report.json"
    runtime_root = tmp_path / "runtime"

    exit_code = live_runner.main(
        [
            "--runtime-root",
            str(runtime_root),
            "--report",
            str(report_path),
        ]
    )

    assert exit_code == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    arms = {item["arm_id"]: item for item in report["arm_summary"]}

    assert report["runner_mode"] == "gate_closed_readiness"
    assert report["provider_calls_started"] is False
    assert report["comparison_status"] == "blocked"
    assert arms["A"]["fixed_asset_injection"] is False
    assert arms["A"]["result_ref_count"] == 0
    assert arms["B"]["fixed_asset_injection"] is False
    assert arms["C"]["fixed_asset_injection"] is True
    assert arms["C"]["subject_reference_asset_id"]


def test_live_comparison_runner_refuses_ready_gate_without_explicit_flag(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")
    monkeypatch.delenv("AFS_PROVIDER_CONFIG", raising=False)
    report_path = tmp_path / "live_report.json"

    exit_code = live_runner.main(["--report", str(report_path)])

    assert exit_code == 2
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert report["runner_mode"] == "preflight"
    assert report["provider_gate"]["status"] == "ready_not_run"
    assert report["provider_calls_started"] is False
    assert report["blocks"][0]["block_id"] == "live_provider_flag_missing"


def test_live_comparison_runner_requires_reference_image_for_live_mode(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")
    provider_config = tmp_path / "providers.local.json"
    provider_config.write_text("{}", encoding="utf-8")
    report_path = tmp_path / "live_report.json"

    exit_code = live_runner.main(
        [
            "--provider-config",
            str(provider_config),
            "--allow-live-provider",
            "--report",
            str(report_path),
        ]
    )

    assert exit_code == 2
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert report["runner_mode"] == "preflight"
    assert report["provider_gate"]["status"] == "ready_not_run"
    assert report["provider_calls_started"] is False
    assert report["blocks"][0]["block_id"] == "reference_image_missing"


def test_sample_reference_writer_creates_real_png(tmp_path) -> None:
    output = write_sample_reference(tmp_path / "lin-wan-reference.png")

    payload = output.read_bytes()

    assert output.is_file()
    assert payload.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(payload) > 1000


def test_live_comparison_runner_can_use_sample_reference_in_readiness_mode(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_IMAGE", raising=False)
    monkeypatch.delenv("AFS_PROVIDER_CONFIG", raising=False)
    report_path = tmp_path / "live_report.json"
    reference_path = tmp_path / "reference.png"

    exit_code = live_runner.main(
        [
            "--sample-reference-output",
            str(reference_path),
            "--report",
            str(report_path),
        ]
    )

    assert exit_code == 0
    assert reference_path.is_file()
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert report["runner_mode"] == "gate_closed_readiness"
    assert report["provider_calls_started"] is False
    assert report["arm_summary"][2]["reference_image_count"] == 1
