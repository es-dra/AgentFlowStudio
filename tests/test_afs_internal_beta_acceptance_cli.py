from __future__ import annotations

import json
from pathlib import Path

from tools import afs_internal_beta_acceptance as acceptance_runner


def test_three_end_status_flag_runs_standalone_report_not_acceptance(tmp_path: Path, monkeypatch, capsys) -> None:
    report_path = tmp_path / "three-end.json"
    called: dict[str, object] = {}

    def fake_three_end_status(**kwargs):
        called.update(kwargs)
        return {
            "artifact_type": "afs_three_end_status_report",
            "schema_version": "0.1.0",
            "status": "aligned",
            "provider_calls_started": False,
            "writes_company_kb": False,
            "writes_long_term_memory": False,
            "summary": {
                "checked_end_count": 1,
                "aligned_end_count": 1,
                "dirty_end_count": 0,
                "runtime_status": "ready",
            },
            "ends": {},
            "runtime_health": {"status": "ready"},
        }

    def fail_acceptance(**_kwargs):
        raise AssertionError("standalone three-end status must not run acceptance")

    monkeypatch.setattr(acceptance_runner, "run_three_end_status", fake_three_end_status, raising=False)
    monkeypatch.setattr(acceptance_runner, "run_inprocess_acceptance", fail_acceptance)
    monkeypatch.setattr(
        "sys.argv",
        [
            "afs_internal_beta_acceptance.py",
            "--three-end-status",
            "--three-end-repo-root",
            str(tmp_path),
            "--three-end-server",
            "afs-bwg-ops",
            "--report",
            str(report_path),
        ],
    )

    exit_code = acceptance_runner.main()

    stdout = json.loads(capsys.readouterr().out)
    persisted = json.loads(report_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert stdout == {"status": "aligned", "report": str(report_path.resolve())}
    assert persisted["artifact_type"] == "afs_three_end_status_report"
    assert called["repo_root"] == tmp_path.resolve()
    assert called["server"] == "afs-bwg-ops"
