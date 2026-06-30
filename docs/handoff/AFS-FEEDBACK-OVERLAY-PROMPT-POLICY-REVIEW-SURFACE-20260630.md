# AFS TaskRun - Feedback Overlay Prompt Policy Review Surface - 2026-06-30

## 任务

Task ID: `AFS-T18b Feedback Overlay Prompt Policy Review Surface`

分支: `codex/afs-project-book-full-goal-20260630`

起始 HEAD: `76d2c407c8c0e9622e4421bc185f13d82c1f6a14`

状态: 已实现；focused 验证和本地 closeout 验证已通过；提交、push 和分支 preflight 待执行。

## 中文摘要

本轮继续 project-book goal mode，但没有执行 `master` 合并、服务器三端同步、Runtime 重启、Runtime health 核验或 provider smoke。`AFS-T19 Authorized Master Merge + Three-End Sync` 仍需要用户明确授权。

T17b 已在 Runtime/request 侧记录 `feedback_overlay_prompt_policy`，但 Studio 只能看到 consumed feedback overlay 摘要，无法在 review surface 上确认这些 overlay 不会进入 provider prompt。T18b 的最小切片是在不新增 route、不改 OpenAPI、不启动 provider 的前提下，把同一份 prompt policy 作为安全摘要接入 Studio。

当前 Studio 会在节点上下文摘要和算法过程面板中只读显示反馈 prompt policy：默认显示为“本地上下文，不注入生成提示词”。这只是安全边界可见化，不是 prompt 注入授权，不是 overlay 创建 UI，不是 durable memory，也不是人类创意验收或业务验证。

## Dirty Ownership Ledger

| Surface | Ownership | Handling |
|---|---|---|
| `apps/api/runtime_feedback_context.py` | T18b Runtime bundle surface | 保留；把 T17b 已有 policy 复制到 context bundle 顶层安全字段，便于 Studio 显示。 |
| `apps/api/runtime_studio_state_context.py` | T18b Studio state sanitizer | 保留；只持久化 policy 白名单字段，不保存 trace、provider raw、local path 或 signed URL。 |
| `apps/studio/src/feedback-context-overlays.js` | T18b Studio helper | 保留；复用现有 overlay helper，新增只读 policy normalize/summary。 |
| `apps/studio/src/panels/inspector-context-summary.js` | T18b inspector review surface | 保留；显示反馈提示词策略摘要。 |
| `apps/studio/src/panels/algorithm-context-panel.js` | T18b algorithm process surface | 保留；显示“反馈策略”统计 chip。 |
| `tests/test_api_runtime_feedback_candidate_context_consumption.py` | T18b Runtime regression | 保留；断言 context bundle 顶层 policy 仍为不注入 provider prompt。 |
| `tests/test_api_runtime_studio_feedback_overlay_state.py` | T18b persistence regression | 保留；断言 Studio state 只保存安全 policy 摘要。 |
| `tests/test_web_studio_feedback_candidate_static.py` | T18b Studio static/Node regression | 保留；断言 helper local-only、无 fetch/provider gate，并验证 summary 文案。 |
| `DEVLOG.md`, `TASK_TRACKER.md`, `docs/handoff/INDEX.md` | T18b project records | 本轮更新。 |
| external execution state YAML | T18b execution state | 最小更新，位于 Learning_notes 项目书目录。 |
| `docs/demo-docs-20260629/` | 既有 untracked do-not-touch | 未触碰、未 stage、未清理。 |

## 读取范围

- `AGENTS.md`
- `docs/company_operating_model.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- `docs/handoff/AFS-FEEDBACK-OVERLAY-PROMPT-POLICY-GATE-20260630.md`
- external execution state YAML
- `apps/api/runtime_feedback_context.py`
- `apps/api/runtime_studio_state_context.py`
- `apps/studio/src/feedback-context-overlays.js`
- `apps/studio/src/panels/inspector-context-summary.js`
- `apps/studio/src/panels/algorithm-context-panel.js`
- feedback overlay Runtime/Studio tests

## 写入范围

- `apps/api/runtime_feedback_context.py`
- `apps/api/runtime_studio_state_context.py`
- `apps/studio/src/feedback-context-overlays.js`
- `apps/studio/src/panels/inspector-context-summary.js`
- `apps/studio/src/panels/algorithm-context-panel.js`
- `tests/test_api_runtime_feedback_candidate_context_consumption.py`
- `tests/test_api_runtime_studio_feedback_overlay_state.py`
- `tests/test_web_studio_feedback_candidate_static.py`
- 本 handoff
- `DEVLOG.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- external execution state YAML

## Contract 判断

当前合同仍然是：

