from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tools.maintenance_audit import build_maintenance_audit


def test_maintenance_audit_reports_expected_contract_shape(tmp_path) -> None:
    _init_git_repo(tmp_path)
    (tmp_path / "AGENTS.md").write_text(
        "# 规则\n\nTreat `D:\\Learning materials\\Learning_notes\\Company` as legacy.\n",
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text("# Hello\n\nEnglish only.\n", encoding="utf-8")
    report = build_maintenance_audit(tmp_path)

    assert report["artifact_type"] == "agentflow_maintenance_audit_report"
    assert report["schema_version"] == "0.1.0"
    assert report["writes_long_term_memory"] is False
    assert report["writes_company_kb"] is False
    checks = {check["check_id"]: check for check in report["checks"]}
    assert checks["legacy_company_path"]["count"] == 1
    assert checks["human_doc_chinese_coverage"]["status"] == "warning"


def test_maintenance_audit_cli_outputs_json() -> None:
    result = subprocess.run(
        [sys.executable, "tools/maintenance_audit.py", "--root", "."],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    payload = json.loads(result.stdout)

    assert payload["artifact_type"] == "agentflow_maintenance_audit_report"
    assert payload["summary"]["passed"] >= 1


def test_maintenance_audit_ignores_generated_egg_info_metadata(tmp_path) -> None:
    egg_info = tmp_path / "agentflow_studio.egg-info"
    egg_info.mkdir()
    (egg_info / "SOURCES.txt").write_text("\n".join(f"generated/file_{index}.py" for index in range(600)), encoding="utf-8")
    (tmp_path / "README.md").write_text("# 当前说明\n\n这是当前中文入口。\n", encoding="utf-8")

    report = build_maintenance_audit(tmp_path)
    checks = {check["check_id"]: check for check in report["checks"]}

    assert checks["oversized_files"]["status"] == "passed"


def test_maintenance_audit_does_not_count_named_fake_secret_fixture(tmp_path) -> None:
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "fixture.py").write_text(
        '\n'.join(
            [
                'value = "sk-test-secret-value"',
                'provider_prompt = "api_key=sk-fixture-provider-redaction"',
            ]
        ),
        encoding="utf-8",
    )

    report = build_maintenance_audit(tmp_path)
    checks = {check["check_id"]: check for check in report["checks"]}

    assert checks["secret_like_fragments"]["high_confidence_count"] == 0


def test_maintenance_audit_flags_ambiguous_fake_secret_names(tmp_path) -> None:
    (tmp_path / "tests").mkdir()
    ambiguous_value = "sk-" + "client-event"
    (tmp_path / "tests" / "fixture.py").write_text(f'value = "{ambiguous_value}"\n', encoding="utf-8")

    report = build_maintenance_audit(tmp_path)
    checks = {check["check_id"]: check for check in report["checks"]}

    assert checks["secret_like_fragments"]["status"] == "failed"
    assert checks["secret_like_fragments"]["high_confidence_count"] == 1


def test_maintenance_audit_does_not_hide_real_secret_when_fixture_shares_line(tmp_path) -> None:
    (tmp_path / "tests").mkdir()
    fixture_value = "sk-fixture-redaction"
    secret_value = "sk-" + "live-secret-value-123456"
    (tmp_path / "tests" / "fixture.py").write_text(
        f'value = "{fixture_value} {secret_value}"\n',
        encoding="utf-8",
    )

    report = build_maintenance_audit(tmp_path)
    checks = {check["check_id"]: check for check in report["checks"]}

    assert checks["secret_like_fragments"]["status"] == "failed"
    assert checks["secret_like_fragments"]["high_confidence_count"] == 1


def test_maintenance_audit_ignores_schema_fields_and_safe_fixture_values(tmp_path) -> None:
    (tmp_path / "configs").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "configs" / "tool_catalog.yaml").write_text(
        """
tools:
  - name: remote_asr
    requires:
      api_key: true
    failure_modes:
      - api_key_missing
""",
        encoding="utf-8",
    )
    (tmp_path / "tests" / "provider_fixture.py").write_text(
        '\n'.join(
            [
                'provider = Provider(api_key="fake-key")',
                'token_url = "https://signed.example/video.mp4?token=provider-secret-url"',
                '$env:AFS_IMAGE_API_KEY="<local-provider-key>"',
            ]
        ),
        encoding="utf-8",
    )

    report = build_maintenance_audit(tmp_path)
    checks = {check["check_id"]: check for check in report["checks"]}

    assert checks["secret_like_fragments"]["status"] == "passed"


def test_maintenance_audit_still_flags_real_high_confidence_secret(tmp_path) -> None:
    secret_value = "sk-" + "live-secret-value-123456"
    (tmp_path / "bad.py").write_text(f'value = "{secret_value}"\n', encoding="utf-8")

    report = build_maintenance_audit(tmp_path)
    checks = {check["check_id"]: check for check in report["checks"]}

    assert checks["secret_like_fragments"]["status"] == "failed"
    assert checks["secret_like_fragments"]["high_confidence_count"] == 1


