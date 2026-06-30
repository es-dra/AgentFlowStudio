# AFS TaskRun - Feedback Candidate Scope Conflict Contract - 2026-06-30

## 任务

Task ID: `AFS-T15g Feedback Candidate Scope + Conflict Contract`

分支: `codex/afs-project-book-full-goal-20260630`

起始 HEAD: `af441fc93bdd36215a52248b503f773274b85853`

状态: 已实现；focused verification、全量 pytest、CLI、Studio JS、维护审计、diff/YAML closeout 已通过；commit/push 作为本 TaskRun 最后步骤执行。

## 中文摘要

T15f 已经让 feedback candidate 带上受控 `feedback_taxonomy`。本轮继续补齐
feedback governance 的下一个最小合同：候选反馈必须明确绑定项目内目标、保持
project scope，并记录单条反馈内部的 conflict signal。这样后续 full goal-mode 在
消费反馈时不会把某个项目/节点/资产上的反馈误当成全局偏好、Company KB 规则或
durable memory。

新增字段仍然只是安全摘要：

- `target_binding`: project_id、target_kind、bound_refs 和 bound_ref_count。
- `scope_policy`: 明确 global/cross-project/Company KB promotion 均不允许，且需要 human/conflict review。
- `conflict_summary`: 记录单条反馈内是否出现 mixed quality rating、revision success conflict、mixed asset decision 等信号。

## Dirty Ownership Ledger

| Surface | Ownership | Handling |
|---|---|---|
| `apps/api/runtime_events.py` | T15g candidate source | 新增 target binding、scope policy、single-feedback conflict summary。 |
| `agentflow/algorithms/feedback_candidate_promotion/__init__.py` | T15g promotion propagation | promotion decision 复制 safe scope/conflict fields。 |
| `agentflow/algorithms/feedback_candidate_context_overlay/__init__.py` | T15g overlay propagation | context overlay artifact 复制 safe scope/conflict fields。 |
| `apps/api/runtime_feedback_context.py` | T15g context resolver summary | consumed overlay summary 保留 scope/conflict fields。 |
| `agentflow/algorithms/model_call_context/__init__.py` | T15g model context summary | model-call context 保留 safe scope/conflict summary；不进入 provider prompt。 |
| `apps/api/runtime_studio_state_context.py` | T15g Studio-state sanitizer | Studio state 白名单化 safe scope/conflict summary。 |
| feedback Runtime tests | T15g regression | 覆盖 candidate、promotion、overlay、context consumption、model context、Studio state。 |
| `DEVLOG.md`, `TASK_TRACKER.md`, `docs/handoff/INDEX.md` | T15g records | 本轮更新。 |
| external execution state YAML | T15g execution state | 最小更新，仅记录 AFS 项目包状态。 |
| `docs/demo-docs-20260629/` | 既有 untracked do-not-touch | 未触碰、未 stage、未清理。 |

## 读取范围

- `AGENTS.md`
- `docs/company_operating_model.md`
- `TASK_TRACKER.md`
- `docs/handoff/AFS-FEEDBACK-CANDIDATE-TAXONOMY-CONTRACT-20260630.md`
- Runtime feedback/candidate/promotion/context modules
- Model-call context and Studio-state context sanitizer
- Existing feedback, overlay, model context, OpenAPI snapshot tests

## 写入范围

