# AFS-T39 Goal-Mode Threshold Merge Review Gate

## 任务信息

- Task ID: `AFS-T39`
- 分支: `codex/afs-goal-mode-threshold-gate-20260630`
- Base ref: `origin/master`
- Base HEAD: `f51237df89c680dafc54296d7e013bd98cd459af`
- 本轮审查起点 HEAD: `fa04cfbe83b9559303d256a1b8813d64cce144af`
- 模式: provider-closed merge review gate
- 状态: 本地验证与分支审查已通过；在人工 merge/split/defer 决策前，不应继续在本分支追加功能切片。

本 gate 的原因是分支已经进入强制集成审查区。T38 post-push preflight
显示当前分支相对 `origin/master` 已有 19 commits、59 changed files、4610
insertions。记录 T39 的提交会成为第 20 个 commit，因此会触发已设定的分支阈值。

## Dirty Ownership Ledger

本轮拥有:

- `docs/handoff/AFS-GOAL-MODE-THRESHOLD-MERGE-REVIEW-GATE-20260630.md`
- `docs/handoff/INDEX.md`
- `DEVLOG.md`
- `TASK_TRACKER.md`
- 外部 execution state:
  `D:\Learning materials\Learning_notes\10-Startup\70-Projects\AI-Native-Project-Books\2026-06-30-COS-AFS-autonomous-project-book\AFS-Goal-Driven-Execution-State-v0.1.yaml`

既有 do-not-touch:

- `docs/demo-docs-20260629/` 仍保持 untracked，没有清理、暂存或纳入本轮成果。

## Startup Scan

- `git status --short --branch`: 当前分支追踪
  `origin/codex/afs-goal-mode-threshold-gate-20260630`，只有
  `docs/demo-docs-20260629/` 未跟踪。
- 本地 HEAD 与 upstream 在本轮记录前一致:
  `fa04cfbe83b9559303d256a1b8813d64cce144af`。
- `origin/master`: `f51237df89c680dafc54296d7e013bd98cd459af`。
- `git worktree list --porcelain`: 只有 `D:/Projects/AgentFlowStudio` 一个 worktree。
- 外部 execution state 在本轮开始前已指向 T39 作为下一步有效动作。

## 分支规模

Pre-T39 分支审查报告:

```text
runs\afs_goal_mode_branch_review_t39_precommit.json
```

审查摘要:

- Status: `ready_for_human_merge_review`
- Blockers: `0`
- Commits since `origin/master`: `19`
- Changed files: `59`
- Insertions: `4610`
- Deletions: `20`
- 本轮记录前阈值: 尚未触发
- 本轮记录提交后阈值: 会因 commit count 到 `20` 而触发
- Provider calls started: `false`
- Server sync performed: `false`
- Deploy performed: `false`

本轮记录前的文件分类:

| Category | Files | Insertions | Deletions |
|---|---:|---:|---:|
| records | 22 | 2923 | 0 |
| tests | 13 | 1020 | 2 |
| algorithms | 4 | 109 | 1 |
| runtime | 2 | 59 | 3 |
| studio | 16 | 425 | 13 |
| tools | 2 | 74 | 1 |

记录文件占比较高，主要因为 provider-closed goal-mode 每个切片都保留了
handoff。对这个阈值分支可以接受，但下一条开发分支应减少 record-only 体积，
除非 contract、public API、部署或 provider 边界发生真实变化。

## Commit 分组

已审查的 19 个 commits 可归为五组:

1. 治理与阈值工具:
   `test(governance): add branch size merge review gate`。
2. Asset-card 复用与 fixed-asset promotion contract:
   可复用 asset candidates、human-gate reuse policy、promotion-gate reuse
   summary、fixed-asset source evidence。
3. Production graph 到 keyframe 的证据链:
   production-graph fixed-asset reuse、preflight source evidence summaries、
   Studio production graph evidence、keyframe trace alignment。
4. Studio review surfaces:
   human gate、promotion gate、inspector、output records、asset detail popover、
   asset library source-evidence preservation。
