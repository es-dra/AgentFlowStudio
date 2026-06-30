# AFS TaskRun - Runtime Feedback Candidate Contract - 2026-06-30

## Task

Task ID: `AFS-T15a Runtime Feedback Candidate Contract`

Branch: `codex/afs-project-book-full-goal-20260630`

Start HEAD: `5b0c15951d931e872f39164b1bae29c4cd8dc56a`

Status: implemented and locally verified; pending commit, push, and post-push
branch preflight at time of writing.

## Summary

## 中文摘要

本轮不是合并 `master`，也不是服务器三端同步；这些动作仍然需要单独的人类授权。当前选择的是一个低风险的本地确定性切片：把现有 Runtime `/feedback` 返回的反馈事件补成可追踪的候选反馈合同。原来的 `/feedback` 已经会清洗 Studio 质量反馈、写入 `runtime_feedback_event` artifact、写入 run trace，并把反馈事件加入项目 manifest 的 `feedback_refs`。缺口在于：后续开发者只能看到“这里有一条反馈”，但不能稳定判断这条反馈是否只是候选证据、是否默认禁止进入上下文覆盖、是否禁止写长期记忆、是否需要单独的人类提升决定。本轮新增的 `feedback_candidate` 就是为了解决这个合同漂移风险。

新的候选对象只保存安全摘要：来源反馈 ID、项目 ID、候选范围、安全目标引用、评分数量、决策数量、是否有备注，以及明确的 false 边界。它不会复制 provider 原始响应、私有外链、本地绝对路径、媒体字节或生成素材。`promotion_status` 固定为 `candidate_only`，`promotion_blocked_by_default=true`，`requires_human_promotion_decision=true`，并且 `eligible_for_context_overlay=false`、`eligible_for_durable_memory=false`。这意味着反馈可以被后续人工审查任务引用，但不会因为被记录下来就自动变成上下文、记忆、公司知识库规则、创作验收或业务验证结论。

工程上，本轮没有新增路由、没有新增 Studio UI、没有改 OpenAPI path、没有打开 provider gate，也没有部署或检查服务器 Runtime。实现放在既有 `runtime_events.py` 中，避免新增一套平行反馈系统；测试扩展在既有 `test_api_runtime_feedback.py` 中，避免为一个字段合同创建过重的测试文件。全量 pytest 曾经暴露过一次字段命名问题：安全字段如果包含项目禁用的 `signed_url` 字面量，会导致 artifact 读取被安全扫描拦截。已经改为 `external_private_link_stored=false` 等既有安全命名风格，并用 internal beta 验收相关测试确认该问题修复。

This slice continues goal-mode engineering without running the authorized
master merge path. `AFS-T19 Authorized Master Merge + Three-End Sync` still
requires explicit human authorization, so this task stays on the codex branch
and tightens a local deterministic feedback contract instead.

Runtime `/feedback` already sanitized Studio quality feedback, wrote a
`runtime_feedback_event` artifact, and appended it to project `feedback_refs`.
The remaining contract gap was that the event did not explicitly say how the
feedback may become a future candidate while staying blocked from durable memory
or context promotion by default.

This task fixes that by adding a safe `feedback_candidate` summary to every
Runtime feedback event.

## Dirty Ownership Ledger

| Surface | Ownership | Handling |
|---|---|---|
| `apps/api/runtime_events.py` | T15a Runtime feedback candidate contract | Keep; extends the existing event builder instead of adding a parallel route. |
| `tests/test_api_runtime_feedback.py` | T15a focused regression | Keep; locks candidate-only, safe-target, and promotion-blocked fields. |
| `docs/handoff/AFS-RUNTIME-FEEDBACK-CANDIDATE-CONTRACT-20260630.md` | T15a TaskRun evidence | Keep. |
| `DEVLOG.md`, `TASK_TRACKER.md`, `docs/handoff/INDEX.md` | T15a records | Keep. |
| External execution state YAML | T15a state | Update minimally outside AFS git. |
| `docs/demo-docs-20260629/` | pre-existing untracked docs | Do not touch, do not stage, do not clean. |

## Read Scope

- `AGENTS.md`
- `docs/company_operating_model.md`
- `TASK_TRACKER.md`
- `DEVLOG.md`
- `docs/handoff/INDEX.md`
- `docs/handoff/AFS-FAST-FORWARD-MERGE-PREFLIGHT-GATE-20260630.md`
- `apps/api/runtime_service.py`
- `apps/api/runtime_events.py`
- `apps/api/runtime_models.py`
- `apps/api/runtime_artifacts.py`
- `apps/api/runtime_store.py`
- `agentflow/algorithms/quality_feedback_scoring/__init__.py`
- `apps/studio/src/quality-feedback.js`
- `apps/studio/src/runtime-client.js`
- `tests/test_api_runtime_feedback.py`
- `tests/test_api_runtime_service.py`
- `tests/test_api_runtime_openapi_snapshot.py`
- External execution state YAML

## Write Scope

