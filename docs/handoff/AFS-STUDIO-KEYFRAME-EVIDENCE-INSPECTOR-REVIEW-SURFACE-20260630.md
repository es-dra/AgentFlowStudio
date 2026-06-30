# AFS-T31 Studio Keyframe Evidence Inspector Review Surface

## 任务信息

- Task ID: `AFS-T31`
- 分支: `codex/afs-goal-mode-threshold-gate-20260630`
- 起点 HEAD: `f05cd11f`
- 模式: provider-closed full goal-mode product slice
- 记录时状态: 已实现并通过本地 closeout 验证；commit/push 与 post-push branch preflight 待执行

本轮把 T30 写入 keyframe layer 的固定资产来源证据接到 Studio 右侧 inspector 的
`本次参考摘要`，让操作员不用打开开发者工具也能看到关键帧节点来自哪个固定资产、
human gate 或 asset-card candidate。

## Dirty Ownership Ledger

本轮拥有:

- `apps/studio/src/panels/inspector-context-summary.js`
- `apps/studio/src/panels/inspector-panel.js`
- `tests/test_web_studio_keyframe_layer_source_evidence.py`
- `DEVLOG.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- `docs/handoff/AFS-STUDIO-KEYFRAME-EVIDENCE-INSPECTOR-REVIEW-SURFACE-20260630.md`
- `D:\Learning materials\Learning_notes\10-Startup\70-Projects\AI-Native-Project-Books\2026-06-30-COS-AFS-autonomous-project-book\AFS-Goal-Driven-Execution-State-v0.1.yaml`

既有 do-not-touch:

- `docs/demo-docs-20260629/` 仍然保持未跟踪、未暂存。

## Contract 判断

Studio inspector 现在会读取:

```text
node.params.keyframeLayer.fixed_asset_source_evidence_refs
```

并在节点 `本次参考摘要` 中显示安全摘要:

```text
关键帧来源证据：角色 Lin Wan -> asset_card_candidate:main_character
```

该摘要只消费 T30 已经归一化的安全 refs，不读取 provider raw、签名 URL、本地路径、
媒体字节或 secret。它不改变 Runtime API，不改变 provider prompt inclusion policy，
也不把来源证据正文注入生成 prompt。

## 本轮改动

- `nodeContextSummaryText()` 增加 keyframe layer source evidence 摘要。
- `inspectorSignature()` 纳入 `keyframeLayer`，确保关键帧来源证据变化后 inspector 会刷新。
- 扩展 T30 的 executable Node 回归，验证 inspector summary 会显示 keyframe 来源证据。

## 非目标和边界

- 不新增 Runtime route。
- 不更新 request schema 或 OpenAPI。
- 不改变 provider prompt inclusion policy。
- 不调用 live provider。
- 不生成或保存媒体字节。
- 不 deploy、不 server sync、不做 Runtime health check。
- 不声明 human creative acceptance、business validation 或 durable memory promotion。

## 验证

已执行 focused verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_keyframe_layer_source_evidence.py
# 2 passed

.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_mature_shell_static.py::test_studio_mature_shell_exposes_algorithm_console_and_quick_start_rail tests\test_web_studio_feedback_candidate_static.py::test_studio_feedback_overlay_review_surface_reads_context_bundle_only tests\test_web_studio_feedback_candidate_static.py::test_studio_feedback_overlay_prompt_policy_review_surface_is_local
# 3 passed

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
# yaml_ok=True; current_task_id=AFS-T31

branch preflight after push
# pending post-push check
```

## Cleanup Review

- 没有新增 UI 面板；复用 inspector 的既有 `本次参考摘要`。
- 没有新增 sanitizer；只消费 T30 已经安全归一化的 refs。
- 没有新增一次性工具。
- 触达的 Studio JS 文件仍低于 300 行。
- `docs/demo-docs-20260629/` 未清理、未暂存、未纳入本轮成果。

## 下一步

T31 commit/push 和 branch preflight 通过后，如果分支仍低于阈值，可以继续
provider-closed 切片。下一步最有效方向是把 keyframe evidence 接到本地 generation
trace 或 production graph review，但仍不要改变 provider prompt inclusion policy。