5. 非声明与安全标记:
   shared Studio `sourceEvidenceRefs()` 保留 `provider_calls_started` 与
   `human_creative_acceptance_claimed`，但不把它们声明为 provider smoke 或人工验收。

## 产品能力与 Contract 分类

真实产品能力:

- 操作者可以看到资产为什么可复用、fixed visual asset 来源是什么、production
  graph reuse 如何进入 keyframe context，以及 Studio review surface 附带了哪些证据。
- Studio 已形成更清晰的本地链路:
  `script/storyboard -> asset candidates -> reuse policy -> human gate -> fixed asset promotion -> production graph/evidence -> keyframe context`。

Deterministic contract / harness:

- Runtime 测试覆盖 asset-card candidate reuse、fixed-asset source evidence、
  production-graph reuse、promotion-gate contract。
- Studio static tests 覆盖 reuse policy visibility、keyframe evidence、
  production-graph trace、asset detail source evidence、non-claim flag preservation。
- Branch-size review tooling 固化 `20 commits / 80 files / 5000 insertions`
  阈值，避免长分支继续累积 review debt。

Review surface only:

- handoff、DEVLOG/TASK_TRACKER、branch review reports 是证据与治理记录，不是产品功能。

## 冗余审查

- 未新增重复 Runtime route 或 OpenAPI path。
- 未新增重复 provider gate、prompt policy 或 feedback promotion 概念。
- Studio evidence sanitizer 仍集中在共享 `sourceEvidenceRefs()` helper；
  `assetSourceEvidenceRows()` 只是展示 helper，不是第二个 contract boundary。
- 当前最大维护风险是记录体积，不是 Runtime 或 Studio 运行复杂度。
- 既有 oversized test/doc warnings 本轮不做无关重构，避免扩大风险面。

## Public API / Provider / Human Gate 审查

- OpenAPI/public API: 本分支未改变。
- Runtime routes: T39 未新增 route；分支内 Runtime 变化是 deterministic contract addition。
- Provider gates: 未改变；未调用 live LLM、image、video、ASR 或 external download provider。
- Prompt policy: source evidence 与 context overlay 类数据仍默认不进入 provider prompts。
- Human gate: review surfaces 有增强，但不声明 human creative acceptance。
- Feedback promotion: 未写 durable memory，未晋升 Company KB 规则。

## 验证

```text
.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

.\.venv\Scripts\python.exe -m pytest
# 770 passed, 520 deselected, 2 warnings

npm.cmd run check:studio-js
# JS syntax check passed: 134 files

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; existing warning classes only before this handoff

git diff --check
# passed

.\.venv\Scripts\python.exe tools\afs_goal_mode_branch_integration_review.py --repo-root . --base-ref origin/master --allowed-untracked docs/demo-docs-20260629/ --report runs\afs_goal_mode_branch_review_t39_precommit.json
# status=ready_for_human_merge_review; blocker_count=0
```

本轮未解决的既有 warning:

- `legacy_frozen_surface`
- `human_doc_chinese_coverage`
- `secret_like_fragments`, `high_confidence_count=0`
- `oversized_files`, 包括历史 tracked docs/tests 与 do-not-touch demo docs

## 建议

建议: `merge after human authorization`。

理由:

- 分支主题一致，所有产品改动都服务于 fixed-asset reuse 与 source-evidence chain。
- full pytest、Studio JS、maintenance audit、diff check、branch review gate 均无 blocker。
- 未出现 public API/OpenAPI drift、provider call、deploy、server sync、人类验收或商业验证声明。
- 本轮记录提交达到 commit 阈值，继续追加功能会制造不必要的 review debt。

本 gate 不授权 merge、push `master`、deploy、server sync 或 Runtime health。以上动作必须等人工明确授权。

## Evidence State

`structure_verified_goal_mode_threshold_merge_review_ready_no_merge_no_provider_no_sync`

## Next Valid Task

`AFS-T40 Authorized Merge Decision Gate`:

- 如果人工决策为 `merge`，再执行安全 merge/push、三端同步和 Runtime health 核验。
- 如果人工决策为 `split`，先拆分 records 与产品改动后再决定合并。
- 如果人工决策为 `defer`，停止本分支功能工作，并先记录 defer 原因。
