# AFS TaskRun - Studio Feedback Overlay Review Surface - 2026-06-30

## 任务

Task ID：`AFS-T15e Studio Feedback Overlay Review Surface`

分支：`codex/afs-project-book-full-goal-20260630`

起始 HEAD：`7be884f75829da9e6614aab288898b11f04775bb`

状态：已实现；focused 验证和完整 closeout 验证已通过；提交、push、push 后分支 preflight 在本记录更新后执行。

## 中文摘要

本轮继续 project-book goal mode，但没有执行 `master` 合并、服务器三端同步、Runtime 重启、Runtime health 核验或 provider smoke。`AFS-T19 Authorized Master Merge + Three-End Sync` 仍需要用户明确授权。

T15d 已经让 Runtime context resolver 把人工允许的 `runtime_feedback_candidate_context_overlay` artifact 消费为 `context_bundle.feedback_context_overlays`。T15e 的最小切片是把这份已消费的安全 overlay 摘要接到 Studio 状态保存和现有 inspector/algorithm review 面板上，使 Studio 能看见“本次上下文已纳入哪些反馈 overlay”，而不是只停留在 Runtime 返回值。

这不是新的反馈创建 UI，不是 promotion UI，不是 provider prompt 注入，不是长期记忆，不是 Company KB 规则，不是生成媒体，也不是人工创意验收或业务验证。Studio 只读取 `lastContextBundle.feedback_context_overlays`，不调用 overlay 创建 route，不打开 provider gate。

## Dirty Ownership Ledger

| Surface | Ownership | Handling |
|---|---|---|
| `apps/api/runtime_studio_state_context.py` | T15e Studio state sanitizer | 保留；只允许 `feedback_context_overlays` 的安全摘要字段进入 `lastContextBundle`。 |
| `apps/studio/src/feedback-context-overlays.js` | T15e Studio helper | 保留；纯格式化 helper，不 fetch、不写状态、不创建 overlay。 |
| `apps/studio/src/panels/inspector-context-summary.js` | T15e review surface | 保留；在现有“本次参考摘要”里展示反馈上下文摘要。 |
| `apps/studio/src/panels/algorithm-context-panel.js` | T15e algorithm summary | 保留；把已消费 overlay 计入反馈信号和节点过程摘要。 |
| `tests/test_api_runtime_studio_feedback_overlay_state.py` | T15e focused state regression | 保留；新建小文件，避免把既有 oversized state 测试继续推高。 |
| `tests/test_web_studio_feedback_candidate_static.py` | T15e Studio static guard | 保留；确认 helper 只读 context bundle，不触发 Runtime/provider。 |
| `DEVLOG.md`, `TASK_TRACKER.md`, `docs/handoff/INDEX.md` | T15e 项目记录 | 保留。 |
| external execution state YAML | T15e 执行状态 | 最小更新，位于 Learning_notes 项目书目录。 |
| `docs/demo-docs-20260629/` | 既有 untracked do-not-touch | 未触碰、未 stage、未清理。 |

## 读取范围

- `AGENTS.md`
- `docs/company_operating_model.md`
- `TASK_TRACKER.md`
- `DEVLOG.md`
- `docs/handoff/INDEX.md`
- `docs/handoff/AFS-FEEDBACK-CANDIDATE-CONTEXT-CONSUMPTION-TASKRUN-20260630.md`
- `apps/api/runtime_studio_state_context.py`
- `apps/api/runtime_studio_state_sanitizer.py`
- `apps/api/runtime_studio_state_params.py`
- `apps/api/runtime_feedback_context.py`
- `apps/studio/src/runtime-client.js`
- `apps/studio/src/panels/inspector-context-summary.js`
- `apps/studio/src/panels/algorithm-context-panel.js`
- `apps/studio/src/node-keyframe-response.js`
- `apps/studio/src/node-video-actions.js`
- Runtime Studio-state 和反馈 context 相关测试
- external execution state YAML

## 写入范围

