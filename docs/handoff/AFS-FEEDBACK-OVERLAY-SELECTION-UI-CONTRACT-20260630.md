# AFS TaskRun - Feedback Overlay Selection UI Contract - 2026-06-30

## 任务

Task ID: `AFS-T16 Feedback Overlay Selection / Rejection UI Contract`

分支: `codex/afs-project-book-full-goal-20260630`

起始 HEAD: `829f980d8157059fb721f399eda4bcfe33cb9493`

状态: 已实现；focused 验证和 closeout 验证已通过；提交、push 和分支 preflight 将在本记录更新后执行。

## 中文摘要

本轮继续 project-book goal mode，但没有执行 `master` 合并、服务器三端同步、Runtime 重启、Runtime health 核验或 provider smoke。`AFS-T19 Authorized Master Merge + Three-End Sync` 仍需要用户明确授权。

T15d 已让 Runtime context resolver 消费安全的 `runtime_feedback_candidate_context_overlay` artifact，T15e 已让 Studio 可以展示已消费的 `lastContextBundle.feedback_context_overlays`。T16 的最小切片是补上“人可以对这些 overlay 做下一轮上下文选择”的合同：Studio 在本地节点状态记录 include/reject 决策，keyframe 请求把安全决策放入 `context_subgraph.nodes[].node_parameters.feedback_context_overlay_decisions`，Runtime resolver 按这些决策过滤 `feedback_context_overlays`。

这不是 provider prompt 注入，不是新 Runtime route，不是 OpenAPI 扩展，不是固定资产确认，不是长期记忆，不是 Company KB，不是生成媒体，也不是人类创意验收或业务验证。

## Dirty Ownership Ledger

| Surface | Ownership | Handling |
|---|---|---|
| `apps/api/runtime_feedback_context.py` | T16 Runtime overlay decision filter | 保留；在已有 overlay helper 内增加 selected/rejected ID 过滤，仍低于 300 行。 |
| `apps/api/runtime_context_resolver.py` | T16 resolver integration | 保留；把 `context_subgraph` 传给 overlay helper。 |
| `apps/api/runtime_studio_state_feedback_overlay.py` | T16 Studio state sanitizer helper | 新增小文件；只保留 overlay/candidate ID、decision、reviewed_at 和 false safety booleans。 |
| `apps/api/runtime_studio_state_params.py` / `runtime_studio_state_sanitizer.py` | T16 state whitelist | 保留；允许 `feedbackOverlayDecisions` 走专用 sanitizer，避免保存 raw/provider/local path。 |
| `apps/studio/src/feedback-context-overlays.js` | T16 Studio helper | 保留；增加 request decision normalization 和当前 decision 查询。 |
| `apps/studio/src/feedback-overlay-review.js` | T16 Studio local UI | 新增小文件；只写本地节点参数，不 `fetch`，不调用 overlay creation route。 |
| `apps/studio/src/panels/node-menu.js` | T16 menu entry | 保留；仅在节点已有 feedback overlays 时显示“选择反馈上下文”。 |
| `apps/studio/src/optimizer-contract.js` | T16 request projection | 保留；把本地决策映射为 snake_case Runtime node parameters。 |
| `tests/test_api_runtime_feedback_candidate_context_consumption.py` | T16 Runtime regression | 保留；覆盖 include/reject 对 resolver 输出的影响。 |
| `tests/test_api_runtime_studio_feedback_overlay_state.py` | T16 state regression | 保留；覆盖 unsafe raw/path 被剔除且 safety booleans 被强制 false。 |
| `tests/test_web_studio_feedback_candidate_static.py` | T16 Studio static guard | 保留；防止 UI 变成 provider/route/overlay creation 入口。 |
| `DEVLOG.md`, `TASK_TRACKER.md`, `docs/handoff/INDEX.md` | T16 project records | 保留。 |
| external execution state YAML | T16 execution state | 最小更新，位于 Learning_notes 项目书目录。 |
| `docs/demo-docs-20260629/` | 既有 untracked do-not-touch | 未触碰、未 stage、未清理。 |

