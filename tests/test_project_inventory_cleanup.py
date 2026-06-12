from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tools.project_inventory import (
    build_project_inventory,
    execute_cleanup_plan,
)


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
        capture_output=True,
    )


def _write(path: Path, text: str = "x\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_project_inventory_counts_tracked_and_ignored_without_reading_local_config(tmp_path: Path) -> None:
    _git(tmp_path, "init")
    _write(tmp_path / ".gitignore", "*.local.json\n__pycache__/\ndata/models/\n")
    _write(tmp_path / "apps/api/runtime.py", "print('ok')\n")
    _write(tmp_path / "configs/providers.local.json", '{"secret": "do-not-read"}\n')
    _write(tmp_path / "agentflow/__pycache__/cached.pyc", "compiled")
    _write(tmp_path / "data/models/fake/model.bin", "weights")
    _git(tmp_path, "add", ".gitignore", "apps/api/runtime.py")

    report = build_project_inventory(tmp_path)

    assert report["tracked"]["total_files"] == 2
    ignored_paths = {entry["path"] for entry in report["ignored"]["entries"]}
    assert "configs/providers.local.json" in ignored_paths
    local_config = next(entry for entry in report["ignored"]["entries"] if entry["path"] == "configs/providers.local.json")
    assert local_config["cleanup_action"] == "report_only"
    assert local_config["cleanup_reason"] == "protected local configuration"
    assert "do-not-read" not in json.dumps(report, ensure_ascii=False)
    pycache = next(entry for entry in report["ignored"]["entries"] if entry["path"] == "agentflow/__pycache__/cached.pyc")
    assert pycache["cleanup_action"] == "auto_delete"
    model = next(entry for entry in report["ignored"]["entries"] if entry["path"] == "data/models/fake/model.bin")
    assert model["cleanup_action"] == "report_only"


def test_execute_cleanup_deletes_only_auto_delete_targets(tmp_path: Path) -> None:
    _git(tmp_path, "init")
    _write(tmp_path / ".gitignore", "*.local.json\n__pycache__/\ndata/models/\ndata/processed/pytest-basetemp/\n")
    _write(tmp_path / "tracked.py", "print('tracked')\n")
    _write(tmp_path / "configs/providers.local.json", '{"secret": "keep"}\n')
    _write(tmp_path / "agentflow/__pycache__/cached.pyc", "compiled")
    _write(tmp_path / "data/processed/pytest-basetemp/full/tmp.txt", "cache")
    _write(tmp_path / "data/models/fake/model.bin", "weights")
    _git(tmp_path, "add", ".gitignore", "tracked.py")
    report = build_project_inventory(tmp_path)

    manifest = execute_cleanup_plan(tmp_path, report["cleanup_plan"])

    assert manifest["summary"]["deleted_count"] >= 2
    assert not (tmp_path / "agentflow/__pycache__/cached.pyc").exists()
    assert not (tmp_path / "data/processed/pytest-basetemp/full/tmp.txt").exists()
    assert (tmp_path / "configs/providers.local.json").exists()
    assert (tmp_path / "data/models/fake/model.bin").exists()
    _git(tmp_path, "status", "--short")


def test_project_inventory_cli_writes_reports_and_markdown(tmp_path: Path) -> None:
    _git(tmp_path, "init")
    _write(tmp_path / ".gitignore", "__pycache__/\n")
    _write(tmp_path / "tracked.py", "print('tracked')\n")
    _write(tmp_path / "pkg/__pycache__/cached.pyc", "compiled")
    _git(tmp_path, "add", ".gitignore", "tracked.py")

    output_dir = tmp_path / "out"
    doc_path = tmp_path / "docs/maintenance/report.md"
    result = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve().parents[1] / "tools" / "project_inventory.py"),
            "--root",
            str(tmp_path),
            "--output-dir",
            str(output_dir),
            "--report-doc",
            str(doc_path),
            "--execute-cleanup",
        ],
        check=True,
        text=True,
        capture_output=True,
    )

    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert (output_dir / "inventory.json").exists()
    assert (output_dir / "cleanup_plan.json").exists()
    assert (output_dir / "cleanup_manifest.json").exists()
    assert doc_path.exists()
    assert "AFS Project Inventory" in doc_path.read_text(encoding="utf-8")
