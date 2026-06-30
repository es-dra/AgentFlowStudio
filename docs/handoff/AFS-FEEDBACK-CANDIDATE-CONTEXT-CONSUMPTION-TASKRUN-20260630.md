# AFS TaskRun - Feedback Candidate Context Resolver Consumption - 2026-06-30

## 任务

Task ID：`AFS-T15d Feedback Candidate Context Resolver Consumption Harness`

分支：`codex/afs-project-book-full-goal-20260630`

起始 HEAD：`6bffc18a6eceeabcf45733ddfd4c87e85a84cd80`

状态：已实现，已通过本地 focused 验证和提交前完整验证；提交、push、push 后分支 preflight 在本记录更新后执行。

## 中文摘要

本轮继续 project-book goal mode，但没有执行 `master` 合并、服务器三端同步、Runtime 重启、Runtime health 核验或 provider smoke。`AFS-T19 Authorized Master Merge + Three-End Sync` 仍需要用户明确授权。

T15a 已经把 Runtime `/feedback` 记录为安全的 `feedback_candidate`。T15b 增加了人工 promotion decision。T15c 在人工允许后写出 `runtime_feedback_candidate_context_overlay` artifact。T15d 做的是下一步最小消费切片：让 Runtime context resolver 从项目 manifest 的 `feedback_refs` 读取这些安全 overlay artifact，并把它们作为 `feedback_context_overlays` 安全摘要挂到本地 context bundle。

这不是 provider prompt 注入，不是固定资产确认，不是长期记忆，不是 Company KB 规则，不是生成媒体，也不是人工创意验收或业务验证。它只是让“被人工允许进入下一轮本地上下文的反馈候选”可以被后续 keyframe preflight、model-call context、safe manifest 和 local generation bridge 一致地看见。

## Dirty Ownership Ledger

| Surface | Ownership | Handling |
|---|---|---|
| `apps/api/runtime_feedback_context.py` | T15d feedback overlay context helper | 保留；单职责读取 manifest/artifact，文件小于 300 行。 |
| `apps/api/runtime_context_resolver.py` | T15d resolver wrapper integration | 保留；在 core resolver 完成后追加安全 overlay 摘要。 |
| `apps/api/runtime_generation_preflight.py` | T15d preflight output/token digest | 保留；输出 overlay 摘要，并纳入 preflight token digest。 |
| `agentflow/algorithms/model_call_context/__init__.py` | T15d model-call feedback evidence | 保留；只记录 overlay ID/状态摘要，不复制长文本到 provider prompt。 |
| `agentflow/algorithms/generation_bridge/__init__.py` | T15d bridge context evidence | 保留；记录 overlay count/IDs。 |
| `apps/api/runtime_keyframe_payloads.py` | T15d keyframe safe manifest counts | 保留；记录 overlay count/IDs。 |
| `tests/test_api_runtime_feedback_candidate_context_consumption.py` | T15d focused regression | 保留；覆盖正常消费和坏 ref 忽略。 |
| `DEVLOG.md`, `TASK_TRACKER.md`, `docs/handoff/INDEX.md` | T15d 项目记录 | 保留。 |
| external execution state YAML | T15d 执行状态 | 最小更新，位于 Learning_notes 项目书目录。 |
| `docs/demo-docs-20260629/` | 既有 untracked do-not-touch | 未触碰、未 stage、未清理。 |

## 读取范围

- `AGENTS.md`
- `docs/company_operating_model.md`
- `TASK_TRACKER.md`
- `DEVLOG.md`
- `docs/handoff/INDEX.md`
- `docs/handoff/AFS-RUNTIME-FEEDBACK-CANDIDATE-CONTEXT-OVERLAY-TASKRUN-20260630.md`
- `apps/api/runtime_context_resolver.py`
- `apps/api/runtime_generation_preflight.py`
- `apps/api/runtime_keyframes.py`
- `apps/api/runtime_keyframe_payloads.py`
- `apps/api/runtime_keyframe_generation_bridge.py`
- `apps/api/runtime_feedback_candidate.py`
- `apps/api/runtime_store.py`
- `agentflow/algorithms/context_resolver/__init__.py`
- `agentflow/algorithms/model_call_context/__init__.py`
- `agentflow/algorithms/generation_bridge/__init__.py`
- Runtime feedback/context/keyframe/model-call 相关测试
- external execution state YAML

## 写入范围

