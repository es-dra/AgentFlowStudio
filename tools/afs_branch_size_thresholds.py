from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any


MERGE_REVIEW_COMMIT_THRESHOLD = 20
MERGE_REVIEW_CHANGED_FILE_THRESHOLD = 80
MERGE_REVIEW_INSERTION_THRESHOLD = 5000


def build_branch_size_thresholds(
    *,
    commit_count: int,
    changed_file_count: int,
    insertion_count: int,
) -> dict[str, Any]:
    reached: list[str] = []
    if commit_count >= MERGE_REVIEW_COMMIT_THRESHOLD:
        reached.append("commits")
    if changed_file_count >= MERGE_REVIEW_CHANGED_FILE_THRESHOLD:
        reached.append("changed_files")
    if insertion_count >= MERGE_REVIEW_INSERTION_THRESHOLD:
        reached.append("insertions")
    return {
        "commit_threshold": MERGE_REVIEW_COMMIT_THRESHOLD,
        "changed_file_threshold": MERGE_REVIEW_CHANGED_FILE_THRESHOLD,
        "insertion_threshold": MERGE_REVIEW_INSERTION_THRESHOLD,
        "commit_count": commit_count,
        "changed_file_count": changed_file_count,
        "insertion_count": insertion_count,
        "threshold_reached": bool(reached),
        "reached": reached,
        "required_action": "enter_merge_review_gate" if reached else "continue_provider_closed_slice",
    }


def diff_numstat_summary(repo_root: Path, base_ref: str) -> dict[str, int]:
    result = subprocess.run(
        ["git", "diff", "--numstat", f"{base_ref}..HEAD"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git diff --numstat failed")
    insertions = 0
    deletions = 0
    binary_files = 0
    for line in result.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        if parts[0].isdigit():
            insertions += int(parts[0])
        else:
            binary_files += 1
        if parts[1].isdigit():
            deletions += int(parts[1])
    return {"insertions": insertions, "deletions": deletions, "binary_files": binary_files}
