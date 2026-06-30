# AFS-T36 Studio Asset Detail Source Evidence Surface

## 任务信息

- Task ID: `AFS-T36`
- 分支: `codex/afs-goal-mode-threshold-gate-20260630`
- 起点 HEAD: `b8fbc4b4`
- 模式: provider-closed full goal-mode product slice
- 状态: 已实现并通过 focused 本地验证；commit/push 和 post-push branch preflight 待执行

T36 将 fixed visual asset 的 `source_evidence` 展示到 Studio asset detail
popover。此前 promotion 后的 `node.params.visualAssets` 已能保留 Runtime 返回的
`source_evidence`，keyframe layer 也会读取它；但操作员在查看固定资产详情时看不到
证据来源。本轮补上这个本地 review surface。

## Dirty Ownership Ledger

本轮拥有:

- `apps/studio/src/panels/asset-detail-popover.js`
- `tests/test_web_studio_asset_detail_source_evidence.py`
- `DEVLOG.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- `docs/handoff/AFS-STUDIO-ASSET-DETAIL-SOURCE-EVIDENCE-SURFACE-20260630.md`
- `D:\Learning materials\Learning_notes\10-Startup\70-Projects\AI-Native-Project-Books\2026-06-30-COS-AFS-autonomous-project-book\AFS-Goal-Driven-Execution-State-v0.1.yaml`

既有 do-not-touch:

- `docs/demo-docs-20260629/` 仍然保持未跟踪、未暂存。

## Contract 判断

T36 增强的是 Studio 本地展示:

```text
asset detail popover -> source evidence rows
```

白名单字段:

```text
source_human_gate_id
source_asset_card_candidate_id
source_stage
provider_calls_started
human_creative_acceptance_claimed
```

不展示 provider raw、signed URL、本地绝对路径、secret、素材字节或生成媒体字节。

## 本轮改动

- `asset-detail-popover.js` 新增 `assetSourceEvidenceRows()` 纯 helper。
- asset detail popover 在存在 source evidence 时显示 `来源证据` 区块。
- Focused tests 验证白名单字段和 unsafe 字段过滤边界。

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
.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_asset_detail_source_evidence.py tests\test_web_studio_keyframe_layer_source_evidence.py
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
# yaml_ok=True; current_task_id=AFS-T36

branch preflight after push
# pending post-push check
```

## Cleanup Review

- 没有新增 sanitizer 体系；使用本地白名单 helper。
- 没有新增 Runtime/public API surface。
- 新测试独立成小文件，避免继续放大既有超长测试。
- 没有触碰历史不明文件或 `docs/demo-docs-20260629/`。

## 下一步

T36 commit/push 和 branch preflight 通过后，如果分支仍低于阈值，可以继续
provider-closed 切片。下一步最有效方向是把 keyframe context / asset detail /
generation preflight 的证据摘要继续统一到同一组安全显示字段。
