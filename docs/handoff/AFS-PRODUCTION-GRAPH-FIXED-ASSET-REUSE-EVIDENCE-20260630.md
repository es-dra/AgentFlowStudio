# AFS-T25 Production Graph Fixed Asset Reuse Evidence

## 任务信息

- Task ID: `AFS-T25`
- 分支: `codex/afs-goal-mode-threshold-gate-20260630`
- 起点: `0f26bf06c4ed69a44ff5ba655feaea3150a65af0`
- 模式: provider-closed full goal-mode product slice
- 目标: 让 storyboard production graph 消费当前项目已有 fixed visual assets 的安全来源证据，把固定资产复用显式放入 production graph。

## Dirty Ownership Ledger

本轮拥有:

- `agentflow/algorithms/production_graph/__init__.py`
- `apps/api/runtime_storyboard_breakdown.py`
- `tests/test_api_runtime_production_graph_contract.py`
- `DEVLOG.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- `docs/handoff/AFS-PRODUCTION-GRAPH-FIXED-ASSET-REUSE-EVIDENCE-20260630.md`
- `D:\Learning materials\Learning_notes\10-Startup\70-Projects\AI-Native-Project-Books\2026-06-30-COS-AFS-autonomous-project-book\AFS-Goal-Driven-Execution-State-v0.1.yaml`

既有 do-not-touch:

- `docs/demo-docs-20260629/`

## Contract

Storyboard production graph 现在会接收当前项目 fixed visual assets 的 public projection，并新增:

- `fixed_visual_asset` graph nodes
- `script_can_reuse_fixed_asset` relationships
- `summary.fixed_visual_asset_count`
- `safe_manifest.fixed_visual_asset_source_evidence_count`

Fixed asset node 只携带 safe public fields:

- `asset_id`
- `asset_type`
- `label`
- `status`
- `source_node_id`
- `review_state=fixed_asset_available_for_reuse`
- `source_evidence`
- `writes_long_term_memory=false`

## 本轮改动

- `build_storyboard_production_graph()` 增加 optional `fixed_visual_assets` 输入。
- Runtime storyboard route 从当前项目 visual asset store 读取 fixed assets，转成 public projection 后传入 graph builder。
- 新增 graph node/relationship helper，避免把 fixed asset 逻辑混入 route 层。
- 扩展 production graph contract test，覆盖 fixed asset source evidence、safe manifest count 和 unsafe marker 排除。

## 非目标和边界

- 不新增 Runtime route。
- 不新增 request 字段。
- 不修改 OpenAPI request contract。
- 不调用 live provider。
- 不生成或保存媒体字节。
- 不写 provider raw、本地绝对路径、signed URL、secret。
- 不声明 human creative acceptance 或 business validation。
- 不做 deploy、server sync 或 provider smoke。

## 验证

已完成 focused 验证:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_production_graph_contract.py -q
# 3 passed, 1 existing warning

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_production_graph_contract.py tests\test_api_runtime_storyboard_evidence_ledger.py tests\test_api_runtime_asset_card_candidates_contract.py tests\test_api_runtime_fixed_asset_source_evidence_context.py -q
# 8 passed, 1 existing warning
```

已完成收口验证:

```text
.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; existing warnings unchanged:
# legacy_frozen_surface=10
# human_doc_chinese_coverage=22
# secret_like_fragments=9
# oversized_files=59

git diff --check
# passed

YAML parse check for external execution state
# yaml_ok=True; current_task_id=AFS-T25

branch preflight after push
# pending post-push check
```

## Cleanup Review

- 未新增 route、schema fork、provider path、一次性工具或重复 sanitizer。
- 新 helper 保持在 production graph module 内，route 只负责传入 public fixed assets。
- 触达代码和测试文件均低于 300 行。
- `docs/demo-docs-20260629/` 未清理、未归入本轮成果。

## 下一步

下一批最有效切片: 在 Studio 里把 production graph 的 fixed asset reuse evidence 更清楚地展示给操作者，或把 source evidence 摘要带入 keyframe preflight review surface。达到 20 commits、80 files 或 5000 insertions 任一阈值时必须停止新增功能并进入 merge review gate。
