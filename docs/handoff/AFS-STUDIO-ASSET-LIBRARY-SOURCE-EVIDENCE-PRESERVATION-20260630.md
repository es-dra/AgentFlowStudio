# AFS-T37 Studio Asset Library Source Evidence Preservation

## 任务信息

- Task ID: `AFS-T37`
- 分支: `codex/afs-goal-mode-threshold-gate-20260630`
- 起点 HEAD: `ddbf53d5`
- 模式: provider-closed full goal-mode product slice
- 状态: 已实现并通过 focused 本地验证；commit/push 和 post-push branch preflight 待执行

T36 已经让 asset detail popover 可以显示 fixed visual asset 的
`source_evidence`。T37 补齐同一链路中的保存点：当 fixed visual asset promotion
成功后，Studio 不仅把 Runtime 返回的 asset 放入 `node.params.visualAssets`，也把
同一份 `source_evidence` 保留到 `s.assets` 资产库条目。这样从节点或资产库打开详情
都能看到一致证据。

## Dirty Ownership Ledger

本轮拥有:

- `apps/studio/src/panels/visual-asset-panel.js`
- `tests/test_web_studio_asset_detail_source_evidence.py`
- `DEVLOG.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- `docs/handoff/AFS-STUDIO-ASSET-LIBRARY-SOURCE-EVIDENCE-PRESERVATION-20260630.md`
- `D:\Learning materials\Learning_notes\10-Startup\70-Projects\AI-Native-Project-Books\2026-06-30-COS-AFS-autonomous-project-book\AFS-Goal-Driven-Execution-State-v0.1.yaml`

既有 do-not-touch:

- `docs/demo-docs-20260629/` 仍然保持未跟踪、未暂存。

## Contract 判断

本轮只保存 Runtime 已返回、Studio 已接收的 safe asset projection:

```text
s.assets[].source_evidence = localAsset.source_evidence || null
```

不新增 Runtime 字段或 request schema。source evidence 本身仍由 Runtime fixed visual
asset contract 提供，并由 T36 的 display helper 白名单展示。

## 本轮改动

- `visual-asset-panel.js` 在创建 Studio asset library entry 时保留
  `source_evidence`。
- Focused test 确认 promotion flow 不再丢失 asset library entry 的
  `source_evidence`。

## 非目标和边界

- 不新增 Runtime route。
- 不更新 request schema 或 OpenAPI。
- 不调用 live provider。
- 不改变 provider prompt inclusion policy。
- 不生成、读取或保存媒体字节。
- 不 deploy、不 server sync、不做 Runtime health check。
- 不声明 human creative acceptance、business validation 或 durable memory promotion。

## 验证

Focused verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_asset_detail_source_evidence.py tests\test_web_studio_visual_asset_promotion_gate_static.py
# 6 passed

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
# yaml_ok=True; current_task_id=AFS-T37

branch preflight after push
# pending post-push check
```

## Cleanup Review

- 没有新增 sanitizer 或重复 helper。
- 没有新增 Runtime/public API surface。
- 只保存已存在的 safe projection 字段，避免 node detail 与 asset library detail 漂移。
- 没有触碰历史不明文件或 `docs/demo-docs-20260629/`。

## 下一步

T37 commit/push 和 branch preflight 通过后，如果分支仍低于阈值，可以继续
provider-closed 切片；如果接近 `20 commits` 或 `5000 insertions`，下一步应优先做
merge review gate。
