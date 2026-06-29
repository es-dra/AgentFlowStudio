from __future__ import annotations

import argparse
import fnmatch
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

try:
    from tools.maintenance_audit_git import git_file_states, git_ls_files, workspace_file_summary
    from tools.maintenance_audit_policy import (
        ARTIFACT_TYPE,
        DEFAULT_EXCLUDE_DIRS,
        HISTORICAL_DOC_GLOBS,
        HISTORICAL_DOC_PREFIXES,
        HISTORICAL_SUMMARY_PATH,
        LEGACY_FROZEN_PREFIXES,
        LEGACY_COMPANY_PATTERNS,
        SCHEMA_VERSION,
        TEXT_SUFFIXES,
    )
    from tools.maintenance_audit_secret_scan import check_secret_like_fragments
except ModuleNotFoundError:
    from maintenance_audit_git import git_file_states, git_ls_files, workspace_file_summary  # type: ignore[no-redef]
    from maintenance_audit_policy import (  # type: ignore[no-redef]
        ARTIFACT_TYPE,
        DEFAULT_EXCLUDE_DIRS,
        HISTORICAL_DOC_GLOBS,
        HISTORICAL_DOC_PREFIXES,
        HISTORICAL_SUMMARY_PATH,
        LEGACY_FROZEN_PREFIXES,
        LEGACY_COMPANY_PATTERNS,
        SCHEMA_VERSION,
        TEXT_SUFFIXES,
    )
    from maintenance_audit_secret_scan import check_secret_like_fragments  # type: ignore[no-redef]


@dataclass(frozen=True)
class Finding:
    path: str
    detail: str
    line: int | None = None
    git_state: str | None = None

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"path": self.path, "detail": self.detail}
        if self.line is not None:
            payload["line"] = self.line
        if self.git_state is not None:
            payload["git_state"] = self.git_state
        return payload


def build_maintenance_audit(root: Path) -> dict[str, Any]:
    root = root.resolve()
    files = list(_iter_text_files(root))
    file_states = git_file_states(root, [_rel(root, path) for path in files])
    active_files = [
        path
        for path in files
        if not _is_legacy_frozen_path(root, path)
        and _git_state(root, path, file_states) != "ignored"
    ]
    checks = [
        _check_contract_shape(),
        _check_legacy_company_paths(root, files, file_states),
        _check_legacy_frozen_surface(root, files),
        _check_chinese_doc_coverage(root, active_files, file_states),
        check_secret_like_fragments(root, files, file_states),
        _check_oversized_files(root, active_files, file_states),
        _check_tracked_runtime_artifacts(root),
    ]
    summary = _summarize_checks(checks)
    status = _overall_status(summary)
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": ARTIFACT_TYPE,
        "audit_id": "afs_maintenance_audit_current",
        "repository": root.name,
        "status": status,
        "checks": checks,
        "summary": summary,
        "workspace_files": workspace_file_summary(file_states),
        "non_claims": [
            "not human acceptance",
            "not business validation",
            "not durable memory",
        ],
        "writes_long_term_memory": False,
        "writes_company_kb": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local AFS maintainability audit.")
    parser.add_argument("--root", default=".", help="Repository root to scan.")
    parser.add_argument("--fail-on", choices=["never", "failed"], default="never")
    args = parser.parse_args()

    report = build_maintenance_audit(Path(args.root))
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if args.fail_on == "failed" and report["summary"]["failed"] > 0:
        return 1
    return 0


def _iter_text_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        relative_path = path.relative_to(root)
        if any(part.endswith(".egg-info") for part in relative_path.parts):
            continue
        relative = relative_path.as_posix()
        if any(relative == excluded or relative.startswith(f"{excluded}/") for excluded in DEFAULT_EXCLUDE_DIRS):
            continue
        try:
            if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
                continue
        except (PermissionError, OSError):
            continue
        yield path


def _check_legacy_company_paths(root: Path, files: list[Path], file_states: dict[str, str]) -> dict[str, Any]:
    findings: list[Finding] = []
    for path in files:
        for line_no, line in _read_lines(path):
            if any(pattern in line for pattern in LEGACY_COMPANY_PATTERNS):
                findings.append(_finding(root, path, "legacy Company source path wording", file_states, line_no))
    return _check("legacy_company_path", "warning" if findings else "passed", findings)


def _check_legacy_frozen_surface(root: Path, files: list[Path]) -> dict[str, Any]:
    frozen_prefixes = sorted(
        {
            prefix
            for path in files
            for prefix in LEGACY_FROZEN_PREFIXES
            if _rel(root, path).startswith(prefix)
        }
    )
    findings = [
        Finding(prefix.rstrip("/"), "legacy-frozen: excluded from active maintainability checks")
        for prefix in frozen_prefixes
    ]
    return _check("legacy_frozen_surface", "warning" if findings else "passed", findings)


def _check_contract_shape() -> dict[str, Any]:
    return _check("audit_contract_shape", "passed", [])


