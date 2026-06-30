# AFS-T35 Studio Promotion Gate Production Graph Evidence

## 任务信息

- Task ID: `AFS-T35`
- 分支: `codex/afs-goal-mode-threshold-gate-20260630`
- 起点 HEAD: `468aab38`
- 模式: provider-closed full goal-mode product slice
- 状态: 已实现并通过 focused 本地验证；commit/push 和 post-push branch preflight 待执行

本轮补齐 Studio operator evidence chain 中的一个缺口：human gate 已经能看到
production graph fixed reuse count，但 fixed visual asset promotion review
summary 只能看到 count，不能回到对应的 production graph snapshot artifact。T35 将
安全的 `production_graph_artifact_id` 写入 human-gate review note，并在 promotion
review summary 中显示。

## Dirty Ownership Ledger

本轮拥有:

- `apps/studio/src/human-gate.js`
- `apps/studio/src/human-gate-provenance.js`
- `apps/studio/src/panels/visual-asset-panel-render.js`
- `tests/test_web_studio_production_graph_reuse_static.py`
- `tests/test_web_studio_visual_asset_promotion_gate_static.py`
- `DEVLOG.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- `docs/handoff/AFS-STUDIO-PROMOTION-GATE-PRODUCTION-GRAPH-EVIDENCE-20260630.md`
- `D:\Learning materials\Learning_notes\10-Startup\70-Projects\AI-Native-Project-Books\2026-06-30-COS-AFS-autonomous-project-book\AFS-Goal-Driven-Execution-State-v0.1.yaml`

既有 do-not-touch:

- `docs/demo-docs-20260629/` 仍然保持未跟踪、未暂存。

## Contract 判断

T35 增强的是 Studio 本地 review note 和 display summary:

```text
humanGateTargets(...)[].note
promotionGateReviewSummary(node).production_graph_artifact_id
visual asset promotion panel meta text
```

新增字段只来自 `storyboardBreakdown.productionGraphArtifactId`，并经过
`safeToken()` 白名单处理。它不是 Runtime promotion payload 的新增字段，也不是
新的 Runtime route、request schema 或 OpenAPI contract。

## 本轮改动

- `human-gate.js` 将 `production_graph_artifact_id=<artifact>` 追加到 asset-card
  human-gate review note。
- `human-gate-provenance.js` 从 note 中解析安全 artifact id，并放入 promotion
  review summary。
- `visual-asset-panel-render.js` 在 promotion gate meta line 显示
  `production_graph=<artifact>`。
- Focused tests 覆盖 human gate note、promotion review summary 和面板 meta 的
  新字段。

## 非目标和边界

- 不新增 Runtime route。
- 不更新 Runtime promotion payload 字段。
- 不更新 request schema 或 OpenAPI。
- 不调用 live provider。
- 不生成、读取或保存媒体字节。
- 不 deploy、不 server sync、不做 Runtime health check。
- 不声明 human creative acceptance、business validation 或 durable memory promotion。

## 验证

Focused verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_production_graph_reuse_static.py tests\test_web_studio_visual_asset_promotion_gate_static.py tests\test_web_studio_human_gate_static.py
# 7 passed

npm.cmd run check:studio-js
# JS syntax check passed: 134 files
```

Closeout verification:

```text
.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; existing warning classes only

git diff --check
# passed

YAML parse check for external execution state
# yaml_ok=True; current_task_id=AFS-T35

branch preflight after push
# pending post-push check
```

## Cleanup Review

- 没有新增 sanitizer；继续复用 `safeToken()`。
- 没有新增 Runtime/public API surface。
- 没有把 graph artifact id 写入 promotion Runtime payload。
- 没有触碰历史不明文件或 `docs/demo-docs-20260629/`。

## 下一步

T35 commit/push 和 branch preflight 通过后，如果分支仍低于阈值，可以继续
provider-closed 切片。下一步最有效方向是把 fixed visual asset promotion 后的
source evidence 与 keyframe context review 继续对齐，但仍不打开 provider gate。