def test_maintenance_audit_lists_legacy_frozen_surface_without_skipping_secret_scan(tmp_path) -> None:
    legacy_dir = tmp_path / "agentflow" / "memory"
    legacy_dir.mkdir(parents=True)
    (legacy_dir / "large_loop.py").write_text("\n".join(f"line_{index} = 1" for index in range(550)), encoding="utf-8")
    secret_value = "sk-" + "live-secret-value-123456"
    (legacy_dir / "secret.py").write_text(f'value = "{secret_value}"\n', encoding="utf-8")
    (tmp_path / "README.md").write_text("# 当前说明\n\n这是当前中文入口。\n", encoding="utf-8")

    report = build_maintenance_audit(tmp_path)
    checks = {check["check_id"]: check for check in report["checks"]}

    assert checks["legacy_frozen_surface"]["status"] == "warning"
    assert checks["legacy_frozen_surface"]["count"] == 1
    assert checks["oversized_files"]["status"] == "passed"
    assert checks["secret_like_fragments"]["status"] == "failed"
    assert checks["secret_like_fragments"]["high_confidence_count"] == 1


def test_maintenance_audit_skips_permission_errors_during_stat_and_read(tmp_path, monkeypatch) -> None:
    (tmp_path / "README.md").write_text("# 当前说明\n\n这是当前中文入口。\n", encoding="utf-8")
    (tmp_path / "blocked_stat.py").write_text("value = 1\n", encoding="utf-8")
    (tmp_path / "blocked_read.md").write_text("# Blocked\n\nEnglish only.\n", encoding="utf-8")
    original_is_file = Path.is_file
    original_read_text = Path.read_text

    def guarded_is_file(path: Path) -> bool:
        if path.name == "blocked_stat.py":
            raise PermissionError("stat blocked")
        return original_is_file(path)

    def guarded_read_text(path: Path, *args, **kwargs) -> str:
        if path.name == "blocked_read.md":
            raise PermissionError("read blocked")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "is_file", guarded_is_file)
    monkeypatch.setattr(Path, "read_text", guarded_read_text)

    report = build_maintenance_audit(tmp_path)

    assert report["artifact_type"] == "agentflow_maintenance_audit_report"
    assert report["summary"]["failed"] == 0


def test_chinese_doc_coverage_ignores_machine_contract_blocks(tmp_path) -> None:
    (tmp_path / "README.md").write_text(
        """# 中文说明

这是给人看的中文说明，机器契约字段可以继续保留英文。

```json
{
  "artifact_type": "agentflow_project_manifest",
  "schema_version": "0.1.0",
  "project_id": "proj_xxx",
  "feedback_refs": [],
  "profile_version_refs": []
}
```

前端只使用 safe artifact 引用，不读取私有路径。
""",
        encoding="utf-8",
    )

    report = build_maintenance_audit(tmp_path)
    checks = {check["check_id"]: check for check in report["checks"]}

    assert checks["human_doc_chinese_coverage"]["status"] == "passed"


def test_live_historical_docs_are_not_exempted_by_archive_summary(tmp_path) -> None:
    _init_git_repo(tmp_path)
    docs = tmp_path / "docs"
    handoff = docs / "handoff"
    archive = docs / "archive"
    handoff.mkdir(parents=True)
    archive.mkdir(parents=True)
    (handoff / "AFS-OLD.md").write_text("# Old Handoff\n\nEnglish historical evidence.\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# 当前说明\n\n这是当前中文入口。\n", encoding="utf-8")

    (archive / "HISTORICAL_DOCS_SUMMARY.zh-CN.md").write_text(
        "# 历史文档中文摘要索引\n\n旧 handoff 作为历史证据保留，当前入口改用中文维护账本。\n",
        encoding="utf-8",
    )

    report = build_maintenance_audit(tmp_path)
    checks = {check["check_id"]: check for check in report["checks"]}
    coverage = checks["human_doc_chinese_coverage"]
    finding_paths = {finding["path"] for finding in coverage["findings"]}
    assert coverage["status"] == "warning"
    assert "docs/handoff/AFS-OLD.md" in finding_paths
    assert "historical_docs_exempted_count" not in coverage


def _init_git_repo(path: Path) -> None:
    subprocess.run(
        ["git", "init"],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )


def test_maintenance_audit_classifies_git_state_and_excludes_ignored_oversized_files(tmp_path) -> None:
    subprocess.run(
        ["git", "init"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )
    (tmp_path / ".gitignore").write_text("runs/\n", encoding="utf-8")
    (tmp_path / "tracked_big.py").write_text("\n".join("value = 1" for _ in range(301)), encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "demo.md").write_text("\n".join("English only." for _ in range(302)), encoding="utf-8")
    (tmp_path / "runs").mkdir()
    (tmp_path / "runs" / "generated.json").write_text("\n".join("{}" for _ in range(450)), encoding="utf-8")
    subprocess.run(
        ["git", "add", ".gitignore", "tracked_big.py"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )

    report = build_maintenance_audit(tmp_path)
    checks = {check["check_id"]: check for check in report["checks"]}
    oversized = checks["oversized_files"]
    findings = {finding["path"]: finding for finding in oversized["findings"]}

    assert "runs/generated.json" not in findings
    assert findings["tracked_big.py"]["git_state"] == "tracked"
    assert findings["docs/demo.md"]["git_state"] == "untracked"
    assert oversized["source_summary"]["tracked"] == 1
    assert oversized["source_summary"]["untracked"] == 1
    assert oversized["source_summary"].get("ignored", 0) == 0
    assert report["workspace_files"]["ignored_text_files"] == 1
