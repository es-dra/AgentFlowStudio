from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tools.afs_pr_stack_drift_guard import StackEntry, collect_pr_stack_drift_guard


def test_pr_stack_drift_guard_allows_linear_stack(tmp_path: Path) -> None:
    shas = _init_linear_stack(tmp_path)

    report = collect_pr_stack_drift_guard(
        repo_root=tmp_path,
        entries=[
            StackEntry(
                label="pr-1",
                base_ref="master",
                head_ref="feature-one",
                expected_base_sha=shas["master"],
                expected_head_sha=shas["feature-one"],
            ),
            StackEntry(
                label="pr-2",
                base_ref="feature-one",
                head_ref="feature-two",
                expected_base_sha=shas["feature-one"],
                expected_head_sha=shas["feature-two"],
            ),
        ],
        fetch=False,
    )

    assert report["status"] == "stack_ready_for_review"
    assert report["blockers"] == []
    assert report["entries"][1]["previous_head_is_ancestor_of_head"] is True
    assert report["provider_calls_started"] is False
    assert "not a merge" in report["non_claims"]


def test_pr_stack_drift_guard_blocks_when_base_ref_advances(tmp_path: Path) -> None:
    shas = _init_linear_stack(tmp_path)
    _run_git(tmp_path, "checkout", "master")
    _commit(tmp_path, "base-drift.txt", "base advanced\n", "advance base")

    report = collect_pr_stack_drift_guard(
        repo_root=tmp_path,
        entries=[
            StackEntry(
                label="pr-1",
                base_ref="master",
                head_ref="feature-one",
                expected_base_sha=shas["master"],
            )
        ],
        fetch=False,
    )

    blocker_ids = {block["block_id"] for block in report["blockers"]}
    assert report["status"] == "needs_attention"
    assert "base_ref_drifted" in blocker_ids
    assert "base_not_ancestor_of_head" in blocker_ids
    assert report["recommended_next_action"] == "Rebase or retarget the affected stack entry before claiming integration readiness."


def test_pr_stack_drift_guard_blocks_broken_stack_base_ref(tmp_path: Path) -> None:
    _init_linear_stack(tmp_path)

    report = collect_pr_stack_drift_guard(
        repo_root=tmp_path,
        entries=[
            StackEntry(label="pr-1", base_ref="master", head_ref="feature-one"),
            StackEntry(label="pr-2", base_ref="master", head_ref="feature-two"),
        ],
        fetch=False,
    )

    assert {
        "block_id": "stack_base_ref_not_previous_head_ref",
        "label": "pr-2",
        "base_ref": "master",
        "previous_label": "pr-1",
        "previous_head_ref": "feature-one",
    } in report["blockers"]


def test_pr_stack_drift_guard_cli_outputs_status_json(tmp_path: Path) -> None:
    _init_linear_stack(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            "tools/afs_pr_stack_drift_guard.py",
            "--repo-root",
            str(tmp_path),
            "--no-fetch",
            "--entry",
            "pr-1,master,feature-one",
            "--entry",
            "pr-2,feature-one,feature-two",
        ],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert json.loads(result.stdout) == {"status": "stack_ready_for_review", "blocker_count": 0}


def _init_linear_stack(repo: Path) -> dict[str, str]:
    _run_git(repo, "init", "-b", "master")
    _run_git(repo, "config", "user.email", "codex@example.test")
    _run_git(repo, "config", "user.name", "Codex")
    _commit(repo, "root.txt", "root\n", "root")
    master = _sha(repo, "master")
    _run_git(repo, "checkout", "-b", "feature-one")
    _commit(repo, "feature-one.txt", "one\n", "feature one")
    feature_one = _sha(repo, "feature-one")
    _run_git(repo, "checkout", "-b", "feature-two")
    _commit(repo, "feature-two.txt", "two\n", "feature two")
    feature_two = _sha(repo, "feature-two")
    return {"master": master, "feature-one": feature_one, "feature-two": feature_two}


def _commit(repo: Path, relative_path: str, content: str, message: str) -> None:
    path = repo / relative_path
    path.write_text(content, encoding="utf-8")
    _run_git(repo, "add", relative_path)
    _run_git(repo, "commit", "-m", message)


def _sha(repo: Path, ref: str) -> str:
    return _run_git(repo, "rev-parse", ref).stdout.strip()


def _run_git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    repo.mkdir(parents=True, exist_ok=True)
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )
