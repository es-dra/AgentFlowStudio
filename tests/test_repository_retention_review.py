from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tools.repository_retention_review import build_repository_retention_review


def test_repository_retention_review_classifies_delete_candidate_and_known_paths(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# 项目入口\n", encoding="utf-8")
    (tmp_path / "README.zh-CN.md").write_text("# 旧入口\n", encoding="utf-8")
    (tmp_path / "agentflow").mkdir()
    (tmp_path / "agentflow" / "contracts.py").write_text("", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "handoff.md").write_text("# 交接\n", encoding="utf-8")
    (tmp_path / "apps" / "web_bridge").mkdir(parents=True)
    (tmp_path / "apps" / "web_bridge" / "server.py").write_text("", encoding="utf-8")
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "maintenance.yml").write_text("name: test\n", encoding="utf-8")
    (tmp_path / "agentflow_studio").mkdir()
    (tmp_path / "agentflow_studio" / "memory_advantage_demo_012.py").write_text("", encoding="utf-8")

    report = build_repository_retention_review(tmp_path)
    files = {item["path"]: item for item in report["files"]}

    assert report["artifact_type"] == "agentflow_repository_retention_review"
    assert files["README.md"]["product_surface"] == "production_spine"
    assert files["README.md"]["status"] == "current"
    assert files["README.zh-CN.md"]["status"] == "delete_candidate"
    assert files["agentflow/contracts.py"]["product_surface"] == "production_spine"
    assert files["agentflow/contracts.py"]["status"] == "current"
    assert files["apps/web_bridge/server.py"]["product_surface"] == "delete_candidate"
    assert files["apps/web_bridge/server.py"]["status"] == "legacy_runtime_surface"
    assert files[".github/workflows/maintenance.yml"]["product_surface"] == "operations_spine"
    assert files[".github/workflows/maintenance.yml"]["status"] == "current"
    assert files["agentflow_studio/memory_advantage_demo_012.py"]["product_surface"] == "quarantine_candidate"
    assert files["agentflow_studio/memory_advantage_demo_012.py"]["status"] == "legacy_demo_runtime"
    assert report["summary"]["delete_candidate_count"] == 3
    assert report["summary"]["product_surface_counts"]["quarantine_candidate"] >= 1


def test_repository_retention_review_marks_deleted_redundant_entry_as_applied(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    (tmp_path / "README.md").write_text("# 项目入口\n", encoding="utf-8")
    (tmp_path / "README.zh-CN.md").write_text("# 旧入口\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md", "README.zh-CN.md"], cwd=tmp_path, check=True, capture_output=True)
    (tmp_path / "README.zh-CN.md").unlink()

    report = build_repository_retention_review(tmp_path)
    files = {item["path"]: item for item in report["files"]}

    assert files["README.zh-CN.md"]["git_state"] == "deleted"
    assert files["README.zh-CN.md"]["status"] == "remove_applied_pending_stage"
    assert report["summary"]["delete_candidate_count"] == 0


def test_repository_retention_review_cli_outputs_summary_json() -> None:
    result = subprocess.run(
        [sys.executable, "tools/repository_retention_review.py", "--root", ".", "--summary-only"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    payload = json.loads(result.stdout)

    assert payload["artifact_type"] == "agentflow_repository_retention_review"
    assert payload["summary"]["file_count"] > 0
    assert payload["summary"]["manual_review_required_count"] == 0
