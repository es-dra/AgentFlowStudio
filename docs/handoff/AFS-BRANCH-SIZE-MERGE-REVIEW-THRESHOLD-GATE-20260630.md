# AFS-T20 分支规模 Merge Review 阈值 Gate

## 任务信息

- Task ID：`AFS-T20`
- 日期：2026-06-30
- 分支：`codex/afs-goal-mode-threshold-gate-20260630`
- 基线：`master` / `origin/master` 的 `f51237df89c680dafc54296d7e013bd98cd459af`
- 状态：治理自动化实现与本地确定性验证切片

## Dirty Ownership Ledger

本轮拥有并允许修改：

- `tools/afs_branch_size_thresholds.py`
- `tools/afs_goal_mode_branch_integration_review.py`
- `tests/test_afs_goal_mode_branch_integration_review.py`
- `DEVLOG.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- `docs/handoff/AFS-BRANCH-SIZE-MERGE-REVIEW-THRESHOLD-GATE-20260630.md`
- `D:\Learning materials\Learning_notes\10-Startup\70-Projects\AI-Native-Project-Books\2026-06-30-COS-AFS-autonomous-project-book\AFS-Goal-Driven-Execution-State-v0.1.yaml`

既有 do-not-touch 边界：

- `docs/demo-docs-20260629/`

## Contract 判断

T19 已经把膨胀分支合入并同步到 `master`。后续新的目标模式分支不能继续无限追加功能，必须在达到任一规模阈值时自动进入 merge review gate：

- 距离 `origin/master` 达到 `20` 个 commits
- 距离 `origin/master` 达到 `80` 个 changed files
- 距离 `origin/master` 达到 `5000` 行 insertions

`tools/afs_goal_mode_branch_integration_review.py` 的 JSON 报告现在包含：

- `insertion_count_since_base`
- `deletion_count_since_base`
- `binary_file_count_since_base`
- `merge_review_thresholds.threshold_reached`
- `merge_review_thresholds.reached`
- `merge_review_thresholds.required_action`

这个 gate 只属于仓库治理和发布节奏控制。它不是产品能力、不是 Runtime 验证、不是 provider smoke、不是服务器同步、不是部署、不是人工验收、不是商业验证，也不是 durable memory promotion。

## 本轮改动

- 新增 `tools/afs_branch_size_thresholds.py`，集中放置阈值常量、阈值判断和基于 `git diff --numstat` 的插入/删除行统计。
- 扩展 `tools/afs_goal_mode_branch_integration_review.py`，让 preflight 报告输出分支规模和阈值状态，同时保持既有 blocker 行为不变。
- 新增阈值测试：一个覆盖低于阈值的普通切片，一个覆盖刚好命中 20 commits、80 files、5000 insertions 的 merge review 触发条件。
- 为避免新增维护债，主 preflight 脚本保持在 300 行以下，阈值策略拆入小 helper。

## 验证结果

提交前本地确定性验证：

```text
.\.venv\Scripts\python.exe -m pytest tests\test_afs_goal_mode_branch_integration_review.py -q
# 7 passed

npm.cmd run check:studio-js
# JS syntax check passed: 132 files

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; existing warnings unchanged
# legacy_frozen_surface=10
# human_doc_chinese_coverage=22
# secret_like_fragments=9
# oversized_files=59

git diff --check
# passed

YAML parse check for the external execution state
# yaml_ok=True; current_task_id=AFS-T20
```

分支 preflight 的最终 ready 结果必须在 commit/push 之后再跑，因为该 preflight 会正确阻塞 dirty 或未推送的分支状态。

## Provider Gate

本轮没有打开 provider gate，没有发起 live LLM、image、video、ASR、vision 或 external-download provider 调用。

## Cleanup Review

- 旧的膨胀分支只在 T19 已完成 fast-forward merge、push 和 master 同步后才删除本地与远端分支。
- 本 T20 切片没有执行 `git reset`、force push、workspace clean、deploy、server sync 或 provider smoke。
- 新 helper 有 focused tests，并被 branch preflight 直接使用，不是一次性 report 脚本。

## 下一步

继续在新的 `codex/*` 分支上做 provider-closed 目标模式切片。只要分支 preflight 报告任一阈值命中，就停止新增功能并再次进入 merge review gate。
