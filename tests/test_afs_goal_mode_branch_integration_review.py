from __future__ import annotations

from tools.afs_goal_mode_branch_integration_review import build_branch_integration_blockers


def test_branch_integration_review_allows_known_demo_docs_untracked() -> None:
    blockers = build_branch_integration_blockers(
        branch="codex/afs-project-book-full-goal-20260630",
        expected_branch_prefix="codex/",
        head="abc123",
        upstream="abc123",
        remote="abc123",
        base_head="base123",
        local_base_head="base123",
        status_text="## codex/afs-project-book-full-goal-20260630...origin/codex/afs-project-book-full-goal-20260630\n?? docs/demo-docs-20260629/\n",
        changed_files=[
            "docs/handoff/AFS-PROVIDER-SMOKE-READINESS-GATE-20260630.md",
            "docs/handoff/INDEX.md",
            "tools/afs_provider_connected_validation_readiness.py",
        ],
        handoff_index_text="- `AFS-PROVIDER-SMOKE-READINESS-GATE-20260630.md`\n",
        allowed_untracked=("docs/demo-docs-20260629/",),
    )

    assert blockers == []


def test_branch_integration_review_blocks_missing_handoff_index_entry() -> None:
    blockers = build_branch_integration_blockers(
        branch="codex/afs-project-book-full-goal-20260630",
        expected_branch_prefix="codex/",
        head="abc123",
        upstream="abc123",
        remote="abc123",
        base_head="base123",
        local_base_head="base123",
        status_text="## codex/afs-project-book-full-goal-20260630...origin/codex/afs-project-book-full-goal-20260630\n",
        changed_files=["docs/handoff/AFS-NEW-TASKRUN.md"],
        handoff_index_text="",
        allowed_untracked=("docs/demo-docs-20260629/",),
    )

    assert blockers == [
        {
            "block_id": "handoff_index_missing_entries",
            "paths": ["docs/handoff/AFS-NEW-TASKRUN.md"],
        }
    ]


def test_branch_integration_review_blocks_forbidden_artifact_paths() -> None:
    blockers = build_branch_integration_blockers(
        branch="codex/afs-project-book-full-goal-20260630",
        expected_branch_prefix="codex/",
        head="abc123",
        upstream="abc123",
        remote="abc123",
        base_head="base123",
        local_base_head="base123",
        status_text="## codex/afs-project-book-full-goal-20260630...origin/codex/afs-project-book-full-goal-20260630\n",
        changed_files=["runs/live-smoke.json", "docs/handoff/AFS-OK.md", "apps/studio/assets/generated.png"],
        handoff_index_text="- `AFS-OK.md`\n",
        allowed_untracked=("docs/demo-docs-20260629/",),
    )

    assert blockers == [
        {
            "block_id": "forbidden_changed_paths",
            "paths": ["runs/live-smoke.json", "apps/studio/assets/generated.png"],
        }
    ]


def test_branch_integration_review_blocks_unpushed_or_wrong_branch_state() -> None:
    blockers = build_branch_integration_blockers(
        branch="master",
        expected_branch_prefix="codex/",
        head="abc123",
        upstream="old456",
        remote="",
        base_head="base123",
        local_base_head="base999",
        status_text="## master...origin/master\n M DEVLOG.md\n?? scratch.txt\n",
        changed_files=[],
        handoff_index_text="",
        allowed_untracked=("docs/demo-docs-20260629/",),
    )

    assert [block["block_id"] for block in blockers] == [
        "unexpected_branch",
        "upstream_not_aligned",
        "remote_branch_not_aligned",
        "local_base_not_aligned_with_origin",
        "disallowed_worktree_dirty",
    ]
