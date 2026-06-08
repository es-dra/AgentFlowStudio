from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

try:
    from tools.repository_retention_policy import is_excluded, review_directory, review_file
except ModuleNotFoundError:
    from repository_retention_policy import is_excluded, review_directory, review_file


SCHEMA_VERSION = "0.1.0"
ARTIFACT_TYPE = "agentflow_repository_retention_review"


def build_repository_retention_review(root: Path) -> dict[str, Any]:
    root = root.resolve()
    files = _collect_files(root)
    directories = _collect_directories(files)
    directory_reviews = [
        review_directory(path)
        for path in directories
        if not is_excluded(path)
    ]
    file_reviews = [
        review_file(path, git_state)
        for path, git_state in files.items()
        if not is_excluded(path)
    ]
    delete_candidates = [
        item
        for item in [*directory_reviews, *file_reviews]
        if item.status != "remove_applied_pending_stage"
        and (item.status == "delete_candidate" or item.product_surface == "delete_candidate")
    ]
    manual_review_required = [
        item for item in [*directory_reviews, *file_reviews] if item.status == "manual_review_required"
    ]
    status_counts: dict[str, int] = {}
    surface_counts: dict[str, int] = {}
    for item in [*directory_reviews, *file_reviews]:
        status_counts[item.status] = status_counts.get(item.status, 0) + 1
        surface_counts[item.product_surface] = surface_counts.get(item.product_surface, 0) + 1

    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": ARTIFACT_TYPE,
        "review_id": "afs_repository_retention_review_current",
        "repository": root.name,
        "summary": {
            "directory_count": len(directory_reviews),
            "file_count": len(file_reviews),
            "delete_candidate_count": len(delete_candidates),
            "manual_review_required_count": len(manual_review_required),
            "status_counts": status_counts,
            "product_surface_counts": surface_counts,
        },
        "directories": [item.as_dict() for item in directory_reviews],
        "files": [item.as_dict() for item in file_reviews],
        "non_claims": [
            "not human acceptance",
            "not business validation",
            "not durable memory",
        ],
        "writes_long_term_memory": False,
        "writes_company_kb": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Review AFS repository paths for retention or cleanup.")
    parser.add_argument("--root", default=".", help="Repository root to scan.")
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Print only counts and candidate lists.",
    )
    args = parser.parse_args()

    report = build_repository_retention_review(Path(args.root))
    if args.summary_only:
        report = {
            key: report[key]
            for key in (
                "schema_version",
                "artifact_type",
                "review_id",
                "repository",
                "summary",
                "non_claims",
                "writes_long_term_memory",
                "writes_company_kb",
            )
        }
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def _collect_files(root: Path) -> dict[str, str]:
    tracked = _git_paths(root, ["git", "ls-files", "-z"])
    untracked = _git_paths(root, ["git", "ls-files", "--others", "--exclude-standard", "-z"])
    if not tracked and not untracked:
        return {
            path.relative_to(root).as_posix(): "filesystem"
            for path in root.rglob("*")
            if path.is_file()
        }
    files = {
        path: "deleted" if not (root / path).exists() else "tracked"
        for path in tracked
    }
    for path in untracked:
        files.setdefault(path, "untracked")
    return dict(sorted(files.items()))


def _git_paths(root: Path, command: list[str]) -> list[str]:
    try:
        result = subprocess.run(
            command,
            cwd=root,
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return []
    raw = result.stdout.decode("utf-8", errors="ignore")
    return sorted(path.replace("\\", "/") for path in raw.split("\0") if path)


def _collect_directories(files: dict[str, str]) -> list[str]:
    directories = {"."}
    for file_path, git_state in files.items():
        if git_state == "deleted":
            continue
        current = Path(file_path).parent
        while str(current) not in ("", "."):
            directories.add(current.as_posix())
            current = current.parent
    return sorted(directories)

if __name__ == "__main__":
    raise SystemExit(main())
