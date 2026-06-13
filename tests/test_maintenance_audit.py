from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tools.maintenance_audit import build_maintenance_audit


def test_maintenance_audit_reports_expected_contract_shape(tmp_path) -> None:
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
    (tmp_path / "tests" / "fixture.py").write_text('value = "sk-test-secret-value"\n', encoding="utf-8")

    report = build_maintenance_audit(tmp_path)
    checks = {check["check_id"]: check for check in report["checks"]}

    assert checks["secret_like_fragments"]["high_confidence_count"] == 0


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

    assert checks["secret_like_fragments"]["status"] == "warning"
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


def test_historical_docs_are_exempt_only_when_summary_exists(tmp_path) -> None:
    docs = tmp_path / "docs"
    handoff = docs / "handoff"
    archive = docs / "archive"
    handoff.mkdir(parents=True)
    archive.mkdir(parents=True)
    (handoff / "AFS-OLD.md").write_text("# Old Handoff\n\nEnglish historical evidence.\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# 当前说明\n\n这是当前中文入口。\n", encoding="utf-8")

    report_without_summary = build_maintenance_audit(tmp_path)
    checks_without_summary = {check["check_id"]: check for check in report_without_summary["checks"]}
    assert checks_without_summary["human_doc_chinese_coverage"]["status"] == "warning"

    (archive / "HISTORICAL_DOCS_SUMMARY.zh-CN.md").write_text(
        "# 历史文档中文摘要索引\n\n旧 handoff 作为历史证据保留，当前入口改用中文维护账本。\n",
        encoding="utf-8",
    )

    report_with_summary = build_maintenance_audit(tmp_path)
    checks_with_summary = {check["check_id"]: check for check in report_with_summary["checks"]}
    coverage = checks_with_summary["human_doc_chinese_coverage"]
    assert coverage["status"] == "passed"
    assert coverage["historical_docs_exempted_count"] == 1
