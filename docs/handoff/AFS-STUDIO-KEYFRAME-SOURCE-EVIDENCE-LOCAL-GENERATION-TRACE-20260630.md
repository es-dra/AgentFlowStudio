# AFS-T32 Studio Keyframe Source Evidence Local Generation Trace

## 任务信息

- Task ID: `AFS-T32`
- 分支: `codex/afs-goal-mode-threshold-gate-20260630`
- 起点 HEAD: `4e4a9c9b`
- 模式: provider-closed full goal-mode product slice
- 记录时状态: 已实现并通过本地 closeout 验证；commit/push 与 post-push branch preflight 待执行

本轮把 T30/T31 的 keyframe source evidence 从 UI review surface 延伸到 Studio 本地
generation trace。目标是让关键帧生成响应处理后，节点能保留一份安全 trace，说明本次关键帧
关联了哪些固定资产来源证据，同时明确这些证据默认不进入 provider prompt。

## Dirty Ownership Ledger

本轮拥有:

- `apps/studio/src/keyframe-source-evidence-trace.js`
- `apps/studio/src/panels/inspector-context-summary.js`
- `apps/studio/src/node-keyframe-response.js`
- `tests/test_web_studio_keyframe_layer_source_evidence.py`
- `DEVLOG.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- `docs/handoff/AFS-STUDIO-KEYFRAME-SOURCE-EVIDENCE-LOCAL-GENERATION-TRACE-20260630.md`
- `D:\Learning materials\Learning_notes\10-Startup\70-Projects\AI-Native-Project-Books\2026-06-30-COS-AFS-autonomous-project-book\AFS-Goal-Driven-Execution-State-v0.1.yaml`

既有 do-not-touch:

- `docs/demo-docs-20260629/` 仍然保持未跟踪、未暂存。

## Contract 判断

Studio keyframe response 现在会在节点参数中保留:

```text
lastKeyframeSourceEvidenceTrace
```

trace 由共享 helper `keyframe-source-evidence-trace.js` 生成，字段为:

- `trace_type`
- `source`
- `provider_prompt_inclusion_policy`
- `fixed_asset_source_evidence_count`
- `fixed_asset_source_evidence_refs`

`provider_prompt_inclusion_policy` 固定为 `excluded_by_default`，表示这只是本地 evidence trace，
不改变 provider prompt inclusion policy。

## 本轮改动

- 新增 `keyframe-source-evidence-trace.js`，集中复用 `sourceEvidenceRefs()` 安全归一化逻辑。
- `inspector-context-summary.js` 改为复用共享 helper 生成 keyframe 来源证据摘要。
- `node-keyframe-response.js` 在 keyframe response apply 阶段写入
  `lastKeyframeSourceEvidenceTrace`。
- 扩展 executable Node 回归，验证 trace 会记录安全来源证据，并剔除不安全字段。

## 非目标和边界

- 不新增 Runtime route。
- 不更新 request schema 或 OpenAPI。
- 不把来源证据注入 provider prompt。
- 不调用 live provider。
- 不生成或保存媒体字节。
- 不 deploy、不 server sync、不做 Runtime health check。
- 不声明 human creative acceptance、business validation 或 durable memory promotion。

## 验证

已执行 focused verification:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_keyframe_layer_source_evidence.py
# 3 passed

.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_assets_generation_static.py::test_keyframe_prompt_uses_editable_candidate_asset_plan_details tests\test_web_studio_mature_shell_static.py::test_studio_mature_shell_exposes_algorithm_console_and_quick_start_rail tests\test_web_studio_feedback_candidate_static.py::test_studio_feedback_overlay_review_surface_reads_context_bundle_only
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
# yaml_ok=True; current_task_id=AFS-T32

branch preflight after push
# pending post-push check
```

## Cleanup Review

- 没有复制 sanitizer；共享 helper 继续复用 `sourceEvidenceRefs()`。
- 没有新增 Runtime/public API surface。
- 没有新增一次性工具。
- 新增 JS helper 36 行，触达文件均低于 300 行。
- `docs/demo-docs-20260629/` 未清理、未暂存、未纳入本轮成果。

## 下一步

T32 commit/push 和 branch preflight 通过后，如果分支仍低于阈值，可以继续
provider-closed 切片。下一步最有效方向是把 trace 与 production graph review 或生成记录
摘要进一步对齐，仍不改变 provider prompt inclusion policy。