## 读取范围

- `AGENTS.md`
- `docs/company_operating_model.md`
- `TASK_TRACKER.md`
- `DEVLOG.md`
- `docs/handoff/INDEX.md`
- `docs/handoff/AFS-STUDIO-FEEDBACK-OVERLAY-REVIEW-SURFACE-20260630.md`
- `docs/handoff/AFS-FEEDBACK-CANDIDATE-CONTEXT-CONSUMPTION-TASKRUN-20260630.md`
- `apps/api/runtime_feedback_context.py`
- `apps/api/runtime_context_resolver.py`
- `apps/api/runtime_studio_state_params.py`
- `apps/api/runtime_studio_state_sanitizer.py`
- `apps/studio/src/feedback-context-overlays.js`
- `apps/studio/src/panels/node-menu.js`
- `apps/studio/src/optimizer-contract.js`
- Runtime feedback/context/Studio-state 相关测试
- external execution state YAML

## 写入范围

- `apps/api/runtime_feedback_context.py`
- `apps/api/runtime_context_resolver.py`
- `apps/api/runtime_studio_state_feedback_overlay.py`
- `apps/api/runtime_studio_state_params.py`
- `apps/api/runtime_studio_state_sanitizer.py`
- `apps/studio/src/feedback-context-overlays.js`
- `apps/studio/src/feedback-overlay-review.js`
- `apps/studio/src/panels/node-menu.js`
- `apps/studio/src/optimizer-contract.js`
- `tests/test_api_runtime_feedback_candidate_context_consumption.py`
- `tests/test_api_runtime_studio_feedback_overlay_state.py`
- `tests/test_web_studio_feedback_candidate_static.py`
- 本 handoff
- `DEVLOG.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- external execution state YAML

## Contract 判断

`feedback_context_overlays` 现在仍是 Runtime 生成的安全上下文摘要，不是 provider prompt 文本。T16 新增的是 Studio-facing 的“下一轮上下文选择合同”：

- Studio 只允许记录 `include_for_next_context` 或 `reject_for_next_context`。
- Studio state 中的 `feedbackOverlayDecisions` 只保留 `overlay_id`、`candidate_id`、`decision`、`reviewed_at`、`provider_calls_started=false`、`writes_long_term_memory=false`、`writes_company_kb=false`。
- Studio keyframe request 只通过 `context_subgraph.nodes[].node_parameters.feedback_context_overlay_decisions` 传递安全决策。
- Runtime context resolver 只按 overlay ID 过滤已有安全 overlays，并在 `trace_summary` 记录 selected/rejected IDs。
- 如果没有实际 selected/rejected ID，不新增 decision trace，避免污染无 overlay 的 context bundle。
- OpenAPI path count 不变，仍为 52；本轮没有新增 public route。

## 安全边界

本轮没有打开任何 provider gate，没有调用 live LLM/image/video/vision/ASR provider，没有写 provider raw、signed URL、本地绝对路径、生成媒体字节、secret、cookie、token、客户信息或真实成本。

前端只接触安全 overlay summary 和安全 decision；不接触 provider raw、本地绝对路径、signed URL、媒体字节或 CLI 内部实现。

## 本轮改动

- Runtime overlay helper 支持从 target node parameters 读取 include/reject decisions，并过滤已消费 overlay 列表。
- Studio state 保存支持 `feedbackOverlayDecisions` 专用 sanitizer，unsafe 字段被剔除，安全边界布尔值强制为 false。
- Studio 新增本地 review popover：节点已有 feedback overlays 时，可以在节点菜单选择“选择反馈上下文”，对单个 overlay 记录“纳入”或“拒绝”。
- Studio keyframe request 自动把本地 decision 投影为 Runtime snake_case 参数。
- 新增 Runtime、Studio state、Studio static 三类回归测试，覆盖选择/拒绝、保存清洗、前端无 provider/route 侧效应。

## 验证

红测基线:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_feedback_candidate_context_consumption.py::test_context_resolver_applies_studio_feedback_overlay_selection_decisions -q
# 1 failed as expected because Runtime returned both overlays before decision filtering.

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_studio_feedback_overlay_state.py::test_studio_state_persists_feedback_overlay_decisions_as_safe_node_params -q
# 1 failed as expected because feedbackOverlayDecisions was not whitelisted/sanitized.

.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_feedback_candidate_static.py::test_studio_feedback_overlay_selection_ui_is_local_and_provider_closed tests\test_web_studio_feedback_candidate_static.py::test_keyframe_generation_request_carries_feedback_overlay_decisions -q
# failed as expected because the selection UI/request projection did not exist yet.
```

