# AFS TaskRun - Human Merge Review + Baseline Freeze Decision - 2026-06-30

## Task

Task ID: `AFS-T18 Human Merge Review + Baseline Freeze Decision`

Branch: `codex/afs-project-book-full-goal-20260630`

Start HEAD: `21760e5d59707323ff305ae6a90e8ffa719b04cf`

Base: `origin/master` at `6071ef1aa665930df2b9fa383260fc68ed4e4e64`

Status: implemented as a merge-review evidence packet; no merge, deploy, server
sync, Runtime restart, Runtime health claim, provider smoke, human acceptance,
business validation, or durable memory promotion was performed.

本轮目标是把 goal-mode codex 分支从“机器审查通过”推进到“可交给人做
merge / baseline freeze 决策”的证据状态。它不替代人的合并决定，也不把
codex 分支自动提升为 `master` 或服务器运行基线。

## Decision Summary

## 中文决策说明

本轮结论不是“已经可以直接合并并上线”，而是“当前 codex 分支已经具备交给人做
合并评审的证据条件”。这一区分很重要：机器审查能够证明分支引用一致、工作树没有
未知脏改动、handoff 已索引、没有把本地运行产物或 provider 敏感面带进 Git；但它
不能替代人对产品方向、风险接受度、是否冻结为新主线基线的判断。

当前建议是：如果项目负责人认可这一轮 goal-mode 分支的 15 个提交和对应的 15 个
TaskRun 记录，可以另开一个明确授权的 merge 任务，把
`codex/afs-project-book-full-goal-20260630` 合入 `master`。合入后必须重新在
`master` 上跑本地验证，再推送 `origin/master`，然后用单独任务同步服务器
`/home/afs-ops/AgentFlowStudio` 和 `/opt/afs/AgentFlowStudio`，最后再检查 Runtime
`/health`。这些步骤不能因为当前分支审查为 green 就合并成一句“全部成功”。

本轮也不打开 provider gate。即使服务器或本地环境变量中曾经观察到 LLM/image/video
相关 gate 状态，也只能说明环境具备某些技术条件，不代表本会话获得了 live provider
调用授权。真正的 provider smoke 必须单独说明能力范围、成本风险、保存路径和清理
策略，并且不能把 provider raw response、signed URL、secret、cookie、本地私有素材
字节或生成媒体字节写入仓库。

因此，本 handoff 的用途是让下一位执行者或项目负责人清楚看到：当前分支是一个
可审查的 baseline candidate；`master` 仍停留在上一轮三端同步基线；服务器未同步；
Runtime 健康未复核；human creative acceptance 和 business validation 仍未发生。下一步
只有在明确授权后，才应该进入 master merge 和三端同步。

Current judgment:

```text
ready_for_human_merge_review_with_constraints
```

The codex branch is a valid merge-review candidate because:

- Local HEAD, upstream, and GitHub remote branch are aligned at
  `21760e5d59707323ff305ae6a90e8ffa719b04cf`.
- Local `master` and `origin/master` remain aligned at the frozen three-end
  baseline `6071ef1aa665930df2b9fa383260fc68ed4e4e64`.
- `tools/afs_goal_mode_branch_integration_review.py` reports
  `ready_for_human_merge_review` with `blocker_count=0`.
- The accumulated branch has 15 commits, 77 changed files, and 15 indexed
  TaskRun handoffs since `origin/master`.
- The AFS worktree is clean except the pre-existing untracked
  `docs/demo-docs-20260629/`, which remains do-not-touch and unstaged.

Constraints:

- This is not approval to merge. Human approval is still required.
- This is not server sync. Server `/home` and `/opt` checkouts were not touched.
- This is not Runtime health verification. `/health` was not checked in this
  TaskRun.
- This is not provider smoke. No LLM/image/video/vision/ASR/external download
  provider call was authorized or started.
- This is not human creative acceptance or business validation.

## Dirty Ownership Ledger

| Surface | Ownership | Handling |
|---|---|---|
| `docs/handoff/AFS-HUMAN-MERGE-REVIEW-BASELINE-DECISION-20260630.md` | T18 review packet | Keep as the human merge-review evidence entry. |
| `docs/handoff/AFS-GOAL-MODE-BRANCH-INTEGRATION-REVIEW-20260630.md` | T17 record correction | Keep; update stale pending commit/push wording after post-commit verification. |
| `DEVLOG.md`, `TASK_TRACKER.md`, `docs/handoff/INDEX.md` | T18 records | Keep. |
| External execution state YAML | T18 state | Update minimally outside AFS git. |
| `runs/goal_mode_branch_integration_review_t18_preflight.json` | ignored local evidence | Do not commit. |
| `docs/demo-docs-20260629/` | pre-existing untracked docs | Do not touch, do not stage, do not clean. |

## Read Scope

