from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from apps.cli.main import app
from narratocut.package_sop.delivery import build_delivery_readiness, write_delivery_readiness
from narratocut.utils import write_json


def test_delivery_readiness_passes_for_two_clean_product_runs(tmp_path: Path) -> None:
    video_only = _write_product_run(tmp_path / "video_only", run_id="video_only")
    video_script = _write_product_run(tmp_path / "video_script", run_id="video_script")

    report = build_delivery_readiness([video_only, video_script])

    assert report["status"] == "pass"
    assert report["summary"] == {"total_runs": 2, "passed": 2, "warning": 0, "failed": 0}
    assert [run["mode"] for run in report["runs"]] == ["video_only", "video_script"]


def test_delivery_readiness_warns_for_selection_quality_warnings(tmp_path: Path) -> None:
    run_dir = _write_product_run(
        tmp_path / "video_only",
        run_id="video_only",
        diagnostics_warnings=[{"code": "near_miss_rejected", "message": "Rejected candidate was close."}],
    )

    report = build_delivery_readiness([run_dir])

    assert report["status"] == "warning"
    assert report["runs"][0]["status"] == "warning"
    assert report["runs"][0]["warnings"] == ["selection: near_miss_rejected"]


def test_delivery_readiness_fails_when_required_product_artifact_is_missing(tmp_path: Path) -> None:
    run_dir = _write_product_run(tmp_path / "video_only", run_id="video_only")
    (run_dir / "package_report.md").unlink()

    report = build_delivery_readiness([run_dir])

    assert report["status"] == "fail"
    assert report["runs"][0]["status"] == "fail"
    assert "missing package_report.md" in report["runs"][0]["failures"]


def test_write_delivery_readiness_writes_json_and_markdown(tmp_path: Path) -> None:
    run_dir = _write_product_run(tmp_path / "video_only", run_id="video_only")

    result = write_delivery_readiness([run_dir], tmp_path / "reports")

    assert result["json_path"].is_file()
    assert result["markdown_path"].is_file()
    payload = json.loads(result["json_path"].read_text(encoding="utf-8"))
    assert payload["status"] == "pass"
    markdown = result["markdown_path"].read_text(encoding="utf-8")
    assert "# NarratoCut Delivery Readiness" in markdown
    assert "- Overall status: pass" in markdown
    assert "video_only" in markdown


def test_delivery_readiness_cli_writes_report_and_exits_for_warning(tmp_path: Path) -> None:
    run_dir = _write_product_run(
        tmp_path / "video_only",
        run_id="video_only",
        diagnostics_warnings=[{"code": "clustered_selection", "message": "Selected clips are clustered."}],
    )
    output_dir = tmp_path / "delivery"

    result = CliRunner().invoke(
        app,
        [
            "delivery-readiness",
            "--run-dir",
            str(run_dir),
            "--output",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Delivery readiness:" in result.output
    assert "Status: warning" in result.output
    assert (output_dir / "delivery_readiness.json").is_file()
    assert (output_dir / "delivery_readiness.md").is_file()


def test_delivery_readiness_cli_returns_failure_for_failed_gate(tmp_path: Path) -> None:
    run_dir = _write_product_run(tmp_path / "video_only", run_id="video_only")
    (run_dir / "package_report.md").unlink()
    output_dir = tmp_path / "delivery"

    result = CliRunner().invoke(
        app,
        [
            "delivery-readiness",
            "--run-dir",
            str(run_dir),
            "--output",
            str(output_dir),
        ],
    )

    assert result.exit_code == 1, result.output
    assert "Status: fail" in result.output
    assert (output_dir / "delivery_readiness.json").is_file()
    assert (output_dir / "delivery_readiness.md").is_file()


def _write_product_run(
    run_dir: Path,
    *,
    run_id: str,
    diagnostics_warnings: list[dict[str, str]] | None = None,
) -> Path:
    run_dir.mkdir(parents=True)
    write_json(
        run_dir / "run_manifest.json",
        {
            "run_id": run_id,
            "workflow": "workflows/video_to_finished_package_local_asr.yaml",
            "workflow_mode": run_id,
            "quality_profile": "finished_package",
            "artifacts": {
                "finished_package_manifest": "finished_package_manifest.json",
                "package_report": "package_report.md",
            },
        },
    )
    write_json(
        run_dir / "finished_package_manifest.json",
        {
            "status": "succeeded",
            "package_id": f"pkg_{run_id}",
            "assets": [
                {"role": "final_video", "path": "final_video.mp4", "required": True, "exists": True},
                {"role": "cover", "path": "cover.jpg", "required": False, "exists": True},
            ],
        },
    )
    write_json(
        run_dir / "quality_report.json",
        {
            "status": "pass",
            "checks": [{"id": "finished_package_manifest", "status": "pass"}],
            "warnings": [],
        },
    )
    write_json(
        run_dir / "review_report.json",
        {
            "status": "passed",
            "summary": {"passed": 12, "failed": 0, "warnings": 0},
            "sections": [],
        },
    )
    write_json(
        run_dir / "selection_diagnostics.json",
        {
            "status": "succeeded",
            "candidate_count": 8,
            "selected_count": 4,
            "warnings": diagnostics_warnings or [],
        },
    )
    write_json(
        run_dir / "highlight_score_report.json",
        {
            "status": "succeeded",
            "selected_candidate_ids": ["cand_001", "cand_002", "cand_003", "cand_004"],
            "candidates": [],
        },
    )
    (run_dir / "package_report.md").write_text("# Package Report\n", encoding="utf-8")
    (run_dir / "final_video.mp4").write_bytes(b"fake video")
    return run_dir
