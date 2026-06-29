# AFS 第十一波 TaskRun - Context Resolver 候选/确认边界 - 2026-06-30

## 任务

Task ID：`AFS-T6 Context Resolver`

当前分支：`codex/afs-project-book-full-goal-20260630`

启动基线：`a2016bc4bfeb0a2fb696cba32434df12e008e852`

本轮目标是在第十波 `asset_card_candidates` 合同之后，验证并收窄 Context Resolver 对未确认资产卡候选的处理边界。
未确认 candidate 可以被 Runtime 记录和展示，但不能作为固定资产进入生成上下文、reference image channel 或 subject reference。

## 脏改账本

| 表面 | 归属 | 处理 |
|---|---|---|
| `agentflow/algorithms/context_resolver/assets.py` | 本轮合同修正 | 保留，将 `asset_card_candidate:*` 和 `asset_card:*` 的排除理由明确为未确认候选。 |
| `apps/api/runtime_context_assets.py` | 本轮镜像 helper 对齐 | 保留，避免 apps/api 侧旧 helper 与算法库 helper 漂移。 |
| `tests/test_api_runtime_context_resolver_asset_card_candidates.py` | 本轮 focused regression | 保留，覆盖 storyboard candidate 到 keyframe preflight 的边界。 |
| `DEVLOG.md`、`TASK_TRACKER.md`、`docs/handoff/INDEX.md` | 本轮项目记录 | 保留。 |
| 私有 execution state YAML | 本轮状态记录 | 只更新当前任务和验证结果，不处理 Learning_notes 其他脏状态。 |
| `docs/demo-docs-20260629/` | 既有未跟踪本地文档 | defer/do-not-touch，不读取为本轮成果，不清理。 |

## 合同判断

Context Resolver 当前只信任 Runtime fixed visual asset store。客户端传入的 draft/candidate id 不应被当成事实资产。

本轮把原本泛化的 `retired_or_missing_visual_asset` 排除理由收窄：

- `asset_card_candidate:*` -> `asset_card_candidate_unconfirmed`
- `asset_card:*` -> `asset_card_candidate_unconfirmed`
- 其他缺失或退休资产仍保持 `retired_or_missing_visual_asset`

这个改动不让候选资产进入上下文，只让 preflight 的排除原因更可治理。

## 本轮改动

- 新增 `tests/test_api_runtime_context_resolver_asset_card_candidates.py`。
- 测试先通过 storyboard breakdown 产生真实 `asset_card_candidates`。
- 再把 candidate id 作为 upstream `visual_asset_ids` 传入 keyframe preflight。
- 断言：
  - `included_assets=[]`
  - `reference_image_channel=[]`
  - `subject_reference_asset_id=None`
  - excluded reason 为 `asset_card_candidate_unconfirmed`
  - `trace_summary.draft_assets_rejected=true`

实现层只新增 `_missing_asset_reason(...)` helper，并同步到算法库和 apps/api 镜像文件。

## 验证

红线复现：

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_context_resolver_asset_card_candidates.py -q
# 预期失败：candidate 已被排除，但 reason 仍为 retired_or_missing_visual_asset
```

focused green：

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_context_resolver_asset_card_candidates.py -q
# 1 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_context_resolver.py -q
# 18 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_asset_card_candidates_contract.py tests\test_api_runtime_production_graph_contract.py -q
# 4 passed, 1 existing Starlette/httpx deprecation warning
```

全量 closeout：

```text
.\.venv\Scripts\python.exe -m pytest
# 697 passed, 520 deselected, 2 warnings

.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

npm.cmd run check:studio-js
# JS syntax check passed: 125 files

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; passed=3; warning=4
# warnings remain existing categories: legacy_frozen_surface, human_doc_chinese_coverage,
# secret_like_fragments, oversized_files

git diff --check
# passed

YAML parse check for AFS-Goal-Driven-Execution-State-v0.1.yaml
# yaml_parse_ok; current_task_id=AFS-T6
```

## 证据状态

当前证据状态：

```text
structure_verified_context_resolver_candidate_boundary
```

这不是 provider smoke，不是 human acceptance，不是 fixed asset promotion，不是 business validation，不是部署验证，也不是服务器三端同步。

## Cleanup Review

| 对象 | 分类 | 决定 |
|---|---|---|
| focused boundary test | keep | 覆盖新 T5 候选合同到 T6 上下文解析边界。 |
| `_missing_asset_reason` helper | keep | 将排除理由从泛化缺失收窄为未确认候选。 |
| apps/api 镜像 helper | keep | 与算法库保持一致，避免后续入口漂移。 |
| fixed visual asset selection | unchanged | 本轮不改变 confirmed/fixed 资产选择逻辑。 |
| Studio UI | unchanged | 本轮只收窄 Runtime/preflight 合同。 |
| `docs/demo-docs-20260629/` | defer/do-not-touch | 既有未跟踪本地文档，不清理。 |

未新增生成媒体、provider raw、signed URL、secret、客户材料或真实成本。

## 下一步

推荐下一任务：

```text
AFS-T9 Evidence Ledger for Storyboard-to-Asset Artifacts
```

目标是把 storyboard、asset graph、production graph、asset card candidates 与后续 keyframe/video artifacts 的 safe evidence ledger 衔接起来。
