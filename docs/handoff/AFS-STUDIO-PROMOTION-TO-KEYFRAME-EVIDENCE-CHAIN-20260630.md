# AFS-T30 Studio Promotion-to-Keyframe Evidence Chain

## 任务信息

- Task ID: `AFS-T30`
- 分支: `codex/afs-goal-mode-threshold-gate-20260630`
- 起点 HEAD: `3cae6b88`
- 模式: provider-closed full goal-mode product slice
- 记录时状态: 已实现并通过本地 closeout 验证；commit/push 与 post-push branch preflight 待执行

本轮目标是把固定视觉资产的 promotion/source evidence 带到 Studio 关键帧层，
补齐本地 Studio 链路:

```text
asset card candidate -> human gate -> fixed visual asset -> keyframe layer
```

这只是安全证据链，不是 provider prompt 扩展，不是生成质量验收，也不是人工创意验收。

## Dirty Ownership Ledger

本轮拥有:

- `apps/studio/src/storyboard-keyframes.js`
- `tests/test_web_studio_keyframe_layer_source_evidence.py`
- `DEVLOG.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- `docs/handoff/AFS-STUDIO-PROMOTION-TO-KEYFRAME-EVIDENCE-CHAIN-20260630.md`
- `D:\Learning materials\Learning_notes\10-Startup\70-Projects\AI-Native-Project-Books\2026-06-30-COS-AFS-autonomous-project-book\AFS-Goal-Driven-Execution-State-v0.1.yaml`

既有 do-not-touch:

- `docs/demo-docs-20260629/` 仍然保持未跟踪、未暂存，本轮不清理。

## Contract 判断

当 Studio 从 storyboard 创建或刷新关键帧节点时，`keyframeLayer` 现在会记录固定视觉资产的
安全来源证据引用:

```text
keyframeLayer.fixed_asset_source_evidence_count
keyframeLayer.fixed_asset_source_evidence_refs
```

每个 ref 由既有 `sourceEvidenceRefs()` 安全归一化函数产生，只保留边界内字段:

- `asset_id`
- `asset_type`
- `label`
- `status`
- `source_human_gate_id`
- `source_asset_card_candidate_id`
- `source_stage`

这些字段用于 Studio 本地审计和后续 review surface。关键帧 prompt 不注入来源证据正文，
也不保留 provider 原始响应、签名 URL、本地绝对路径、媒体字节或 secret。

## 本轮改动

- 在 `storyboard-keyframes.js` 复用 `generation-preflight-source-evidence.js`
  里的 `sourceEvidenceRefs()`，避免新增重复 sanitizer。
- 在既有 `keyframeLayer` 上新增:
  - `fixed_asset_source_evidence_count`
  - `fixed_asset_source_evidence_refs`
- 新增一个可执行 Node 回归测试，构造 storyboard -> fixed asset card -> keyframe，
  并确认带有不安全字段的固定资产只会投影为安全 evidence refs。

## 非目标和边界

- 不新增 Runtime route。
- 不更新 request schema 或 OpenAPI。
- 不改变 provider prompt inclusion policy。
- 不调用 live LLM/image/video/ASR provider。
- 不生成或保存媒体字节。
- 不 deploy、不 server sync、不做 Runtime health check。
- 不声明 human creative acceptance、business validation 或 durable memory promotion。

## 验证

已执行 focused verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_keyframe_layer_source_evidence.py
# 1 passed

.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_assets_generation_static.py::test_keyframe_prompt_uses_editable_candidate_asset_plan_details tests\test_web_studio_preflight_source_evidence_static.py
# 2 passed

npm.cmd run check:studio-js
# JS syntax check passed: 133 files
```

Closeout verification:

```text
.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; existing warning classes only

git diff --check
# passed

YAML parse check for external execution state
# yaml_ok=True; current_task_id=AFS-T30

branch preflight after push
# pending post-push check
```

## Cleanup Review

- 没有新增重复 sanitizer；本轮复用既有 `sourceEvidenceRefs()`。
- 没有新增一次性工具。
- 没有新增 Runtime/public API surface。
- 新测试放入独立小文件，没有继续加重既有超长 Studio static test。
- `docs/demo-docs-20260629/` 未清理、未暂存、未纳入本轮成果。

## 下一步

在 T30 commit/push 和 branch preflight 通过后，如果分支仍低于
20 commits / 80 changed files / 5000 insertions 阈值，可以继续 provider-closed 切片。
最有效的下一步是把 keyframe-layer source evidence 接到操作员 review surface 或本地
generation trace，但仍不改变 provider prompt inclusion policy。
