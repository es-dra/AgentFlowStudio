# AFS TaskRun - Feedback Candidate Taxonomy Contract - 2026-06-30

## 任务

Task ID: `AFS-T15f Feedback Candidate Taxonomy Contract`

分支: `codex/afs-project-book-full-goal-20260630`

起始 HEAD: `a87b8f2f29c0e32c0f9d28fff86c2242be8decd3`

状态: 已实现；focused verification、全量 pytest、CLI、Studio JS、维护审计、diff/YAML closeout 已通过；commit/push 作为本 TaskRun 最后步骤执行。

## 中文摘要

T15 目标要求用户反馈能以 candidate/limited 形态沉淀，并且能够区分
character、scene、prop、style、shot、narrative、rhythm、provider、
generation failure 等反馈类别。此前 `/feedback` 已有安全 candidate、
promotion decision、context overlay、context resolver consumption 和 Studio
review surface，但候选没有明确 taxonomy，后续全量目标模式很容易把“反馈存在”
和“反馈能被治理”混在一起。

本轮新增最小安全合同：Runtime 反馈在 sanitizer 阶段生成受控
`feedback_taxonomy` ID 列表，并通过 candidate、promotion、overlay、context
resolver、model-call context 和 Studio state 持续保留这些安全 ID 与
`taxonomy_count`。这只是本地 deterministic feedback contract，不把反馈自动写入
durable memory 或 Company KB。

## Dirty Ownership Ledger

| Surface | Ownership | Handling |
|---|---|---|
| `agentflow/algorithms/quality_feedback_scoring/__init__.py` | T15f taxonomy source | 新增受控 taxonomy 枚举、metric/text/asset decision 分类。 |
| `apps/api/runtime_events.py` | T15f candidate propagation | `feedback_candidate` 记录 safe taxonomy 和 `taxonomy_count`。 |
| `agentflow/algorithms/feedback_candidate_promotion/__init__.py` | T15f promotion propagation | promotion decision 复制 safe taxonomy，不回读原始反馈。 |
| `agentflow/algorithms/feedback_candidate_context_overlay/__init__.py` | T15f overlay propagation | context overlay artifact 复制 safe taxonomy。 |
| `apps/api/runtime_feedback_context.py` | T15f context resolver summary | consumed overlay summary 保留 taxonomy 和 `taxonomy_count`。 |
| `agentflow/algorithms/model_call_context/__init__.py` | T15f model context summary | model-call context 保留 overlay taxonomy summary，不注入 provider prompt。 |
| `apps/api/runtime_studio_state_context.py` | T15f Studio-state sanitizer | Studio state 只白名单化 taxonomy ID 和 evidence summary count。 |
| `tests/test_api_runtime_feedback*.py`, `tests/test_api_runtime_studio_feedback_overlay_state.py` | T15f regression | 覆盖 taxonomy 生成、传播、持久化和安全边界。 |
| `DEVLOG.md`, `TASK_TRACKER.md`, `docs/handoff/INDEX.md` | T15f records | 本轮更新。 |
| `docs/handoff/AFS-STUDIO-STATE-FEEDBACK-POLICY-SANITIZER-SPLIT-20260630.md` | T18d record correction | 修正已完成 commit/push/preflight 的过期状态。 |
| external execution state YAML | T15f execution state | 最小更新，仅记录 AFS 项目包状态。 |
| `docs/demo-docs-20260629/` | 既有 untracked do-not-touch | 未触碰、未 stage、未清理。 |

## 读取范围

- `AGENTS.md`
- `docs/company_operating_model.md`
- `TASK_TRACKER.md`
- full goal-mode prompt attachment
- `AFS-Task-Ledger-v0.1.md`
- `AFS-Project-Book-v0.1.md`
- external execution state YAML
- Runtime feedback/candidate/promotion/context modules
- Model-call context and Studio-state context sanitizer
- Existing feedback, overlay, model context, OpenAPI snapshot tests

## 写入范围

- `agentflow/algorithms/quality_feedback_scoring/__init__.py`
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
- `docs/handoff/AFS-STUDIO-STATE-FEEDBACK-POLICY-SANITIZER-SPLIT-20260630.md`
- external execution state YAML