- `feedback_context_overlays` 是本地安全 context evidence，不是 provider prompt 文本。
- `feedback_context_overlay_prompt_policy` 是只读安全摘要，用于解释 overlay 文本是否进入 provider prompt。
- 默认 `provider_prompt_includes_context_overlays=false`。
- Studio 可以展示 policy，但不能用展示本身授权 prompt 注入。
- Runtime provider prompt 和 provider request prompt 仍不读取 overlay intent。
- 若未来要把 selected overlay 文本用于 provider prompt，必须走新的显式 prompt policy gate。

## 安全边界

本轮没有打开任何 provider gate，没有调用 live LLM/image/video/vision/ASR provider，没有写 provider raw、signed URL、本地绝对路径、生成媒体字节、secret、cookie、token、客户信息或真实成本。

Studio state sanitizer 只保存 policy 白名单字段：`schema_version`、`policy_id`、`default_action`、`provider_prompt_includes_context_overlays`、`overlay_text_channel`、`requires_explicit_prompt_policy_gate`、`context_overlay_count`、`selected_overlay_ids`、`rejected_overlay_ids`。

## 本轮改动

- Runtime context bundle 顶层新增安全 `feedback_context_overlay_prompt_policy`，复用 trace 中同一 policy。
- Studio state sanitizer 支持持久化安全 policy 摘要，并能从旧 `trace_summary.feedback_context_overlay_prompt_policy` 提取安全字段但不保存 trace。
- Studio overlay helper 新增 policy normalize/summary。
- Inspector context summary 显示“反馈提示词策略”。
- Algorithm process panel 显示“反馈策略”。
- 新增回归测试覆盖 provider prompt 不注入、state sanitizer 安全持久化、Studio helper local-only。

## 验证

Focused green:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_feedback_candidate_context_consumption.py::test_selected_feedback_overlay_stays_out_of_provider_prompt_and_records_policy tests\test_api_runtime_studio_feedback_overlay_state.py tests\test_web_studio_feedback_candidate_static.py -q
# 10 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_feedback_candidate_context_consumption.py tests\test_api_runtime_studio_feedback_overlay_state.py tests\test_web_studio_feedback_candidate_static.py tests\test_api_runtime_studio_state.py tests\test_api_runtime_studio_state_persistence.py tests\test_model_call_context_contract.py tests\test_api_runtime_keyframe_generation_bridge.py -q
# 37 passed, 1 existing Starlette/httpx deprecation warning

npm.cmd run check:studio-js
# JS syntax check passed: 130 files
```

Closeout verification:

```text
.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

.\.venv\Scripts\python.exe -m pytest
# 737 passed, 520 deselected, 2 warnings

npm.cmd run check:studio-js
# JS syntax check passed: 130 files

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; passed=3; warning=4
# existing warnings remain: legacy_frozen_surface=10,
# human_doc_chinese_coverage=22, secret_like_fragments=9,
# oversized_files=59

git diff --check
# passed

YAML parse check for external execution state
# yaml_parse_ok
```

## Evidence State

```text
structure_verified_feedback_overlay_prompt_policy_review_surface_full_local_verification_no_merge
```

这只是本地 deterministic Runtime/Studio review-surface evidence。它不是 provider smoke，不是 generated media evidence，不是 Runtime health verification，不是 server sync，不是 human creative acceptance，不是 business validation，也不是 durable memory promotion。

## Cleanup Review

- 没有新增 Runtime route、OpenAPI path、第二套 feedback subsystem、provider 配置、生成媒体或服务器状态写入。
- `runtime_studio_state_context.py` 当前 277 行，仍低于 300 行，但接近阈值；后续如果再增加 state bundle 字段，应考虑拆出 context bundle policy sanitizer。
- `algorithm-context-panel.js` 当前 293 行，仍低于 300 行，但接近阈值；后续如果再增加过程面板展示，应拆分 stats/render helpers。
- `feedback-context-overlays.js` 当前 126 行，仍低于 300 行。
- 没有触碰或 stage `docs/demo-docs-20260629/`。

## Deferred Items

- 未来如果需要在 Studio 中显式审批“允许 overlay 文本进入 provider prompt”，必须单独定义授权 UI、Runtime policy gate、prompt budget、安全清洗和 provider-gated 测试。
- 如果继续扩展 algorithm process panel，应先拆分 `algorithm-context-panel.js`，避免越过 300 行维护阈值。
- `AFS-T19 Authorized Master Merge + Three-End Sync` 仍需要用户明确授权。
- Provider smoke 仍需要单独能力授权。

## Next Valid Task

```text
AFS-T18c Feedback Overlay Prompt Authorization Design Gate
```

可选授权任务:

```text
AFS-T19 Authorized Master Merge + Three-End Sync
```
