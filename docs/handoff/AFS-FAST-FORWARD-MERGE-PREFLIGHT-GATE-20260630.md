# AFS TaskRun - Fast-Forward Merge Preflight Gate - 2026-06-30

## Task

Task ID: `AFS-T19a Fast-Forward Merge Preflight Gate`

Branch: `codex/afs-project-book-full-goal-20260630`

Start HEAD: `38a1bdeacecaf2a347c063b058c65b5aba5b6371`

Base: `origin/master` at `6071ef1aa665930df2b9fa383260fc68ed4e4e64`

Status: implemented and locally verified; pending final commit/push and
post-commit branch preflight at time of writing.

## 中文结论

本轮不执行 `master` 合并，也不做服务器 `/home`、服务器 `/opt` 同步，不重启
Runtime，不检查线上 `/health`，不打开 provider gate。它只补齐一个合并前必须
明确的机器证据：当前 `origin/master` 是否真的是 codex 分支 `HEAD` 的祖先。

这个判断很关键。上一轮 T18 已经说明 codex 分支可以进入人工合并评审，但如果
后续真正执行合并，仍需要确认它是 fast-forward candidate，避免在授权合并时才发现
`master` 与 codex 分支发生分叉、需要额外冲突处理或改写历史。本轮把这个判断纳入
既有的 `tools/afs_goal_mode_branch_integration_review.py`，而不是新增第二套合并工具，
以减少维护债务。

新增字段：

- `base_is_ancestor_of_head`: `origin/master` 是否是当前 `HEAD` 的祖先。
- `merge_mode_recommendation`: 没有 blocker 且 base 是祖先时返回
  `fast_forward_candidate_after_human_authorization`。
- `base_not_ancestor_of_head`: 如果 base 不是祖先，直接作为 blocker，阻止把该分支
  误报为可合并评审通过。

因此，下一轮如果用户明确授权 `AFS-T19 Authorized Master Merge + Three-End Sync`，
执行者可以先看这个字段，再决定是否进行 fast-forward merge。即使该字段为 green，
仍然不能跳过人工授权、`master` 上的本地验证、GitHub `origin/master` 推送、服务器
两处 checkout 同步和 Runtime `/health` 分离核验。

## Dirty Ownership Ledger

| Surface | Ownership | Handling |
|---|---|---|
| `tools/afs_goal_mode_branch_integration_review.py` | T19a preflight enhancement | Keep; extends the existing review tool instead of adding a parallel merge tool. |
| `tests/test_afs_goal_mode_branch_integration_review.py` | T19a regression | Keep; blocks base/head divergence. |
| `docs/handoff/AFS-FAST-FORWARD-MERGE-PREFLIGHT-GATE-20260630.md` | T19a TaskRun evidence | Keep. |
| `DEVLOG.md`, `TASK_TRACKER.md`, `docs/handoff/INDEX.md` | T19a records | Keep. |
| External execution state YAML | T19a state | Update minimally outside AFS git. |
| `docs/demo-docs-20260629/` | pre-existing untracked docs | Do not touch, do not stage, do not clean. |

## Read Scope

- `AGENTS.md`
- `docs/company_operating_model.md`
- `TASK_TRACKER.md`
- `docs/handoff/AFS-HUMAN-MERGE-REVIEW-BASELINE-DECISION-20260630.md`
- `tools/afs_goal_mode_branch_integration_review.py`
- `tests/test_afs_goal_mode_branch_integration_review.py`
- Current git refs and branch status
- External execution state YAML

## Write Scope

- `tools/afs_goal_mode_branch_integration_review.py`
- `tests/test_afs_goal_mode_branch_integration_review.py`
- This handoff
- `DEVLOG.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- External execution state YAML

## Contract

The branch integration review now additionally guarantees:

- It uses `git merge-base --is-ancestor <base-ref> HEAD` to determine whether
  the merge-review base is an ancestor of the current branch.
- It includes `base_is_ancestor_of_head` in the safe JSON report.
- It includes a `merge_mode_recommendation` field for the next human-authorized
  merge task.
- It blocks review with `base_not_ancestor_of_head` if the base is not an
  ancestor of `HEAD`.
- It still does not merge, deploy, sync servers, call providers, read secrets,
  or inspect generated media bytes.

## Verification

```text
.\.venv\Scripts\python.exe -m pytest tests\test_afs_goal_mode_branch_integration_review.py -q
# 5 passed

.\.venv\Scripts\python.exe -m pytest
# 718 passed, 520 deselected, 2 existing warnings

npm.cmd run check:studio-js
# JS syntax check passed: 128 files

.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; passed=3; warning=4
# existing warnings remain: legacy_frozen_surface=10,
# human_doc_chinese_coverage=22, secret_like_fragments=9, oversized_files=59

git diff --check
# passed

.\.venv\Scripts\python.exe tools\afs_goal_mode_branch_integration_review.py --report runs\goal_mode_branch_integration_review_t19a_dirty.json
# status=needs_attention; blocker_count=1
# expected while T19a files are dirty:
# base_is_ancestor_of_head=true; merge_mode_recommendation=blocked
```

Post-commit branch preflight must be rerun after this TaskRun is committed and
pushed. The expected final state is `ready_for_human_merge_review` with
`merge_mode_recommendation=fast_forward_candidate_after_human_authorization`.

## Evidence State

```text
structure_verified_fast_forward_merge_preflight_no_merge
```

This is merge-readiness evidence only. It is not a merge, not server sync, not
Runtime health verification, not provider smoke, not human creative acceptance,
not business validation, and not final MVP completion.

## Cleanup Review

- Reused the existing branch integration review tool.
- Kept the tool under the 300-line ideal threshold after the enhancement.
- Added one focused unit test instead of adding a new shell-only process.
- Did not change Runtime, Studio, OpenAPI, provider config, generated media, or
  server state.
- Did not touch or stage `docs/demo-docs-20260629/`.

## Deferred Items

- Actual merge to `master` still requires explicit human authorization.
- Server `/home` and `/opt` sync remains a separate authorized task.
- Runtime `/health` remains a post-sync check, not a local branch-review claim.
- Provider smoke still requires explicit capability authorization.

## Next Valid Task

```text
AFS-T19 Authorized Master Merge + Three-End Sync
```
