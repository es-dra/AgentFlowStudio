from __future__ import annotations

from pathlib import Path

from tools.staging_preflight import (
    STARTUP_SECRET_PATH,
    format_report,
    parse_status,
    run_preflight,
)


def test_parse_status_keeps_untracked_dirs_and_rename_targets() -> None:
    status = "\n".join(
        [
            " M DEVLOG.md",
            "?? docs/maintenance/",
            "R  old.py -> tools/staging_preflight.py",
        ]
    )

    assert parse_status(status) == [
        "DEVLOG.md",
        "docs/maintenance/",
        "tools/staging_preflight.py",
    ]


def test_preflight_blocks_local_only_paths(tmp_path: Path) -> None:
    repo = tmp_path
    (repo / "data" / "processed").mkdir(parents=True)
    (repo / "data" / "processed" / "run.json").write_text("{}", encoding="utf-8")

    report = run_preflight(repo, "?? data/processed/run.json\n")

    assert not report.ok
    assert {finding.code for finding in report.findings} == {"local-only-path"}


def test_preflight_expands_dirs_and_warns_on_oversized_files(tmp_path: Path) -> None:
    repo = tmp_path
    docs = repo / "docs" / "maintenance"
    docs.mkdir(parents=True)
    (docs / "too_big.md").write_text("\n".join(str(i) for i in range(301)), encoding="utf-8")

    report = run_preflight(repo, "?? docs/maintenance/\n")

    assert report.ok
    assert any(finding.code == "oversized-file" and finding.path == "docs/maintenance/too_big.md" for finding in report.findings)


def test_preflight_rejects_hardcoded_startup_secret_path(tmp_path: Path) -> None:
    repo = tmp_path
    source = repo / "agentflow_studio" / "model_gateway"
    source.mkdir(parents=True)
    (source / "company_secrets.py").write_text(f'path = "{STARTUP_SECRET_PATH}"\n', encoding="utf-8")

    report = run_preflight(repo, " M agentflow_studio/model_gateway/company_secrets.py\n")

    assert not report.ok
    assert {finding.code for finding in report.findings} == {"hardcoded-startup-secret-path"}
    assert {finding.severity for finding in report.findings} == {"block"}


def test_preflight_formats_passing_report(tmp_path: Path) -> None:
    repo = tmp_path
    (repo / "DEVLOG.md").write_text("# DEVLOG\n", encoding="utf-8")

    report = run_preflight(repo, " M DEVLOG.md\n")

    assert report.ok
    assert "status: pass" in format_report(report)
