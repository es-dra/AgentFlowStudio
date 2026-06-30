# AFS TaskRun - Studio 质量反馈上下文覆盖 UI - 2026-06-30

## 任务

Task ID: `AFS-T15h Studio Quality Feedback Context Overlay UI Hook`

分支：`codex/afs-project-book-full-goal-20260630`

起始 HEAD：`ee87172d6a32bf90e91bdf246458ceb040b96fb5`

状态：已完成本地实现、聚焦测试、全量 pytest、CLI、Studio JS、维护审计和
`git diff --check` 验证；提交/推送状态以本线程最终 git 证据为准。本文是结构验证
记录，不是人类验收、provider smoke、服务器同步或商业验证。

## 摘要

本切片补齐质量反馈回路中的一个实际缺口。Runtime 已经具备三类安全接口：

- `/feedback`：记录安全的原始反馈，并生成 feedback candidate。
- `/projects/{project_id}/feedback-candidate-promotions`：审查并提升候选反馈。
- `/projects/{project_id}/feedback-candidate-context-overlays`：写入下一次本地上下
  文可消费的安全 overlay。

此前 Studio 可以记录质量反馈，也可以查看已消费的反馈 overlay，但缺少一条从
“刚记录的质量反馈候选”到“下一次本地上下文 overlay”的显式操作路径。本轮新增
的 UI 入口是默认关闭的复选框：用户正常记录反馈时，行为仍然只是保存证据；只有
操作员明确勾选“纳入下一次本地上下文”后，Studio 才会请求 Runtime 做候选提升和
context overlay 写入。

## Dirty Ownership Ledger

| 范围 | 归属 | 处理 |
|---|---|---|
| `apps/studio/src/quality-feedback.js` | T15h UI hook | 保留；只新增默认关闭的下一次上下文选项和结果文案。 |
| `apps/studio/src/feedback-candidate-flow.js` | T15h 新 helper | 保留；构造安全 promotion/context-overlay 请求和有界摘要。 |
| `apps/studio/src/quality-feedback-runtime-flow.js` | T15h 新 helper | 保留；把 Runtime feedback 串联逻辑从 `main.js` 中移出。 |
| `apps/studio/src/main.js` | T15h 集成 | 保留；入口变薄，只委托反馈 Runtime 处理。 |
| `apps/studio/styles/node-result.css` | T15h UI 样式 | 保留；只增加复选框布局。 |
| `apps/api/runtime_studio_state_quality_feedback.py` | T15h sanitizer | 保留；定义 `qualityFeedbackCandidates` 的持久化安全边界。 |
| `apps/api/runtime_studio_state_params.py` | T15h sanitizer wiring | 保留；白名单接入并委托专用 sanitizer。 |
| `tests/test_web_studio_feedback_candidate_static.py` | T15h Studio contract 测试 | 保留；覆盖显式 UI、helper、无 fetch 绕路、无 provider gate。 |
| `tests/test_api_runtime_studio_quality_feedback_state.py` | T15h state contract 测试 | 保留；拆成独立文件，避免扩大 oversized 测试债。 |
| `tests/test_api_runtime_studio_feedback_overlay_state.py` | T15h 清理 | 初始新增测试已移出，避免把既有文件推过维护阈值。 |
| `tests/test_web_studio_assets_generation_static.py` | T15h 静态测试校准 | 保留；断言委托后的真实合同，而不是强迫逻辑留在 `main.js`。 |
| `DEVLOG.md`、`TASK_TRACKER.md`、`docs/handoff/INDEX.md` | T15h 记录 | 已更新。 |
| 外部 execution state YAML | T15h 执行状态 | 只做最小状态更新。 |
| `docs/demo-docs-20260629/` | 既有未跟踪 do-not-touch | 未触碰、未清理、不会 staged。 |

## 读取范围

- `AGENTS.md`
- `docs/company_operating_model.md`
- `TASK_TRACKER.md`
- `DEVLOG.md`
- `docs/handoff/INDEX.md`
- `docs/handoff/AFS-MODEL-CALL-FEEDBACK-OVERLAY-SANITIZER-SPLIT-20260630.md`
- `AFS-Task-Ledger-v0.1.md`
- `AFS-AI-Execution-Spec.yaml`
- `AFS-Goal-Driven-Execution-State-v0.1.yaml`
- `apps/api/runtime_service.py`
- `apps/api/runtime_feedback_candidate.py`
- `apps/api/runtime_events.py`
- `apps/api/runtime_studio_state*.py`
- `apps/studio/src/quality-feedback.js`
- `apps/studio/src/runtime-client.js`
- `apps/studio/src/main.js`
- `apps/studio/src/feedback-context-overlays.js`
- `apps/studio/src/feedback-overlay-review.js`
- 反馈候选、Studio state、质量反馈相关测试

## 写入范围

