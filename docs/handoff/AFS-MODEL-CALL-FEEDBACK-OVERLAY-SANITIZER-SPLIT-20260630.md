# AFS TaskRun - Model Call Feedback Overlay Sanitizer Split - 2026-06-30

## 任务

Task ID: `AFS-T18e Model Call Feedback Overlay Sanitizer Split`

分支: `codex/afs-project-book-full-goal-20260630`

起始 HEAD: `e865237bc3d6f297e220a26138563ed501f20c90`

状态: 已实现；focused verification、全量 pytest、CLI、Studio JS、维护审计和 diff closeout 已通过；commit/push 作为本 TaskRun 最后步骤执行。

## 中文摘要

T15g 为 model-call feedback overlay summary 增加了 scope/conflict 安全字段，
把 `agentflow/algorithms/model_call_context/__init__.py` 推到 294 行。继续在这个
主模块上叠加 overlay 字段会直接制造新的维护债。本轮的最小切片是把 feedback
overlay summary sanitizer 从主模型上下文构建逻辑中拆到同包 helper：

```text
agentflow/algorithms/model_call_context/feedback_context.py
```

拆分后 `model_call_context/__init__.py` 从 294 行降到 228 行，新 helper 91 行。行为
保持不变：helper 通过依赖注入复用原 `_sanitize_text` 和 `_safe_ref_list`，所以
URL、credential、本地路径、provider raw 和 safe ref 归一化仍走原边界。

## Dirty Ownership Ledger

| Surface | Ownership | Handling |
|---|---|---|
| `agentflow/algorithms/model_call_context/feedback_context.py` | T18e new helper | 保留；单一职责为 model-call feedback overlay summary sanitizer。 |
| `agentflow/algorithms/model_call_context/__init__.py` | T18e split source | 保留；只负责 model-call context 主 payload 装配和通用 sanitizer。 |
| `tests/test_model_call_context_contract.py` | T18e boundary regression | 更新；覆盖 helper split 和 line-count guard。 |
| `DEVLOG.md`, `TASK_TRACKER.md`, `docs/handoff/INDEX.md` | T18e records | 本轮更新。 |
| external execution state YAML | T18e execution state | 最小更新，仅记录 AFS 项目包状态。 |
| `docs/demo-docs-20260629/` | 既有 untracked do-not-touch | 未触碰、未 stage、未清理。 |

## 读取范围

- `AGENTS.md`
- `docs/company_operating_model.md`
- `TASK_TRACKER.md`
- `docs/handoff/AFS-FEEDBACK-CANDIDATE-SCOPE-CONFLICT-CONTRACT-20260630.md`
- `agentflow/algorithms/model_call_context/__init__.py`
- `tests/test_model_call_context_contract.py`
- model-call context runtime route and feedback overlay consumption tests

## 写入范围

- `agentflow/algorithms/model_call_context/feedback_context.py`
- `agentflow/algorithms/model_call_context/__init__.py`
- `tests/test_model_call_context_contract.py`
- `DEVLOG.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- this handoff
- external execution state YAML

## Contract 判断

这是维护性拆分，不是新 Runtime/Studio contract。外部可见行为保持：

- `feedback_context.context_overlays` shape 不变。
- `feedback_context_overlay_prompt_policy` behavior 不变。
- `provider_prompt_includes_context_overlays=false` policy 不变。
- URL、credential、本地路径和 provider raw redaction 仍使用主模块原 sanitizer。
- 没有新增 Runtime route、OpenAPI path、Studio fetch、provider gate 或 prompt injection 路径。

## 本轮改动

- 新增 `bundle_feedback_context_overlays(...)` helper。
- `build_model_call_context(...)` 通过 dependency injection 调用 helper。
- 删除 `__init__.py` 内的 overlay-specific private helpers。
- 新增测试确保主文件不再定义 `_bundle_feedback_context_overlays`，且主文件/helper 均保持低于本轮 line-count guard。

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
.\.venv\Scripts\python.exe -m pytest tests\test_model_call_context_contract.py tests\test_model_call_context_runtime_routes.py tests\test_api_runtime_feedback_candidate_context_consumption.py tests\test_api_runtime_keyframe_generation_bridge.py tests\test_api_runtime_openapi_snapshot.py -q
# 19 passed, 1 existing Starlette/httpx deprecation warning
```

Closeout:

```text
.\.venv\Scripts\python.exe -m pytest
# 739 passed, 520 deselected, 2 warnings

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
# passed
```

## Evidence State

```text
structure_verified_model_call_feedback_overlay_sanitizer_split_full_local_verification_no_merge
```

这只是本地 deterministic maintenance/contract evidence。它不是 provider smoke，不是 generated media evidence，不是 Runtime health verification，不是 server sync，不是 human creative acceptance，不是 business validation，也不是 durable memory promotion。

## Cleanup Review

- `model_call_context/__init__.py` 已从 294 行降到 228 行。
- 新 helper `model_call_context/feedback_context.py` 为 91 行，低于维护 warning 阈值。
- 没有复制 URL、credential、本地路径 redaction 规则；helper 复用原 sanitizer boundary。
- 没有新增重复 route/schema/component/provider path。
- `docs/demo-docs-20260629/` 保持 untouched/untracked。

## Deferred Items

- 如果后续继续扩展 model-call feedback overlay summary，应优先在 `feedback_context.py` 内按职责扩展，不回填到 `model_call_context/__init__.py`。
- `AFS-T19 Authorized Master Merge + Three-End Sync` 仍需要明确授权。
- Provider smoke 仍需要单独能力授权。

## Next Valid Task

```text
AFS-T19 Authorized Master Merge + Three-End Sync
```

只有在用户明确授权后才能执行 T19。若没有 T19 授权，应继续在 codex 分支选择下一个 provider-closed project-book slice。