- `apps/api/runtime_events.py`
- `tests/test_api_runtime_feedback.py`
- This handoff
- `DEVLOG.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- External execution state YAML

## Current Facts

- `/feedback` is already a public Runtime route and Studio uses it through
  `recordFeedback(feedback)`.
- `/feedback` already writes `runtime_feedback_event.json`, registers a
  `runtime_feedback_event` artifact, writes a run trace, writes a job, and
  appends the event to project `feedback_refs`.
- Studio quality feedback already avoids sending preview URLs, provider raw,
  local paths, media bytes, and prompt/result bodies. It sends safe refs,
  ratings, character counts, and sanitized drift notes.
- Runtime feedback sanitization already drops unknown metrics and unsafe fields,
  redacts URLs and local paths from note text, and keeps
  `feedback_is_memory=false`, `writes_long_term_memory=false`, and
  `writes_company_kb=false`.
- Before this task, the returned event did not carry a stable candidate summary
  that future context-overlay or promotion logic could depend on.

## Contract Judgment

The existing `/feedback` route remains the correct Studio-facing Runtime
boundary. This task does not add a new route or a second feedback system.

The new `feedback_candidate` object is a safe internal Runtime event contract
inside the public `/feedback` response and artifact payload. It is intentionally
not a durable memory record, not a context overlay, not Company OS feedback
promotion, and not human creative acceptance.

Minimum stable fields:

- `artifact_type=agentflow_runtime_feedback_candidate`
- `schema_version=runtime-feedback-candidate/v0.1`
- `algorithm_id=afs.runtime_feedback_candidate_contract.v0.1`
- `candidate_id`
- `source_feedback_id`
- `source_project_id`
- `candidate_scope`
- `safe_target`
- `safe_evidence_summary`
- `promotion_status=candidate_only`
- `promotion_blocked_by_default=true`
- `requires_human_promotion_decision=true`
- `eligible_for_context_overlay=false`
- `eligible_for_durable_memory=false`
- `provider_calls_started=false`
- `writes_long_term_memory=false`
- `writes_company_kb=false`
- safety false flags for provider raw, private external link, local path, and
  media bytes

## Changes

- Added `build_runtime_feedback_candidate(...)` to `apps/api/runtime_events.py`.
- Added `feedback_candidate` to `runtime_feedback_event(...)`.
- Added candidate non-claims and candidate-only promotion boundary.
- Extended `tests/test_api_runtime_feedback.py` to assert:
  - sanitized feedback payload remains unchanged,
  - candidate links back to the source feedback event,
  - candidate scope is `quality_feedback_candidate`,
  - only safe target refs and bounded evidence counts are copied,
  - promotion/context/memory/provider flags remain blocked,
  - project manifest `feedback_refs` still points at the feedback event.

## OpenAPI

No OpenAPI snapshot update was required.

- Path count remains unchanged.
- No new route was added.
- No request schema changed.
- `/feedback` response is currently an open object in the service schema, so the
  new event payload field is locked by focused Runtime tests and this TaskRun
  record rather than a generated component schema.

## Provider Gate State

No provider gate was opened or required by this task.

No live LLM, image, video, vision, ASR, external download, provider raw
response, private external link, local private media bytes, or generated media
bytes were read, written, emitted, or committed.

## Verification

Focused verification so far:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_feedback.py -q
# 1 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_service.py tests\test_api_runtime_openapi_snapshot.py -q
# 13 passed, 1 existing Starlette/httpx deprecation warning
```

First full-suite run:

```text
.\.venv\Scripts\python.exe -m pytest
# 5 failed, 713 passed, 520 deselected, 2 existing warnings
```

Root cause: the first candidate safety boundary used a field name containing a
forbidden artifact key fragment. Reading the feedback artifact then failed with
`invalid_artifact` during internal beta acceptance checks. The field was renamed
to the existing safe style:

```text
raw_provider_response_stored=false
external_private_link_stored=false
absolute_path_stored=false
media_bytes_stored=false
```

Regression after the fix:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_feedback.py tests\test_afs_internal_beta_acceptance.py tests\test_afs_internal_beta_human_review_record.py tests\test_afs_internal_beta_preflight_public_edge.py -q
# 19 passed, 1 existing Starlette/httpx deprecation warning
```

Closeout verification:

```text
.\.venv\Scripts\python.exe -m pytest
# 718 passed, 520 deselected, 2 existing warnings

npm.cmd run check:studio-js
# JS syntax check passed: 128 files

.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; passed=3; warning=4
# existing warnings remain: legacy_frozen_surface=10,
# human_doc_chinese_coverage=22, secret_like_fragments=9,
# oversized_files=59

git diff --check
# passed with CRLF normalization warning on apps/api/runtime_events.py

YAML parse check for AFS-Goal-Driven-Execution-State-v0.1.yaml
# yaml_parse_ok; current_task_id=AFS-T15a
```

## Evidence State

```text
structure_verified_runtime_feedback_candidate_contract
```

This is contract/runtime evidence only. It is not provider smoke, not generated
media evidence, not human creative acceptance, not business validation, not
durable memory promotion, not deployment verification, and not server
three-end sync.

## Cleanup Review

- Reused existing `/feedback` and `runtime_feedback_event(...)`.
- Did not add a new route, OpenAPI path, frontend state machine, provider
  adapter, generated media file, or parallel memory system.
- Kept the new event helper in `runtime_events.py`; the file remains under the
  300-line ideal threshold.
- Did not touch or stage `docs/demo-docs-20260629/`.

## Deferred Items

- A later human-authorized task must still handle `AFS-T19 Authorized Master
  Merge + Three-End Sync` if the branch should become the new master/server
  baseline.
- A later task may define a separate human promotion decision that converts a
  feedback candidate into a context overlay. This task deliberately blocks that
  by default.
- Provider smoke still requires explicit capability authorization and remains
  separate from feedback-candidate evidence.

## Next Valid Task

```text
AFS-T19 Authorized Master Merge + Three-End Sync
```

Alternative next local task if merge is still not authorized:

```text
AFS-T15b Feedback Candidate Promotion Decision Harness
```