Focused green:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_feedback_candidate_context_consumption.py -q
# 3 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_studio_feedback_overlay_state.py tests\test_web_studio_feedback_candidate_static.py -q
# 7 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_studio_state.py tests\test_api_runtime_studio_state_persistence.py -q
# 15 passed, 1 existing Starlette/httpx deprecation warning

npm.cmd run check:studio-js
# JS syntax check passed: 130 files
```

Closeout verification will be updated after final commands complete.

Closeout verification:

```text
.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

.\.venv\Scripts\python.exe -m pytest
# first closeout run: 1 failed because the new UI copy included "知识库",
# which violated the existing product-facing prompt optimizer source guard.
# fixed by changing the visible copy to "公司资料".

.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_mature_shell_static.py::test_prompt_optimizer_sources_stay_product_facing -q
# 1 passed

.\.venv\Scripts\python.exe -m pytest
# 734 passed, 520 deselected, 2 warnings

npm.cmd run check:studio-js
# JS syntax check passed: 130 files

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning, failed=0, passed=3, warning=4
# existing warning families: legacy_frozen_surface, human_doc_chinese_coverage,
# secret_like_fragments, oversized_files

git diff --check
# passed

.\.venv\Scripts\python.exe -c "import yaml, pathlib; path=pathlib.Path(r'D:\Learning materials\Learning_notes\10-Startup\70-Projects\AI-Native-Project-Books\2026-06-30-COS-AFS-autonomous-project-book\AFS-Goal-Driven-Execution-State-v0.1.yaml'); yaml.safe_load(path.read_text(encoding='utf-8')); print('yaml_ok')"
# yaml_ok
```

## Evidence State

```text
structure_verified_feedback_overlay_selection_contract_full_local_verification
```

这只是本地 deterministic Runtime/Studio contract evidence。它不是 provider smoke，不是 generated media evidence，不是 Runtime health verification，不是 server sync，不是 human creative acceptance，不是 business validation，也不是 durable memory promotion。

## Cleanup Review

- 新增两个小 helper 文件，避免继续推高既有 state/Studio 菜单模块复杂度。
- `runtime_feedback_context.py` 当前 207 行，`feedback-overlay-review.js` 当前 101 行，均低于 300 行理想阈值。
- `optimizer-contract.js` 是既有 342 行 warning，本轮只增加 3 行 request projection；拆分应放入后续专门维护切片。
- 没有新增 Runtime route、OpenAPI snapshot 改动、第二套 feedback subsystem、provider 配置、生成媒体或服务器状态写入。
- 没有触碰或 stage `docs/demo-docs-20260629/`。

## Deferred Items

- Provider prompt 是否以及如何消费 selected feedback overlay 仍暂缓，需要单独的 prompt policy gate。
- Overlay decision 的撤销/批量管理/排序 UI 仍可后续增强；本轮只做最小 include/reject 合同。
- `optimizer-contract.js` 仍处于 300 行以上维护 warning，后续可做 request projection split。
- `AFS-T19 Authorized Master Merge + Three-End Sync` 仍需要用户明确授权。
- Provider smoke 仍需要单独能力授权。

## Next Valid Task

```text
AFS-T17 Feedback Overlay Prompt Policy Gate
```

可选授权任务:

```text
AFS-T19 Authorized Master Merge + Three-End Sync
```
