from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from tools.afs_branch_size_thresholds import build_branch_size_thresholds, diff_numstat_summary
except ModuleNotFoundError:
    from afs_branch_size_thresholds import build_branch_size_thresholds, diff_numstat_summary


DEFAULT_BASE_REF = "origin/master"
DEFAULT_BRANCH_PREFIX = "codex/"
DEFAULT_ALLOWED_UNTRACKED = ("docs/demo-docs-20260629/",)
FORBIDDEN_PREFIXES = (
    ".env",
    ".dev.vars",
    "configs/providers.local",
    "data/raw/",
    "data/processed/",
    "data/reports/",
    "runs/",
)
FORBIDDEN_MEDIA_SUFFIXES = {
    ".mp4",
    ".mov",
    ".mkv",
    ".webm",
    ".wav",
    ".mp3",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
}


@dataclass(frozen=True)
class CommitSummary:
    commit: str
    subject: str


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    report = collect_branch_integration_review(
        repo_root=Path(args.repo_root).resolve(),
        base_ref=args.base_ref,
        expected_branch_prefix=args.expected_branch_prefix,
        allowed_untracked=tuple(args.allowed_untracked),
        fetch=not args.no_fetch,
    )
    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "blocker_count": len(report["blockers"]), "merge_review_threshold_reached": report["merge_review_thresholds"]["threshold_reached"], "merge_review_threshold_reasons": report["merge_review_thresholds"]["reached"]}, ensure_ascii=False))
    return 0 if report["status"] == "ready_for_human_merge_review" else 2


def collect_branch_integration_review(
    *,
    repo_root: Path,
    base_ref: str = DEFAULT_BASE_REF,
    expected_branch_prefix: str = DEFAULT_BRANCH_PREFIX,
    allowed_untracked: tuple[str, ...] = DEFAULT_ALLOWED_UNTRACKED,
    fetch: bool = True,
) -> dict[str, Any]:
    if fetch:
        _git(repo_root, ["fetch", "origin"])
    branch = _git(repo_root, ["rev-parse", "--abbrev-ref", "HEAD"]).strip()
    head = _git(repo_root, ["rev-parse", "HEAD"]).strip()
    upstream = _git_optional(repo_root, ["rev-parse", "@{u}"]).strip()
    remote = _remote_branch_head(repo_root, branch)
    base_head = _git(repo_root, ["rev-parse", base_ref]).strip()
    base_branch = base_ref.split("/", 1)[-1] if "/" in base_ref else base_ref
    local_base_head = _git_optional(repo_root, ["rev-parse", base_branch]).strip()
    base_is_ancestor = _is_ancestor(repo_root, base_ref, "HEAD")
    status_text = _git(repo_root, ["status", "--short", "--branch"])
    changed_files = _changed_files(repo_root, base_ref)
    commits = _commit_summaries(repo_root, base_ref)
    diff_stat = diff_numstat_summary(repo_root, base_ref)
    thresholds = build_branch_size_thresholds(commit_count=len(commits), changed_file_count=len(changed_files), insertion_count=diff_stat["insertions"])
    index_text = _read_text(repo_root / "docs" / "handoff" / "INDEX.md")
    blockers = build_branch_integration_blockers(
        branch=branch,
        expected_branch_prefix=expected_branch_prefix,
        head=head,
        upstream=upstream,
        remote=remote,
        base_head=base_head,
        local_base_head=local_base_head,
        base_is_ancestor=base_is_ancestor,
        status_text=status_text,
        changed_files=changed_files,
        handoff_index_text=index_text,
        allowed_untracked=allowed_untracked,
    )
    return {
        "artifact_type": "afs_goal_mode_branch_integration_review",
        "schema_version": "0.1.0",
        "status": "ready_for_human_merge_review" if not blockers else "needs_attention",
        "branch": branch,
        "base_ref": base_ref,
        "head": head,
        "upstream_head": upstream,
        "remote_head": remote,
        "base_head": base_head,
        "local_base_head": local_base_head,
        "base_is_ancestor_of_head": base_is_ancestor,
        "merge_mode_recommendation": _merge_mode_recommendation(blockers, base_is_ancestor),
        "commit_count_since_base": len(commits),
        "commits_since_base": [commit.__dict__ for commit in commits],
        "changed_file_count": len(changed_files),
        "insertion_count_since_base": diff_stat["insertions"],
        "deletion_count_since_base": diff_stat["deletions"],
        "binary_file_count_since_base": diff_stat["binary_files"],
        "changed_files": changed_files,
        "merge_review_thresholds": thresholds,
        "handoff_files": _handoff_files(changed_files),
        "allowed_untracked": list(allowed_untracked),
        "blockers": blockers,
        "recommended_next_action": _next_action(blockers),
        "provider_calls_started": False,
        "server_sync_performed": False,
        "deploy_performed": False,
        "secrets_printed": False,
        "non_claims": [
            "not a merge",
            "not deploy verification",
            "not server three-end sync",
            "not provider smoke",
            "not human acceptance",
            "not business validation",
        ],
    }