def _is_legacy_frozen_path(root: Path, path: Path) -> bool:
    relative = _rel(root, path)
    return any(relative.startswith(prefix) for prefix in LEGACY_FROZEN_PREFIXES)


def _check_chinese_doc_coverage(root: Path, files: list[Path], file_states: dict[str, str]) -> dict[str, Any]:
    findings: list[Finding] = []
    exempted_historical = 0
    doc_files = [path for path in files if path.suffix.lower() == ".md"]
    for path in doc_files:
        text = _read_text(path)
        if _is_machine_or_archive_doc(path):
            continue
        if _is_historical_doc_with_summary(root, path):
            exempted_historical += 1
            continue
        if _chinese_ratio(text) < 0.08:
            findings.append(_finding(root, path, "human-facing Markdown is not substantially Chinese", file_states))
    status = "warning" if findings else "passed"
    return {
        **_check("human_doc_chinese_coverage", status, findings[:80]),
        "total_markdown_files": len(doc_files),
        "historical_summary_path": HISTORICAL_SUMMARY_PATH,
        "historical_docs_exempted_count": exempted_historical,
        "warning_limit_applied": len(findings) > 80,
    }


def _check_oversized_files(root: Path, files: list[Path], file_states: dict[str, str]) -> dict[str, Any]:
    findings = []
    for path in files:
        if _is_machine_or_archive_doc(path) or _is_historical_doc_with_summary(root, path):
            continue
        line_count = sum(1 for _ in _read_lines(path))
        if line_count > 300:
            findings.append(_finding(root, path, f"{line_count} lines; review split or archive", file_states))
    return _check("oversized_files", "warning" if findings else "passed", findings)


def _check_tracked_runtime_artifacts(root: Path) -> dict[str, Any]:
    tracked = git_ls_files(root)
    runtime_prefixes = ("data/processed/", "data/raw/", "data/reports/")
    findings = [
        Finding(path, "runtime artifact appears tracked by git")
        for path in tracked
        if path.startswith(runtime_prefixes)
        and not path.endswith("/.gitkeep")
    ]
    return _check("tracked_runtime_artifacts", "failed" if findings else "passed", findings)


def _check(check_id: str, status: str, findings: list[Finding]) -> dict[str, Any]:
    payload = {
        "check_id": check_id,
        "status": status,
        "count": len(findings),
        "findings": [finding.as_dict() for finding in findings],
    }
    source_summary = _source_summary(findings)
    if source_summary:
        payload["source_summary"] = source_summary
    return payload


def _source_summary(findings: list[Finding]) -> dict[str, int]:
    summary: dict[str, int] = {}
    for finding in findings:
        if finding.git_state is None:
            continue
        summary[finding.git_state] = summary.get(finding.git_state, 0) + 1
    return summary


def _summarize_checks(checks: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "passed": sum(1 for check in checks if check["status"] == "passed"),
        "warning": sum(1 for check in checks if check["status"] == "warning"),
        "failed": sum(1 for check in checks if check["status"] == "failed"),
    }


def _overall_status(summary: dict[str, int]) -> str:
    if summary["failed"]:
        return "failed"
    if summary["warning"]:
        return "warning"
    return "passed"


def _read_lines(path: Path) -> Iterable[tuple[int, str]]:
    return enumerate(_read_text(path).splitlines(), start=1)


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except (PermissionError, OSError):
        return ""


def _chinese_ratio(text: str) -> float:
    human_text = _strip_machine_contract_text(text)
    stripped = "".join(ch for ch in human_text if not ch.isspace())
    if not stripped:
        return 1.0
    chinese = sum(1 for ch in stripped if "\u4e00" <= ch <= "\u9fff")
    return chinese / len(stripped)


def _strip_machine_contract_text(text: str) -> str:
    without_fenced_blocks = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    return re.sub(r"`[^`]*`", " ", without_fenced_blocks)


def _is_machine_or_archive_doc(path: Path) -> bool:
    normalized = path.as_posix().lower()
    return "/archive/" in normalized or "/tests/fixtures/" in normalized or normalized.endswith(".example.md")


def _is_historical_doc_with_summary(root: Path, path: Path) -> bool:
    summary_path = root / HISTORICAL_SUMMARY_PATH
    if not summary_path.exists():
        return False
    relative = _rel(root, path)
    if relative == HISTORICAL_SUMMARY_PATH:
        return False
    if any(relative.startswith(prefix) for prefix in HISTORICAL_DOC_PREFIXES):
        return True
    return any(fnmatch.fnmatch(relative, pattern) for pattern in HISTORICAL_DOC_GLOBS)


def _git_state(root: Path, path: Path, file_states: dict[str, str]) -> str:
    return file_states.get(_rel(root, path), "unknown")


def _finding(root: Path, path: Path, detail: str, file_states: dict[str, str], line: int | None = None) -> Finding:
    return Finding(_rel(root, path), detail, line, _git_state(root, path, file_states))


def _rel(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root).as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
