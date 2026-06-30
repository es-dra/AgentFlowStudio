# AFS-T21 资产复用候选策略

## 任务信息

- Task ID：`AFS-T21`
- 分支：`codex/afs-goal-mode-threshold-gate-20260630`
- 起点：`1b3a943408d1332ba464edf64b3b844724fa7a87`
- 模式：provider-closed full goal-mode product slice
- 目标：让 storyboard 产出的 asset-card candidates 明确区分跨镜头复用候选和单镜头局部候选，为后续 human gate 与 fixed asset promotion 提供稳定字段。

## Dirty Ownership Ledger

本轮拥有：

- `agentflow/algorithms/asset_card_candidates/__init__.py`
- `apps/api/runtime_storyboard_breakdown.py`
- `tests/test_api_runtime_asset_card_candidates_contract.py`
- `DEVLOG.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- `docs/handoff/AFS-ASSET-REUSE-CANDIDATE-POLICY-20260630.md`
- `D:\Learning materials\Learning_notes\10-Startup\70-Projects\AI-Native-Project-Books\2026-06-30-COS-AFS-autonomous-project-book\AFS-Goal-Driven-Execution-State-v0.1.yaml`

既有 do-not-touch：

- `docs/demo-docs-20260629/`

## Contract

`asset_card_candidates` 现在对每个候选资产输出：

- `reuse_policy.suggested_reuse_scope`
  - `project_reuse_candidate`：资产出现在两个或更多 storyboard shots 中。
  - `shot_local_candidate`：当前只有单镜头证据。
- `reuse_policy.reason`
- `reuse_policy.shot_ref_count`
- `reuse_policy.requires_human_confirmation=true`
- `reuse_policy.writes_fixed_asset=false`
- `reuse_policy.promotion_blocked_by_default=true`

候选集 summary 增加：

- `reuse_scope_counts.project_reuse_candidate`
- `reuse_scope_counts.shot_local_candidate`

Storyboard safe manifest 增加：

- `asset_card_project_reuse_candidate_count`

## 边界

本轮只从现有 `asset_graph.shot_refs` 派生复用建议，不创建 fixed visual asset，不写长期记忆，不晋升 Company KB，不触发 provider，不存 provider raw、本地绝对路径、signed URL 或媒体字节。

## 验证

已完成 focused 验证：

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_asset_card_candidates_contract.py -q
# 2 passed, 1 existing warning

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_asset_card_candidates_contract.py tests\test_api_runtime_storyboard_evidence_ledger.py tests\test_api_runtime_production_graph_contract.py tests\test_api_runtime_storyboard_content_quality.py tests\test_api_runtime_storyboard_breakdown.py -q
# 24 passed, 1 existing warning

.\.venv\Scripts\python.exe -m pytest
# 752 passed, 520 deselected, 2 existing warnings

npm.cmd run check:studio-js
# JS syntax check passed: 132 files

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; existing warnings unchanged:
# legacy_frozen_surface=10
# human_doc_chinese_coverage=22
# secret_like_fragments=9
# oversized_files=59

git diff --check
# passed

YAML parse check for external execution state
# yaml_ok=True; current_task_id=AFS-T21
```

提交推送后的 branch preflight 需要在工作树干净且远端对齐后执行。

## Cleanup Review

- 没有新增临时 route、schema fork、provider path、一次性工具或重复 sanitizer。
- 新增字段挂在既有候选合同下，来源是已有 asset graph 证据。
- 修改文件均低于 300 行；未新增超长测试文件。

## 下一步

下一批最有效切片是让 Studio 对 `project_reuse_candidate` 的资产卡候选显示更明确的“建议确认/可复用”状态，或让 human gate decision 更好地携带复用策略摘要。仍需保持 provider-closed。