- `apps/api/runtime_feedback_context.py`
- `apps/api/runtime_context_resolver.py`
- `apps/api/runtime_generation_preflight.py`
- `apps/api/runtime_keyframe_payloads.py`
- `agentflow/algorithms/model_call_context/__init__.py`
- `agentflow/algorithms/generation_bridge/__init__.py`
- `tests/test_api_runtime_feedback_candidate_context_consumption.py`
- 本 handoff
- `DEVLOG.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- external execution state YAML

## Contract 判断

Runtime context resolution 现在在 fixed asset context resolver 之后调用 `attach_feedback_context_overlays(...)`。该 helper 的边界是：

- 从 project manifest 的 `feedback_refs` 中读取反馈引用；
- 只选择 artifact type 为 `agentflow_runtime_feedback_candidate_context_overlay` 的 ref；
- 通过 `RuntimeStore.read_artifact(...)` 反查 artifact；
- 缺失、不可读、类型不符、scope 不符或安全边界不显式关闭的 overlay 都跳过；
- 必须确认 overlay 仍保持 provider call、durable memory、Company KB、provider raw、private link、absolute path、media bytes 全部关闭；
- 最多返回 5 条安全摘要；
- 按 manifest 顺序挂到 `context_bundle.feedback_context_overlays`；
- 在 `context_bundle.trace_summary` 中记录 overlay count 和 overlay IDs。

Keyframe preflight 会在顶层返回同一份 `feedback_context_overlays`，并把 overlay ID、candidate ID 和 decision effect 纳入 preflight token digest。这样 overlay 发生变化时，旧 preflight token 不会被静默复用。

Model-call context 会在 `feedback_context.context_overlays` 记录安全 ID/状态摘要，并在 `context_sources.feedback_context_overlay_count` 记录数量。它故意不把 overlay intent 长文本写进 provider prompt policy。

Keyframe safe manifest 和 local generation bridge 记录 overlay count/IDs，方便后续审计。

## 安全边界

本轮没有做以下事项：

- 没有新增或删除 Runtime route；
- 没有更新 OpenAPI snapshot；
- 没有改 Studio UI；
- 没有写 durable memory 或 Company KB；
- 没有把反馈提升为 COS active rule；
- 没有把 feedback overlay 放进 `included_assets`、`reference_image_channel` 或 `subject_reference_asset_id`；
- 没有调用 live LLM/image/video/vision/ASR provider；
- 没有生成媒体字节；
- 没有 merge `master`、deploy、server sync、Runtime restart 或 Runtime health check。

OpenAPI path count 保持 52。

## 验证

红测基线：

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_feedback_candidate_context_consumption.py -q
# 2 failed as expected because feedback_context_overlays were not attached.
```

Focused green：

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_feedback_candidate_context_consumption.py -q
# 2 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_feedback.py tests\test_api_runtime_feedback_candidate_promotion.py tests\test_api_runtime_feedback_candidate_context_overlay.py tests\test_api_runtime_feedback_candidate_context_consumption.py tests\test_api_runtime_context_resolver.py tests\test_api_runtime_context_resolver_asset_card_candidates.py tests\test_api_runtime_keyframe_generation_bridge.py tests\test_model_call_context_contract.py tests\test_model_call_context_runtime_routes.py -q
# 41 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_feedback.py tests\test_api_runtime_feedback_candidate_promotion.py tests\test_api_runtime_feedback_candidate_context_overlay.py tests\test_api_runtime_feedback_candidate_context_consumption.py tests\test_api_runtime_context_resolver.py tests\test_api_runtime_context_resolver_asset_card_candidates.py tests\test_api_runtime_keyframe_generation_bridge.py tests\test_model_call_context_contract.py tests\test_model_call_context_runtime_routes.py tests\test_api_runtime_openapi_snapshot.py -q
# 42 passed, 1 existing Starlette/httpx deprecation warning
```

Closeout verification：

```text
.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

.\.venv\Scripts\python.exe -m pytest
# 727 passed, 520 deselected, 2 warnings

npm.cmd run check:studio-js
# JS syntax check passed: 128 files

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning, failed=0, passed=3, warning=4
# existing warning families: legacy_frozen_surface, human_doc_chinese_coverage,
# secret_like_fragments, oversized_files

git diff --check
# passed

.\.venv\Scripts\python.exe -c "import yaml, pathlib; path=pathlib.Path(r'D:\Learning materials\Learning_notes\10-Startup\70-Projects\AI-Native-Project-Books\2026-06-30-COS-AFS-autonomous-project-book\AFS-Goal-Driven-Execution-State-v0.1.yaml'); yaml.safe_load(path.read_text(encoding='utf-8')); print('yaml_ok')"
# yaml_ok
```

维护审计说明：第一次 audit 发现本 handoff 英文占比过高，会被 `human_doc_chinese_coverage` 计为新增 warning；随后已把本 handoff 改为中文主文档，避免新增人类文档中文覆盖率债务。

## Evidence State

```text
structure_verified_runtime_feedback_candidate_context_consumption_full_local_verification
```

这只是本地 deterministic Runtime/context evidence。它不是 provider smoke，不是 generated media evidence，不是 Runtime health verification，不是 server sync，不是 human creative acceptance，不是 business validation，也不是 durable memory promotion。

## Cleanup Review

- 新增一个小 helper，而不是把 manifest/artifact 扫描塞进现有 context resolver wrapper 或 oversized keyframe 模块。
- 新增代码和测试都低于 300 行理想阈值。
- 复用既有 project manifest `feedback_refs`，没有新增 manifest schema 字段。
- 没有新增第二套 feedback subsystem，也没有复用 legacy production-memory overlay 模块。
- 没有触碰或 stage `docs/demo-docs-20260629/`。

## Deferred Items

- Provider prompt 如何消费 promoted feedback overlay 仍暂缓；本轮只做安全 model-call feedback evidence。
- Studio UI 中如何审阅、选择、应用 context overlay 仍暂缓。
- `AFS-T19 Authorized Master Merge + Three-End Sync` 仍需要用户明确授权。
- Provider smoke 仍需要单独的能力授权。

## Next Valid Task

```text
AFS-T12/T15e Studio Feedback Overlay Review Surface
```

可选授权任务：

```text
AFS-T19 Authorized Master Merge + Three-End Sync
```
