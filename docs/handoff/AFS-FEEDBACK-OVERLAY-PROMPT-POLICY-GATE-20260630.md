# AFS TaskRun - Feedback Overlay Prompt Policy Gate - 2026-06-30

## 任务

Task ID: `AFS-T17b Feedback Overlay Prompt Policy Gate`

说明: 本分支历史上已有 `AFS-T17 Goal-Mode Branch Integration Review`，因此本轮使用 `T17b` 后缀，避免重复任务号造成后续交接歧义。

分支: `codex/afs-project-book-full-goal-20260630`

起始 HEAD: `b58a364a32af175ca3fdf60bd4f189ec39d8ce57`

状态: 已实现；focused 验证和本地 closeout 验证已通过；提交、push 和分支 preflight 待执行。

## 中文摘要

本轮继续 project-book goal mode，但没有执行 `master` 合并、服务器三端同步、Runtime 重启、Runtime health 核验或 provider smoke。`AFS-T19 Authorized Master Merge + Three-End Sync` 仍需要用户明确授权。

T16 已让 Studio 可以对已消费的 feedback overlay 做 include/reject 决策，并让 Runtime context resolver 按决策过滤 `feedback_context_overlays`。T17b 的最小切片是补上 provider prompt policy gate：即使某个 overlay 被 Studio 选择，它也只进入本地 context evidence，不会被静默写进 `provider_prompt` 或 provider request canonical prompt。Runtime 现在在 model-call context、request projection、safe manifest、generation bridge 和 context trace 中显式记录同一个 policy：`provider_prompt_includes_context_overlays=false`，默认行为是 `context_evidence_only`，若未来要把 overlay 文本用于 provider prompt，必须走单独的显式 prompt policy gate。

这不是 provider prompt 注入，不是新 Runtime route，不是 OpenAPI 扩展，不是 generated media，不是 durable memory，不是 Company KB 规则，不是服务器同步，也不是人类创意验收或业务验证。

## Dirty Ownership Ledger

| Surface | Ownership | Handling |
|---|---|---|
| `agentflow/algorithms/feedback_overlay_prompt_policy.py` | T17b shared policy helper | 新增小文件；生成单一 policy 对象，避免多个证据面各自发明字段。 |
| `agentflow/algorithms/__init__.py` | T17b algorithm registry | 保留；把 helper 归入 auxiliary engineering module。 |
| `agentflow/algorithms/model_call_context/__init__.py` | T17b model-call evidence | 保留；在 `feedback_context.prompt_policy` 和 trace 中记录 policy。 |
| `agentflow/algorithms/request_projection/__init__.py` | T17b request projection evidence | 保留；在 projection trace 中记录 policy，不改变 provider request prompt 内容。 |
| `agentflow/algorithms/generation_bridge/__init__.py` | T17b bridge evidence | 保留；在 `context_evidence` 中记录同一 policy。 |
| `apps/api/runtime_feedback_context.py` | T17b context trace policy | 保留；在 context bundle trace 中记录同一 policy。 |
| `apps/api/runtime_keyframe_payloads.py` | T17b safe manifest policy | 保留；safe manifest 顶层记录同一 policy。 |
| `tests/test_api_runtime_feedback_candidate_context_consumption.py` | T17b regression | 保留；覆盖 selected overlay 仍不进入 provider prompt，并检查各证据面 policy。 |
| `DEVLOG.md`, `TASK_TRACKER.md`, `docs/handoff/INDEX.md` | T17b project records | 保留。 |
| external execution state YAML | T17b execution state | 最小更新，位于 Learning_notes 项目书目录。 |
| `docs/demo-docs-20260629/` | 既有 untracked do-not-touch | 未触碰、未 stage、未清理。 |

## 读取范围

- `AGENTS.md`
- `docs/company_operating_model.md`
- `TASK_TRACKER.md`
- `DEVLOG.md`
- `docs/handoff/INDEX.md`
- `docs/handoff/AFS-FEEDBACK-OVERLAY-SELECTION-UI-CONTRACT-20260630.md`
- external execution state YAML
- `apps/api/runtime_feedback_context.py`
- `apps/api/runtime_context_text.py`
- `apps/api/runtime_context_resolver.py`
- `apps/api/runtime_keyframes.py`
- `apps/api/runtime_keyframe_payloads.py`
- `apps/api/runtime_generation_preflight.py`
- `agentflow/algorithms/model_call_context/__init__.py`
- `agentflow/algorithms/request_projection/__init__.py`
- `agentflow/algorithms/generation_bridge/__init__.py`
- Runtime feedback/context/model-call/keyframe 相关测试

## 写入范围