## Contract 判断

`feedback_taxonomy` 是 Runtime feedback candidate 的内部安全 contract，不是新的
OpenAPI route 或 Studio 生成能力。

本轮稳定边界：

- 分类值是受控安全 ID，不保存用户原文、provider raw、本地路径、signed URL 或媒体字节。
- `studio_quality_feedback` 根据白名单 metric、`target_change_success` 和 sanitized note 关键词生成 taxonomy。
- `studio_asset_graph_feedback` 根据 asset decision、label/note/locks 的 sanitized text 生成 taxonomy。
- generic runtime feedback 至少标记 `general`，防止没有分类的候选静默进入后续链路。
- `safe_evidence_summary.taxonomy_count` 只保存计数，不暴露原始证据。
- promotion/context overlay/context resolver/model-call context/Studio state 都只传播 safe taxonomy IDs。
- provider prompt policy 保持 `provider_prompt_includes_context_overlays=false`，taxonomy 不进入 provider prompt。

不公开 OpenAPI 的理由：本轮没有新增 route/path，也没有让 Studio 新增 fetch 或 UI 入口。它是现有 feedback artifact/candidate 结构内的 additive safe field，当前测试覆盖比 OpenAPI path 公开更贴近实际风险。

## 本轮改动

- 新增 `FEEDBACK_TAXONOMY_CATEGORIES` 与 deterministic 分类逻辑。
- `/feedback` 返回的 sanitized feedback 和 embedded `feedback_candidate` 现在包含 taxonomy。
- Promotion decision 和 context overlay artifact 保留 taxonomy，避免后续 promotion 审核丢失分类上下文。
- Context resolver consumed overlay、model-call context overlay summary 和 Studio state sanitizer 保留 taxonomy。
- 回归测试覆盖质量反馈、资产图反馈、promotion、context overlay、context consumption、model-call context 和 Studio-state persistence。
- 修正 T18d handoff 的过期状态文字。

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

Focused:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_feedback.py tests\test_api_runtime_feedback_candidate_promotion.py tests\test_api_runtime_feedback_candidate_context_overlay.py tests\test_api_runtime_feedback_candidate_context_consumption.py tests\test_api_runtime_studio_feedback_overlay_state.py -q
# 15 passed, 1 existing Starlette/httpx deprecation warning
```

Related contract set:

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
structure_verified_feedback_candidate_taxonomy_contract_full_local_verification_no_merge
```

这只是本地 deterministic feedback-contract evidence。它不是 provider smoke，不是 generated media evidence，不是 Runtime health verification，不是 server sync，不是 human creative acceptance，不是 business validation，也不是 durable memory promotion。

## Cleanup Review

- 没有新增 Runtime route、OpenAPI path、Studio fetch、provider adapter 或生成链路。
- 所有 touched Python files remain below the 300-line ideal threshold:
  `quality_feedback_scoring` 254, `runtime_events` 164,
  `feedback_candidate_promotion` 152, `feedback_candidate_context_overlay` 138,
  `runtime_feedback_context` 264, `runtime_studio_state_context` 262,
  `model_call_context` 275.
- 新增字段均为 additive safe summary，不破坏旧 artifact 读取；summary helpers 对旧 artifacts 中缺失 `taxonomy_count` 的情况保持兼容。
- `docs/demo-docs-20260629/` 保持 untouched/untracked。

## Deferred Items

- 如果后续 Studio 需要用户手动选择 taxonomy，应作为单独 UI contract task，不在本轮隐式新增。
- 如果 taxonomy 需要中文关键词或多语言分类，应先建 benchmark/corpus，避免临时关键词扩大误判面。
- `AFS-T19 Authorized Master Merge + Three-End Sync` 仍需要明确授权。
- Provider smoke 仍需要单独能力授权。

## Next Valid Task

```text
AFS-T19 Authorized Master Merge + Three-End Sync
```

只有在用户明确授权后才能执行 T19。若没有 T19 授权，应继续在 codex 分支选择下一个 provider-closed project-book slice。
