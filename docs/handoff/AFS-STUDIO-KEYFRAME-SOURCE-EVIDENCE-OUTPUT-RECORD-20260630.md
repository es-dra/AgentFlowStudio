# AFS-T33 Studio Keyframe Source Evidence Output Record

## 任务信息

- Task ID: `AFS-T33`
- 分支: `codex/afs-goal-mode-threshold-gate-20260630`
- 起点 HEAD: `3607818d`
- 模式: provider-closed full goal-mode product slice
- 记录时状态: 已实现并通过本地 closeout 验证；commit/push 与 post-push branch preflight 待执行

本轮把 T32 写入节点的 `lastKeyframeSourceEvidenceTrace` 接到 Studio inspector 的
`输出记录` 摘要。这样关键帧节点不仅在 `本次参考摘要` 能看到来源证据，也能在生成记录里看到
本地 trace 的摘要和提示词策略。

## Dirty Ownership Ledger

本轮拥有:

- `apps/studio/src/keyframe-source-evidence-trace.js`
- `apps/studio/src/panels/inspector-panel.js`
- `tests/test_web_studio_keyframe_layer_source_evidence.py`
- `DEVLOG.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- `docs/handoff/AFS-STUDIO-KEYFRAME-SOURCE-EVIDENCE-OUTPUT-RECORD-20260630.md`
- `D:\Learning materials\Learning_notes\10-Startup\70-Projects\AI-Native-Project-Books\2026-06-30-COS-AFS-autonomous-project-book\AFS-Goal-Driven-Execution-State-v0.1.yaml`

既有 do-not-touch:

- `docs/demo-docs-20260629/` 仍然保持未跟踪、未暂存。

## Contract 判断

Studio `输出记录` 现在会读取:

```text
node.params.lastKeyframeSourceEvidenceTrace
```

并显示安全摘要:

```text
关键帧来源证据：1 项；角色 Lin Wan -> asset_card_candidate:main_character；提示词策略：excluded_by_default
```

该摘要只显示 T32 trace 中的安全 refs 和 policy，不读取 provider raw、签名 URL、本地路径、
媒体字节或 secret，不改变 provider prompt inclusion policy。

## 本轮改动

- `keyframe-source-evidence-trace.js` 增加 `keyframeSourceEvidenceTraceSummaryText()`。
- `inspector-panel.js` 的 `输出记录` 追加 keyframe source evidence trace 摘要。
- focused Node 回归验证 trace summary 会过滤不安全字段，并确认 inspector 已接线。

## 非目标和边界

- 不新增 Runtime route。
- 不更新 request schema 或 OpenAPI。
- 不调用 live provider。
- 不把来源证据注入 provider prompt。
- 不生成或保存媒体字节。
- 不 deploy、不 server sync、不做 Runtime health check。
- 不声明 human creative acceptance、business validation 或 durable memory promotion。

## 验证

已执行 focused verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_keyframe_layer_source_evidence.py
# 5 passed

.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_mature_shell_static.py::test_studio_mature_shell_exposes_algorithm_console_and_quick_start_rail tests\test_web_studio_feedback_candidate_static.py::test_studio_feedback_overlay_review_surface_reads_context_bundle_only tests\test_web_studio_assets_generation_static.py::test_keyframe_prompt_uses_editable_candidate_asset_plan_details
# 3 passed

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
# yaml_ok=True; current_task_id=AFS-T33

branch preflight after push
# pending post-push check
```

## Cleanup Review

- 没有新增 sanitizer；trace summary 复用 `sourceEvidenceRefs()`。
- 没有新增 UI 面板，只复用 inspector `输出记录`。
- 没有新增 Runtime/public API surface。
- 触达 JS/test 文件均低于 300 行。
- `docs/demo-docs-20260629/` 未清理、未暂存、未纳入本轮成果。

## 下一步

T33 commit/push 和 branch preflight 通过后，如果分支仍低于阈值，可以继续
provider-closed 切片。下一步最有效方向是把 keyframe trace 与 production graph review 的
固定资产复用证据继续对齐，但仍不改变 provider prompt inclusion policy。