- `apps/api/runtime_studio_state_context.py`
- `apps/studio/src/feedback-context-overlays.js`
- `apps/studio/src/panels/inspector-context-summary.js`
- `apps/studio/src/panels/algorithm-context-panel.js`
- `tests/test_api_runtime_studio_feedback_overlay_state.py`
- `tests/test_web_studio_feedback_candidate_static.py`
- 本 handoff
- `DEVLOG.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- external execution state YAML

## Contract 判断

Studio-facing contract 现在是：

- `lastContextBundle.feedback_context_overlays` 可以作为 Studio review surface 的安全输入；
- Studio state 只持久化 bounded safe summary；
- 允许字段包括 overlay/candidate/promotion IDs、scope、safe target、safe evidence summary、decision effect、`context_overlay_consumed`、`candidate_feedback_included_in_context`、`provider_calls_started=false`、`writes_long_term_memory=false`、`writes_company_kb=false`、安全 artifact ref；
- Studio state 丢弃 `trace_summary`、`provider_raw`、`signed_url`、`local_path` 和 `safety_boundary`；
- `safety_boundary.media_bytes_stored` 这类字段名本身会触发全局 forbidden fragment，因此不持久化进 Studio state；
- Studio UI 不创建 overlay，不调用 `recordFeedbackCandidateContextOverlay(...)`，也不发起 provider 请求；
- Runtime public route/OpenAPI path count 不变，仍为 52。

## 本轮改动

- 新增 `feedback-context-overlays.js`，集中格式化反馈 overlay 摘要和计数。
- `inspector-context-summary.js` 在“本次参考摘要”里显示 `反馈上下文：...`。
- `algorithm-context-panel.js` 把 overlay count 算作反馈信号，并在无素材/节点上下文时显示已消费反馈上下文。
- `runtime_studio_state_context.py` 保存 `lastContextBundle.feedback_context_overlays` 的安全字段，同时剪掉 raw/provider/path/signed/safety-boundary 字段。
- 新增 `tests/test_api_runtime_studio_feedback_overlay_state.py` 覆盖纯 sanitizer 和 `/studio-state` 保存读取路径。
- 扩展 `tests/test_web_studio_feedback_candidate_static.py`，防止 review surface 变成 route/provider/overlay 创建入口。

## 验证

红测基线：

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_studio_state.py::test_studio_state_preserves_safe_feedback_context_overlay_summary -q
# 1 failed as expected because feedback_context_overlays were not persisted.

.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_feedback_candidate_static.py -q
# 1 failed as expected because apps/studio/src/feedback-context-overlays.js did not exist.
```

Focused green：

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_studio_feedback_overlay_state.py tests\test_api_runtime_studio_state.py tests\test_api_runtime_studio_state_persistence.py tests\test_web_studio_feedback_candidate_static.py -q
# 19 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_feedback_candidate_context_consumption.py tests\test_api_runtime_studio_feedback_overlay_state.py tests\test_web_studio_feedback_candidate_static.py -q
# 6 passed, 1 existing Starlette/httpx deprecation warning

npm.cmd run check:studio-js
# JS syntax check passed: 129 files
```

Closeout verification：

```text
.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

.\.venv\Scripts\python.exe -m pytest
# 730 passed, 520 deselected, 2 warnings

npm.cmd run check:studio-js
# JS syntax check passed: 129 files

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning, failed=0, passed=3, warning=4
# existing warning families: legacy_frozen_surface, human_doc_chinese_coverage,
# secret_like_fragments, oversized_files

git diff --check
# passed

YAML parse check
# yaml_ok
```

## Evidence State

```text
structure_verified_studio_feedback_overlay_review_surface_full_local_verification
```

这只是本地 deterministic Studio state/UI contract evidence。它不是 provider smoke，不是 generated media evidence，不是 Runtime health verification，不是 server sync，不是 human creative acceptance，不是 business validation，也不是 durable memory promotion。

## Cleanup Review

- 新增小 helper，而不是把格式化逻辑塞进现有面板或 Runtime client。
- 本轮新增测试放在专门小文件中；没有把 `test_api_runtime_studio_state.py` 推过 500 行。
- `apps/studio/src/panels/algorithm-context-panel.js` 当前 282 行，仍低于 300 行理想阈值。
- `apps/api/runtime_studio_state_context.py` 当前 238 行，仍低于 300 行理想阈值。
- 没有新增 Runtime route、OpenAPI snapshot 变更、provider 配置、生成媒体或第二套 feedback subsystem。
- 没有触碰或 stage `docs/demo-docs-20260629/`。

## Deferred Items

- 反馈 overlay 的人工选择/撤销/排序 UI 仍暂缓；当前只展示已由 Runtime context resolver 消费的 overlay。
- Provider prompt 是否以及如何消费 overlay 仍暂缓；T15d/T15e 都只做本地 evidence 和 review surface。
- `AFS-T19 Authorized Master Merge + Three-End Sync` 仍需要用户明确授权。
- Provider smoke 仍需要单独的能力授权。

## Next Valid Task

```text
AFS-T16 Feedback Overlay Selection / Rejection UI Contract
```

可选授权任务：

```text
AFS-T19 Authorized Master Merge + Three-End Sync
```