def build_branch_integration_blockers(
    *,
    branch: str,
    expected_branch_prefix: str,
    head: str,
    upstream: str,
    remote: str,
    base_head: str,
    local_base_head: str,
    base_is_ancestor: bool,
    status_text: str,
    changed_files: list[str],
    handoff_index_text: str,
    allowed_untracked: tuple[str, ...],
) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    if not branch.startswith(expected_branch_prefix):
        blockers.append({"block_id": "unexpected_branch", "branch": branch, "expected_prefix": expected_branch_prefix})
    if not upstream or upstream != head:
        blockers.append({"block_id": "upstream_not_aligned", "head": _short(head), "upstream": _short(upstream)})
    if not remote or remote != head:
        blockers.append({"block_id": "remote_branch_not_aligned", "head": _short(head), "remote": _short(remote)})
    if local_base_head and base_head != local_base_head:
        blockers.append({"block_id": "local_base_not_aligned_with_origin", "base": _short(base_head), "local_base": _short(local_base_head)})
    if not base_is_ancestor:
        blockers.append({"block_id": "base_not_ancestor_of_head", "base": _short(base_head), "head": _short(head)})
    dirty = _disallowed_status_lines(status_text, allowed_untracked)
    if dirty:
        blockers.append({"block_id": "disallowed_worktree_dirty", "lines": dirty})
    forbidden = [path for path in changed_files if _is_forbidden_changed_path(path)]
    if forbidden:
        blockers.append({"block_id": "forbidden_changed_paths", "paths": forbidden})
    missing = _handoff_index_missing(_handoff_files(changed_files), handoff_index_text)
    if missing:
        blockers.append({"block_id": "handoff_index_missing_entries", "paths": missing})
    return blockers


def _changed_files(repo_root: Path, base_ref: str) -> list[str]:
    output = _git(repo_root, ["diff", "--name-only", f"{base_ref}..HEAD"])
    return sorted(line.strip().replace("\\", "/") for line in output.splitlines() if line.strip())


def _commit_summaries(repo_root: Path, base_ref: str) -> list[CommitSummary]:
    output = _git(repo_root, ["log", "--format=%H%x00%s", f"{base_ref}..HEAD"])
    commits: list[CommitSummary] = []
    for line in output.splitlines():
        if "\0" not in line:
            continue
        commit, subject = line.split("\0", 1)
        commits.append(CommitSummary(commit=commit, subject=subject))
    return commits


def _handoff_files(changed_files: list[str]) -> list[str]:
    return [
        path
        for path in changed_files
        if path.startswith("docs/handoff/") and path.endswith(".md") and path != "docs/handoff/INDEX.md"
    ]


def _handoff_index_missing(handoff_files: list[str], handoff_index_text: str) -> list[str]:
    return [path for path in handoff_files if Path(path).name not in handoff_index_text]


def _disallowed_status_lines(status_text: str, allowed_untracked: tuple[str, ...]) -> list[str]:
    dirty: list[str] = []
    for line in status_text.splitlines():
        if not line.strip() or line.startswith("## "):
            continue
        status = line[:2]
        path = line[3:].replace("\\", "/") if len(line) > 3 else ""
        if status == "??" and any(path == item.rstrip("/") or path.startswith(item.rstrip("/") + "/") for item in allowed_untracked):
            continue
        dirty.append(line)
    return dirty


def _is_forbidden_changed_path(path: str) -> bool:
    normalized = path.replace("\\", "/")
    if any(normalized == prefix or normalized.startswith(prefix) for prefix in FORBIDDEN_PREFIXES):
        return True
    return Path(normalized).suffix.lower() in FORBIDDEN_MEDIA_SUFFIXES


def _remote_branch_head(repo_root: Path, branch: str) -> str:
    output = _git_optional(repo_root, ["ls-remote", "origin", f"refs/heads/{branch}"]).strip()
    if not output:
        return ""
    return output.split()[0]


def _is_ancestor(repo_root: Path, ancestor: str, descendant: str) -> bool:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def _merge_mode_recommendation(blockers: list[dict[str, Any]], base_is_ancestor: bool) -> str:
    if blockers:
        return "blocked"
    if base_is_ancestor:
        return "fast_forward_candidate_after_human_authorization"
    return "merge_conflict_or_divergence_review_required"


def _next_action(blockers: list[dict[str, Any]]) -> str:
    if blockers:
        return "Resolve blockers before merge, deploy, or server sync."
    return "Human review may decide whether to merge this codex branch to master; do not deploy until a separate sync task is authorized."


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _short(value: str) -> str:
    return value[:12] if value else ""


def _git(repo_root: Path, args: list[str]) -> str:
    result = subprocess.run(["git", *args], cwd=repo_root, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout


def _git_optional(repo_root: Path, args: list[str]) -> str:
    result = subprocess.run(["git", *args], cwd=repo_root, capture_output=True, text=True, check=False)
    return result.stdout if result.returncode == 0 else ""


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Review AFS goal-mode codex branch before human merge review.")
    parser.add_argument("--repo-root", type=Path, default=Path("."), help="Local repository root.")
    parser.add_argument("--base-ref", default=DEFAULT_BASE_REF, help="Base ref for branch diff review.")
    parser.add_argument("--expected-branch-prefix", default=DEFAULT_BRANCH_PREFIX)
    parser.add_argument("--allowed-untracked", action="append", default=list(DEFAULT_ALLOWED_UNTRACKED))
    parser.add_argument("--no-fetch", action="store_true", help="Skip git fetch before reviewing branch refs.")
    parser.add_argument("--report", default="", help="Optional JSON report path.")
    return parser.parse_args(argv)


if __name__ == "__main__":
    sys.exit(main())
