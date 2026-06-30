# AFS-T38 Studio Source Evidence Non-Claim Flags

## 任务信息

- Task ID: `AFS-T38`
- 分支: `codex/afs-goal-mode-threshold-gate-20260630`
- 起点 HEAD: `f86c45a0`
- 模式: provider-closed full goal-mode product slice
- 状态: 已实现并通过 focused 本地验证；commit/push 和 post-push branch preflight 待执行

T38 统一 Studio source evidence 的安全字段。T36/T37 已让 asset detail 和 asset
library 能看到 fixed visual asset `source_evidence`；本轮把同一证据中的两个非声明布尔值
也纳入共享 `sourceEvidenceRefs()` normalizer，让 preflight、keyframe layer、trace 和
asset detail 使用一致的 evidence 表达。

## Dirty Ownership Ledger

本轮拥有:

- `apps/studio/src/generation-preflight-source-evidence.js`
- `tests/test_web_studio_keyframe_layer_source_evidence.py`
- `tests/test_web_studio_source_evidence_claim_flags.py`
- `DEVLOG.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- `docs/handoff/AFS-STUDIO-SOURCE-EVIDENCE-NON-CLAIM-FLAGS-20260630.md`
- `D:\Learning materials\Learning_notes\10-Startup\70-Projects\AI-Native-Project-Books\2026-06-30-COS-AFS-autonomous-project-book\AFS-Goal-Driven-Execution-State-v0.1.yaml`

既有 do-not-touch:

- `docs/demo-docs-20260629/` 仍然保持未跟踪、未暂存。

## Contract 判断

T38 增强的是 Studio 本地 safe evidence projection:

```text
sourceEvidenceRefs(...)
```

新增保留字段:

```text
provider_calls_started
human_creative_acceptance_claimed
```

这两个字段是布尔型非声明证据，只说明 provider 是否已启动、是否已声明人类创意验收。
它们不打开 provider gate，不构成 human acceptance 或 business validation。

## 本轮改动

- `generation-preflight-source-evidence.js` 在 fallback asset evidence 和 explicit refs 两条入口中保留两个布尔字段。
- keyframe layer focused test 更新，确认固定资产 source evidence 会把两个字段带入 `fixed_asset_source_evidence_refs`。
- 新增 focused test 验证 unsafe 字段不会进入 normalized refs。

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
.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_source_evidence_claim_flags.py tests\test_web_studio_keyframe_layer_source_evidence.py tests\test_web_studio_asset_detail_source_evidence.py
# 9 passed

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
# yaml_ok=True; current_task_id=AFS-T38

branch preflight after push
# pending post-push check
```

## Cleanup Review

- 没有新增 sanitizer；扩展现有 `sourceEvidenceRefs()` 白名单。
- 没有新增 Runtime/public API surface。
- 新测试独立成小文件，避免继续放大既有 keyframe 测试文件。
- 没有触碰历史不明文件或 `docs/demo-docs-20260629/`。

## 下一步

T38 commit/push 和 branch preflight 通过后，分支预计会到 19 commits，接近
`20 commits` 阈值。下一步应先看 branch preflight；若再做一个 commit 会达到阈值，
优先进入 merge review gate，而不是继续追加功能。