- `AGENTS.md`
- `docs/company_operating_model.md`
- `TASK_TRACKER.md`
- `DEVLOG.md`
- `docs/handoff/INDEX.md`
- `docs/handoff/AFS-GOAL-MODE-BRANCH-INTEGRATION-REVIEW-20260630.md`
- `D:\Learning materials\Learning_notes\10-Startup\70-Projects\AI-Native-Project-Books\2026-06-30-COS-AFS-autonomous-project-book\AFS-Task-Ledger-v0.1.md`
- `D:\Learning materials\Learning_notes\10-Startup\70-Projects\AI-Native-Project-Books\2026-06-30-COS-AFS-autonomous-project-book\AFS-Goal-Driven-Execution-State-v0.1.yaml`
- Current git refs, branch review report, commit list, and diff stat

## Write Scope

- This handoff
- `docs/handoff/AFS-GOAL-MODE-BRANCH-INTEGRATION-REVIEW-20260630.md`
- `DEVLOG.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- External execution state YAML

## Branch Facts

```text
branch=codex/afs-project-book-full-goal-20260630
head=21760e5d59707323ff305ae6a90e8ffa719b04cf
upstream_head=21760e5d59707323ff305ae6a90e8ffa719b04cf
remote_head=21760e5d59707323ff305ae6a90e8ffa719b04cf
base_ref=origin/master
base_head=6071ef1aa665930df2b9fa383260fc68ed4e4e64
commit_count_since_base=15
changed_file_count=77
handoff_count=15
branch_review_status=ready_for_human_merge_review
branch_review_blockers=0
```

Commit stack since `origin/master`:

```text
21760e5d test(governance): add goal-mode branch review
1af42f14 test(provider): calibrate smoke readiness gate
abea0d15 test(studio): add promotion browser harness
fe4be34b feat(studio): add deterministic promotion harness
e2a48622 docs(handoff): record browser studio gate flow QA
f758ca8d feat(runtime): add asset promotion gate provenance
510684c0 feat(studio): add human gate hook
4c18b266 feat(runtime): add human gate contract
9a478694 feat(runtime): add keyframe generation bridge
71060697 feat(runtime): add storyboard evidence ledger
0121a995 test(runtime): guard asset card candidate context boundary
a2016bc4 feat(runtime): add storyboard asset card candidates
72f818c3 feat(runtime): add storyboard production graph snapshot
d55ecdb9 test(storyboard): add content quality benchmark scripts
8c20e4da feat(runtime): add storyboard content quality report
```

## Merge Recommendation

Recommended human decision route:

1. Review this packet plus the 15 TaskRun handoffs indexed under Goal / Release
   Gates.
2. If acceptable, authorize a separate `master` merge task.
3. Prefer preserving the existing commit stack rather than squashing, because
   each commit has a TaskRun boundary, verification evidence, and a cleanup
   review.
4. After merge authorization, run a fresh local verification set on `master`,
   push `origin/master`, then run a separate three-end sync task for server
   `/home`, server `/opt`, and Runtime `/health`.

Do not combine human merge decision, master push, server sync, Runtime health,
and provider smoke into one unreviewed step.

## Verification

```text
.\.venv\Scripts\python.exe tools\afs_goal_mode_branch_integration_review.py --report runs\goal_mode_branch_integration_review_t18_preflight.json
# status=ready_for_human_merge_review; blocker_count=0

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

Post-commit branch review must be rerun after this packet is committed and
pushed. While this T18 packet is dirty, the branch-review tool correctly reports
`disallowed_worktree_dirty`.

## Evidence State

```text
structure_verified_human_merge_review_baseline_candidate_no_merge
```

This evidence supports a human merge-review decision only. It does not prove
server deployment, Runtime health, provider smoke, human creative acceptance,
business validation, or final MVP completion.

## Cleanup Review

- No product code, Runtime route, Studio UI, OpenAPI schema, provider adapter,
  or generated media was changed.
- T17 handoff had stale `pending commit/push` wording after the final push; this
  TaskRun corrects the record instead of leaving a misleading handoff.
- The existing T17 branch-review tool is reused; no parallel merge-review tool
  is introduced.
- Generated `runs/` reports remain ignored and uncommitted.
- `docs/demo-docs-20260629/` remains untouched.

## Deferred Items

- Actual merge to `master` requires explicit human authorization.
- Server `/home` and `/opt` sync requires a separate sync task.
- Runtime `/health` must be checked after server sync, not inferred from local
  branch review.
- Live provider smoke requires explicit capability authorization and must remain
  separate from merge/sync.
- Human creative acceptance and business validation remain unclaimed.

## Next Valid Task

```text
AFS-T19 Authorized Master Merge + Three-End Sync
```

Alternative next task if merge is not authorized:

```text
AFS-T18a Authorized One-Sample LLM+Image Provider Smoke
```