- `apps/api/runtime_events.py`
- `agentflow/algorithms/feedback_candidate_promotion/__init__.py`
- `agentflow/algorithms/feedback_candidate_context_overlay/__init__.py`
- `apps/api/runtime_feedback_context.py`
- `agentflow/algorithms/model_call_context/__init__.py`
- `apps/api/runtime_studio_state_context.py`
- `tests/test_api_runtime_feedback.py`
- `tests/test_api_runtime_feedback_candidate_promotion.py`
- `tests/test_api_runtime_feedback_candidate_context_overlay.py`
- `tests/test_api_runtime_feedback_candidate_context_consumption.py`
- `tests/test_api_runtime_studio_feedback_overlay_state.py`
- `DEVLOG.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- this handoff
- external execution state YAML

## Contract 判断

`target_binding`、`scope_policy`、`conflict_summary` 是 existing feedback
candidate artifact contract 的 additive safe fields，不是 public route 或 OpenAPI
path。

本轮稳定边界：

- Feedback candidate is always project-scoped.
- Global scope, cross-project reuse, Company KB promotion, durable memory write, and provider calls remain false by default.
- Conflict detection is deliberately narrow: it only marks single-feedback signals. It does not claim cross-candidate conflict analysis or human review.
- Context overlay consumption may carry these summaries as local evidence, but provider prompt policy still keeps overlays out of provider prompts by default.

## 本轮改动

- Candidate builder now adds `target_binding`, `scope_policy`, and `conflict_summary`.
- Promotion decision and context overlay artifacts preserve those fields.
- Context resolver summaries, model-call context, and Studio-state persistence preserve those fields as bounded safe JSON.
- Tests now assert project-scoped binding, no-global promotion, cross-candidate check requirement, and mixed asset decision conflict signals.

## Provider Gate

Provider gate remained closed for this TaskRun.

- live LLM: not called
- live image: not called
- live video: not called
- live vision: not called
- live ASR: not called
- external download: not called

服务器 Runtime health、三端同步、master merge、deploy 均未执行。

## 验证

Focused/related contract set:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_feedback.py tests\test_api_runtime_feedback_candidate_promotion.py tests\test_api_runtime_feedback_candidate_context_overlay.py tests\test_api_runtime_feedback_candidate_context_consumption.py tests\test_api_runtime_studio_feedback_overlay_state.py tests\test_model_call_context_contract.py tests\test_api_runtime_keyframe_generation_bridge.py tests\test_api_runtime_openapi_snapshot.py -q
# 25 passed, 1 existing Starlette/httpx deprecation warning
```

Closeout:

```text
.\.venv\Scripts\python.exe -m pytest
# 738 passed, 520 deselected, 2 warnings

.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

npm.cmd run check:studio-js
# JS syntax check passed: 130 files

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; passed=3; warning=4
# existing warnings: legacy_frozen_surface=10, human_doc_chinese_coverage=22,
# secret_like_fragments=9, oversized_files=59

git diff --check
# passed, with existing CRLF normalization warning for apps/api/runtime_events.py

YAML parse check for external execution state
# yaml_parse_ok
```

## Evidence State

```text
structure_verified_feedback_candidate_scope_conflict_contract_full_local_verification_no_merge
```

这只是本地 deterministic feedback-governance evidence。它不是 provider smoke，不是 generated media evidence，不是 Runtime health verification，不是 server sync，不是 human creative acceptance，不是 business validation，也不是 durable memory promotion。

## Cleanup Review

- 没有新增 Runtime route、OpenAPI path、Studio fetch、provider adapter 或生成链路。
- All touched Python modules remain under 300 lines after this slice:
  `runtime_events` 223, `feedback_candidate_promotion` 171,
  `feedback_candidate_context_overlay` 157, `runtime_feedback_context` 283,
  `runtime_studio_state_context` 282, `model_call_context` 294.
- `model_call_context` is close to the 300-line ideal threshold. Future overlay/context additions should split a helper instead of adding fields in place.
- `docs/demo-docs-20260629/` 保持 untouched/untracked。

## Deferred Items

- Cross-candidate conflict analysis remains deferred; this task only records single-feedback conflict signals.
- If future taxonomy/scope review needs Studio controls, add a separate UI contract task.
- `AFS-T19 Authorized Master Merge + Three-End Sync` still requires explicit authorization.
- Provider smoke still requires separate capability authorization.

## Next Valid Task

```text
AFS-T19 Authorized Master Merge + Three-End Sync
```

只有在用户明确授权后才能执行 T19。若没有 T19 授权，应继续在 codex 分支选择下一个 provider-closed project-book slice.
