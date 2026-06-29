from __future__ import annotations

import subprocess
from pathlib import Path


def git_ls_files(root: Path) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except (OSError, subprocess.CalledProcessError):
        return []
    return [line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()]


def git_file_states(root: Path, relative_paths: list[str]) -> dict[str, str]:
    if not _is_git_worktree(root):
        return {relative: "unknown" for relative in relative_paths}
    tracked = set(git_ls_files(root))
    ignored = _git_check_ignored(root, relative_paths)
    states: dict[str, str] = {}
    for relative in relative_paths:
        if relative in tracked:
            states[relative] = "tracked"
        elif relative in ignored:
            states[relative] = "ignored"
        else:
            states[relative] = "untracked"
    return states


def workspace_file_summary(file_states: dict[str, str]) -> dict[str, int]:
    return {
        "tracked_text_files": sum(1 for state in file_states.values() if state == "tracked"),
        "untracked_text_files": sum(1 for state in file_states.values() if state == "untracked"),
        "ignored_text_files": sum(1 for state in file_states.values() if state == "ignored"),
        "unknown_text_files": sum(1 for state in file_states.values() if state == "unknown"),
    }


def _is_git_worktree(root: Path) -> bool:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except OSError:
        return False
    return result.returncode == 0 and result.stdout.strip().lower() == "true"


def _git_check_ignored(root: Path, relative_paths: list[str]) -> set[str]:
    if not relative_paths:
        return set()
    try:
        result = subprocess.run(
            ["git", "check-ignore", "--stdin"],
            cwd=root,
            input="\n".join(relative_paths) + "\n",
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
    except OSError:
        return set()
    if result.returncode not in {0, 1}:
        return set()
    return {_normalize_git_path(line) for line in result.stdout.splitlines() if line.strip()}


def _normalize_git_path(value: str) -> str:
    cleaned = value.strip().strip('"').replace("\\r", "").replace("\\n", "")
    return cleaned.replace("\\", "/")