- `agentflow/algorithms/feedback_overlay_prompt_policy.py`
- `agentflow/algorithms/__init__.py`
- `agentflow/algorithms/model_call_context/__init__.py`
- `agentflow/algorithms/request_projection/__init__.py`
- `agentflow/algorithms/generation_bridge/__init__.py`
- `apps/api/runtime_feedback_context.py`
- `apps/api/runtime_keyframe_payloads.py`
- `tests/test_api_runtime_feedback_candidate_context_consumption.py`
- 本 handoff
- `DEVLOG.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- external execution state YAML

## Contract 判断

当前合同明确为：

- `feedback_context_overlays` 是本地安全 context evidence，不是 provider prompt 文本。
- Studio selected overlay 可以影响 Runtime 本地 context overlay 列表，但不能自动进入 provider prompt。
- `provider_prompt_from_bundle(...)` 仍只消费 `text_channel`、fixed asset identity、scene/director/upstream/preference segments。
- `model_request_plan.provider_request.prompt` 仍来自 canonical provider prompt，不读取 overlay intent。
- policy evidence 使用统一字段：
  - `policy_id=feedback_overlay_context_evidence_only_v0`
  - `default_action=context_evidence_only`
  - `provider_prompt_includes_context_overlays=false`
  - `overlay_text_channel=disabled_by_default`
  - `requires_explicit_prompt_policy_gate=true`
- 若未来要把 selected overlay 的文字内容用于 provider prompt，必须通过新的显式任务定义和测试，而不能复用 T16 include 决策作为隐式授权。

## 安全边界

本轮没有打开任何 provider gate，没有调用 live LLM/image/video/vision/ASR provider，没有写 provider raw、signed URL、本地绝对路径、生成媒体字节、secret、cookie、token、客户信息或真实成本。

前端和 Runtime 仍只交换安全引用、safe summary、safe manifest 和本地 policy evidence；不让前端依赖 CLI 内部实现，不把 feedback overlay 提升为 durable memory 或 Company KB。

## 本轮改动

- 新增 `feedback_overlay_prompt_policy` helper，统一生成 feedback overlay prompt policy。
- Runtime context trace、model-call context、request projection、keyframe safe manifest、generation bridge 统一记录 policy evidence。
- 新增回归测试：selected overlay 里带有唯一 marker 时，该 marker 仍存在于本地 `feedback_context_overlays`，但不会出现在 `keyframe_request_plan.provider_prompt` 或 `model_request_plan.provider_request.prompt`。
- 修正 execution state 中 T16 “commit/push pending”的滞后状态，使当前 state 指向 T17b。

## 验证

红测基线:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_feedback_candidate_context_consumption.py::test_selected_feedback_overlay_stays_out_of_provider_prompt_and_records_policy -q
# 1 failed as expected because feedback_context.prompt_policy did not exist yet.
```

Focused green:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_feedback_candidate_context_consumption.py::test_selected_feedback_overlay_stays_out_of_provider_prompt_and_records_policy -q
# 1 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m pytest tests\test_model_call_context_contract.py tests\test_api_runtime_keyframe_generation_bridge.py -q
# 9 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m pytest tests\test_runtime_context_text.py -q
# 4 passed

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_feedback_candidate_context_consumption.py tests\test_model_call_context_contract.py tests\test_api_runtime_keyframe_generation_bridge.py tests\test_api_runtime_creative_agent_keyframes.py tests\test_api_runtime_generation_comparison.py tests\test_api_runtime_openapi_snapshot.py -q
# 28 passed, 1 existing Starlette/httpx deprecation warning
```

Closeout verification:

```text
.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

.\.venv\Scripts\python.exe -m pytest
# 735 passed, 520 deselected, 2 warnings

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
structure_verified_feedback_overlay_prompt_policy_gate_full_local_verification_no_merge
```

这只是本地 deterministic Runtime/request-policy contract evidence。它不是 provider smoke，不是 generated media evidence，不是 Runtime health verification，不是 server sync，不是 human creative acceptance，不是 business validation，也不是 durable memory promotion。

## Cleanup Review

- 新增 policy helper 72 行；未推高 300 行维护阈值。
- 触达的核心文件仍低于 300 行：`model_call_context` 245 行、`request_projection` 102 行、`generation_bridge` 168 行、`runtime_feedback_context` 246 行、`runtime_keyframe_payloads` 150 行。
- 没有新增 Runtime route、OpenAPI snapshot 改动、第二套 feedback subsystem、provider 配置、生成媒体或服务器状态写入。
- 没有触碰或 stage `docs/demo-docs-20260629/`。

## Deferred Items

- 如果未来要允许 selected overlay 文本进入 provider prompt，需要单独任务定义、UI/Runtime 显式授权、prompt budget/安全清洗、provider gate 说明和回归测试。
- Studio 还没有展示 prompt policy evidence；本轮只做 Runtime/request evidence。
- `optimizer-contract.js` 仍处于 300 行以上维护 warning，后续可做 request projection split。
- `AFS-T19 Authorized Master Merge + Three-End Sync` 仍需要用户明确授权。
- Provider smoke 仍需要单独能力授权。

## Next Valid Task

```text
AFS-T18b Feedback Overlay Prompt Policy Review Surface
```

可选授权任务:

```text
AFS-T19 Authorized Master Merge + Three-End Sync
```
