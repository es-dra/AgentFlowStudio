# AFS TaskRun - Goal-Mode Branch Integration Review - 2026-06-30

## Task

Task ID: `AFS-T17 Goal-Mode Branch Integration Review`

Branch: `codex/afs-project-book-full-goal-20260630`

Start HEAD: `1af42f1462632436452dfe7358c7bbd9115cdf70`

Status: implemented and locally verified; pending commit/push at time of writing.

本轮目标是在进入人工 merge 决策、服务器同步或 provider smoke 之前，给
goal-mode codex 分支增加一个本地、可重复、无 provider 成本的集成审查门。
它只判断当前分支是否适合进入人工合并评审，不执行 merge、deploy、server sync、
Runtime health 检查或 live provider 调用。

## 中文结论

`codex/afs-project-book-full-goal-20260630` 已经累积多轮目标模式提交。此前每轮
都有 focused/full verification 和 handoff，但进入 master 或三端同步前还缺少一个
专门回答“当前分支是否干净、是否已推送、是否覆盖 handoff、是否夹带本地产物”的
机器可执行检查。

本轮新增 `tools/afs_goal_mode_branch_integration_review.py`，默认对比
`origin/master..HEAD`，检查以下边界：

- 当前分支必须是 `codex/*`。
- 本地 `HEAD`、upstream 和 GitHub 远端同名分支必须一致。
- 本地 `master` 必须与 `origin/master` 一致，避免基线漂移。
- worktree 只能保留明确允许的既有未跟踪目录 `docs/demo-docs-20260629/`。
- 分支差异不能包含 `runs/`、本地 provider config、env 文件、数据目录或媒体产物。
- 新增 handoff 必须被 `docs/handoff/INDEX.md` 索引。

当无 blocker 时，工具返回 `ready_for_human_merge_review`。这仍然只是人工合并评审
入口，不代表可以自动 merge、部署或打开 provider gate。

## Dirty Ownership Ledger

| Surface | Ownership | Handling |
|---|---|---|
| `tools/afs_goal_mode_branch_integration_review.py` | T17 branch review gate | Keep; single deterministic review tool for pre-merge branch hygiene. |
| `tests/test_afs_goal_mode_branch_integration_review.py` | T17 contract tests | Keep; locks dirty ledger, handoff index, forbidden artifact, and branch alignment behavior. |
| `DEVLOG.md`, `TASK_TRACKER.md`, `docs/handoff/INDEX.md` | T17 records | Keep. |
| This handoff | T17 TaskRun evidence | Keep. |
| External execution state YAML | T17 state | Update minimally outside AFS git after final commit/push. |
| `docs/demo-docs-20260629/` | pre-existing untracked docs | Do not touch, do not stage, do not clean. |

## Read Scope

- `AGENTS.md`
- `docs/company_operating_model.md`
- `TASK_TRACKER.md`
- `DEVLOG.md`
- `docs/handoff/INDEX.md`
- `docs/handoff/AFS-PROVIDER-SMOKE-READINESS-GATE-20260630.md`
- `docs/handoff/AFS-DETERMINISTIC-PROMOTION-BROWSER-HARNESS-20260630.md`
- `docs/handoff/AFS-DETERMINISTIC-PROMOTION-UI-HARNESS-20260630.md`
- `docs/GFR_EXECUTION_PROJECTION.md`
- `pyproject.toml`
- `tools/afs_provider_connected_validation_readiness.py`
- `tests/test_afs_provider_connected_validation_readiness.py`
- project-book execution state, task ledger, runbook, execution spec, readiness review, and project book

## Write Scope

- `tools/afs_goal_mode_branch_integration_review.py`
- `tests/test_afs_goal_mode_branch_integration_review.py`
- `DEVLOG.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- this handoff
- external execution state YAML

## Contract

The branch integration review guarantees:

- It is a no-cost local/GitHub branch hygiene report.
- It fetches `origin` by default before comparing refs.
- It does not read provider secrets, provider config contents, signed URLs,
  local private media bytes, generated media, or provider raw responses.
- It does not call Runtime provider routes or start any provider.
- It does not merge, deploy, restart services, or sync server checkouts.
- It separates branch readiness for human merge review from runtime verification,
  provider smoke, human acceptance, business validation, and durable memory promotion.

## Verification

```text
.\.venv\Scripts\python.exe -m pytest tests\test_afs_goal_mode_branch_integration_review.py -q
# 4 passed

.\.venv\Scripts\python.exe -m pytest
# 717 passed, 520 deselected, 2 existing warnings

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
```

Post-commit remote branch alignment must be rerun after this TaskRun is
committed and pushed. The review tool intentionally cannot return a clean
branch-review result while the T17 files themselves are still dirty.

## Evidence State

```text
structure_verified_goal_mode_branch_integration_review_no_merge
```

This is branch-integration readiness only. It is not a merge, not deploy
verification, not server three-end sync, not live provider smoke, not generated
media evidence, not human creative acceptance, not business validation, and not
durable memory promotion.

## Cleanup Review

- Added one focused review tool instead of spreading branch hygiene checks across
  hand-written shell steps.
- Kept the tool under the project 300-line ideal threshold.
- Kept tests at the pure contract layer so they do not require network, server,
  provider config, Runtime health, or generated artifacts.
- Did not modify Runtime, Studio, OpenAPI, provider config, or generated media.
- Did not touch or stage `docs/demo-docs-20260629/`.

## Deferred Items

- Human review must decide whether to merge the codex branch to `master`.
- If merged, a separate explicit task should perform local/GitHub/server
  three-end sync and Runtime `/health` verification.
- Live LLM/image provider smoke still requires explicit user authorization and
  should remain separate from branch integration review.
- Any generated media, browser screenshots, or provider reports must stay out of
  git unless a future task explicitly defines a safe artifact contract.

## Next Valid Task

```text
AFS-T18 Human Merge Review + Baseline Freeze Decision
```
