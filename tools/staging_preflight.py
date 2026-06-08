from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


MAX_EFFECTIVE_FILE_LINES = 300
STARTUP_KNOWLEDGE_ROOT = r"D:\Learning materials\Learning_notes\10-Startup"
STARTUP_SECRET_PATH = STARTUP_KNOWLEDGE_ROOT + r"\.secrets"

CHECKED_SUFFIXES = {
    ".css",
    ".html",
    ".js",
    ".json",
    ".md",
    ".ps1",
    ".py",
    ".toml",
    ".yaml",
    ".yml",
}

LOCAL_ONLY_PREFIXES = (
    "data/",
    ".venv/",
    ".pytest_cache/",
    ".mypy_cache/",
)
LOCAL_ONLY_EXACT = {
    ".env",
    ".dev.vars",
    "configs/models.yaml",
}
LOCAL_ONLY_NAMES = {
    "__pycache__",
    "providers.local.json",
}
LOCAL_ONLY_SUFFIXES = {
    ".mp3",
    ".mp4",
    ".mov",
    ".mkv",
    ".wav",
    ".webm",
    ".pyc",
    ".pyo",
}


@dataclass(frozen=True)
class Finding:
    code: str
    path: str
    detail: str
    severity: str = "block"


@dataclass(frozen=True)
class PreflightReport:
    status_entries: tuple[str, ...]
    checked_files: tuple[str, ...]
    findings: tuple[Finding, ...]

    @property
    def ok(self) -> bool:
        return not any(finding.severity == "block" for finding in self.findings)


def run_preflight(repo_root: Path, status_text: str | None = None) -> PreflightReport:
    root = repo_root.resolve()
    entries = parse_status(status_text if status_text is not None else git_status_short(root))
    files = tuple(iter_checked_files(root, entries))
    findings = list(check_local_only_paths(entries))
    findings.extend(check_file_line_counts(root, files))
    findings.extend(check_forbidden_content(root, files))
    return PreflightReport(status_entries=tuple(entries), checked_files=files, findings=tuple(findings))


def git_status_short(repo_root: Path) -> str:
    result = subprocess.run(
        ["git", "status", "--short"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git status --short failed")
    return result.stdout


def parse_status(status_text: str) -> list[str]:
    entries: list[str] = []
    for raw_line in status_text.splitlines():
        if not raw_line.strip():
            continue
        path = raw_line[3:].strip()
        if " -> " in path:
            path = path.rsplit(" -> ", 1)[1].strip()
        if path.startswith('"') and path.endswith('"'):
            path = path[1:-1]
        entries.append(_normalize(path))
    return entries


def iter_checked_files(repo_root: Path, status_entries: Iterable[str]) -> Iterable[str]:
    seen: set[str] = set()
    for entry in status_entries:
        path = repo_root / entry
        candidates = path.rglob("*") if path.is_dir() else (path,)
        for candidate in candidates:
            if not candidate.is_file() or candidate.suffix.lower() not in CHECKED_SUFFIXES:
                continue
            rel = _normalize(candidate.relative_to(repo_root).as_posix())
            if rel not in seen:
                seen.add(rel)
                yield rel


def check_local_only_paths(status_entries: Iterable[str]) -> Iterable[Finding]:
    for entry in status_entries:
        normalized = entry.rstrip("/")
        lower = normalized.lower()
        parts = set(lower.split("/"))
        if lower in LOCAL_ONLY_EXACT:
            yield Finding("local-only-path", entry, "local configuration must not be staged")
        elif lower.startswith(LOCAL_ONLY_PREFIXES):
            yield Finding("local-only-path", entry, "local runtime/cache path must not be staged")
        elif parts & LOCAL_ONLY_NAMES:
            yield Finding("local-only-path", entry, "generated cache or local provider config must not be staged")
        elif Path(lower).suffix in LOCAL_ONLY_SUFFIXES:
            yield Finding("local-only-path", entry, "media, bytecode, or generated binary must not be staged")


def check_file_line_counts(repo_root: Path, files: Iterable[str]) -> Iterable[Finding]:
    for rel in files:
        line_count = _line_count(repo_root / rel)
        if line_count > MAX_EFFECTIVE_FILE_LINES:
            yield Finding(
                "oversized-file",
                rel,
                f"{line_count} effective lines exceeds {MAX_EFFECTIVE_FILE_LINES}",
                "warning",
            )


def check_forbidden_content(repo_root: Path, files: Iterable[str]) -> Iterable[Finding]:
    for rel in files:
        path = repo_root / rel
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if STARTUP_SECRET_PATH in text:
            yield Finding("hardcoded-startup-secret-path", rel, "hardcoded local 10-Startup .secrets path")


def format_report(report: PreflightReport) -> str:
    lines = [
        "AFS staging preflight",
        f"status entries: {len(report.status_entries)}",
        f"checked text files: {len(report.checked_files)}",
    ]
    if report.ok:
        lines.append("status: pass")
    else:
        lines.append("status: fail")
    for finding in report.findings:
        prefix = "warning" if finding.severity == "warning" else "block"
        lines.append(f"- {prefix} {finding.code}: {finding.path} ({finding.detail})")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run local AgentFlow Studio staging-boundary preflight.")
    parser.add_argument("--repo-root", type=Path, default=Path("."), help="Repository root to inspect.")
    args = parser.parse_args(argv)

    report = run_preflight(args.repo_root)
    print(format_report(report))
    return 0 if report.ok else 1


def _line_count(path: Path) -> int:
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def _normalize(path: str) -> str:
    return path.replace("\\", "/")


if __name__ == "__main__":
    sys.exit(main())