- `apps/studio/src/quality-feedback.js`
- `apps/studio/src/feedback-candidate-flow.js`
- `apps/studio/src/quality-feedback-runtime-flow.js`
- `apps/studio/src/main.js`
- `apps/studio/styles/node-result.css`
- `apps/api/runtime_studio_state_quality_feedback.py`
- `apps/api/runtime_studio_state_params.py`
- `tests/test_web_studio_feedback_candidate_static.py`
- `tests/test_api_runtime_studio_quality_feedback_state.py`
- `tests/test_web_studio_assets_generation_static.py`
- `DEVLOG.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- 本 handoff
- 外部 execution state YAML

## Contract 判断

`qualityFeedbackCandidates` 是 Studio state 中的安全摘要，不是原始反馈、不是长期
记忆、不是 Company KB 知识，也不是 provider 结果。默认合同保持保守：

- 用户提交质量反馈。
- Runtime 记录 feedback event，并创建 feedback candidate。
- 除非操作员显式勾选下一次上下文选项，否则不做 candidate promotion。

当操作员显式选择纳入下一次本地上下文时：

- Studio 调用 Runtime feedback-candidate promotion。
- Studio 调用 Runtime feedback-candidate context-overlay creation。
- Runtime 将 overlay artifact 追加到 `feedback_refs`。
- 后续本地 context resolver 可通过既有 feedback overlay 路径消费该记录。

Studio 节点上只保存安全 ID、状态和三个 false 边界：
`provider_calls_started=false`、`writes_long_term_memory=false`、
`writes_company_kb=false`。节点 state 不保存 drift note 原文、provider raw、signed
URL、本地绝对路径、媒体字节或生成媒体。

## 本轮改动

- 在质量反馈表单中新增默认关闭的“纳入下一次本地上下文”复选框。
- 新增 `feedback-candidate-flow.js`，统一构造安全 promotion 与 context-overlay
  请求，并输出有界摘要。
- 新增 `quality-feedback-runtime-flow.js`，让 `main.js` 不再直接持有完整 Runtime
  feedback 串联逻辑。
- 新增 Runtime Studio-state sanitizer，允许持久化安全的
  `qualityFeedbackCandidates` 摘要。
- 校准既有静态测试，让测试表达委托后的真实产品合同。
- 初始测试放入既有 oversized 文件后，维护审计显示风险增加；随后拆到
  `tests/test_api_runtime_studio_quality_feedback_state.py`，`oversized_files` 恢复到
  既有 59 项。

## Provider Gate

本 TaskRun 未打开任何 provider gate：

- live LLM：未调用
- live image：未调用
- live video：未调用
- live vision：未调用
- live ASR：未调用
- external download：未调用

本轮没有服务器 Runtime health 检查、三端同步、部署、master merge 或 provider
smoke。

## 验证

聚焦测试：

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_studio_feedback_overlay_state.py tests\test_api_runtime_studio_quality_feedback_state.py tests\test_api_runtime_studio_state_modules.py tests\test_web_studio_feedback_candidate_static.py tests\test_web_studio_assets_generation_static.py -q
# 42 passed, 1 existing Starlette/httpx deprecation warning
```

反馈/Studio 回归：

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_feedback.py tests\test_api_runtime_feedback_candidate_context_consumption.py tests\test_api_runtime_studio_state.py tests\test_api_runtime_studio_state_persistence.py tests\test_api_runtime_studio_feedback_overlay_state.py tests\test_api_runtime_studio_state_modules.py tests\test_web_studio_assets_generation_static.py tests\test_web_studio_feedback_candidate_static.py -q
# 62 passed, 1 existing Starlette/httpx deprecation warning
```

全量收口：

```text
.\.venv\Scripts\python.exe -m pytest
# 743 passed, 520 deselected, 2 warnings

.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

npm.cmd run check:studio-js
# JS syntax check passed: 132 files

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; passed=3; warning=4
# 既有 warning：legacy_frozen_surface=10, human_doc_chinese_coverage=22,
# secret_like_fragments=9, oversized_files=59

git diff --check
# passed
```

## Evidence State

`structure_verified_studio_quality_feedback_context_overlay_ui_hook`

含义：本地 deterministic contract、Studio UI state 和 Runtime state sanitizer 证据已
通过。该证据不代表 provider smoke、人类创意验收、商业验证、服务器同步、Runtime
健康验证或长期记忆晋升。

## 清理复核

- 保留新的 Studio helper，因为它们避免 `main.js` 继续积累 Runtime 串联逻辑。
- 保留新的 Runtime Studio-state sanitizer，因为它是单职责边界模块。
- 新增测试拆到独立文件，避免扩大既有 oversized 测试债。
- 未新增冗余 Runtime route、OpenAPI path、provider adapter、生成媒体或临时产物。

## Deferred Items

- 实际复选框路径的浏览器/runtime QA 可在后续 UI smoke 切片中补齐。
- 更完整的 feedback candidate 操作员审查界面仍然暂缓；本轮只实现最小显式
  next-context hook。
- 本轮不需要 OpenAPI 变更，因为 Runtime route 已存在，Studio client 也已有薄方法。

## Next Valid Task

继续执行 provider-closed 的 project-book 切片。最合适的后续任务是为本反馈到
overlay 路径补一个浏览器/runtime QA harness，或者推进下一个 workbench 生产流缺口。
`AFS-T19 Authorized Master Merge + Three-End Sync` 仍需用户显式授权后才能执行。
