# AFS TaskRun - Studio State Feedback Policy Sanitizer Split - 2026-06-30

## 任务

Task ID: `AFS-T18d Studio State Feedback Policy Sanitizer Split`

分支: `codex/afs-project-book-full-goal-20260630`

起始 HEAD: `98ca7477964fe9bb428ca0343e6c4d20dc224865`

状态: 已实现；focused 验证、本地 closeout 验证、commit、push 和 branch preflight 均已完成。

## 中文摘要

T18c 把 `apps/api/runtime_studio_state_context.py` 推到正好 300 行。根据项目维护规则，继续往这个文件叠加 context/policy 字段会直接进入新的维护债。T18d 的最小切片是把 feedback overlay prompt policy 的 Studio-state sanitizer 拆到独立 helper：

```text
apps/api/runtime_studio_state_feedback_policy.py
```

拆分后 `runtime_studio_state_context.py` 从 300 行降到 248 行，新 helper 84 行。行为不变：Studio state 仍只保存 `feedback_context_overlay_prompt_policy` 和 `prompt_provider_gate` 的安全白名单字段，仍然由原 `_text` 入口拒绝 local path/runtime artifact path。

本轮同时修正 T18c handoff 的过时状态：T18c 实际已提交、push，并通过 branch preflight。

## Dirty Ownership Ledger

| Surface | Ownership | Handling |
|---|---|---|
| `apps/api/runtime_studio_state_feedback_policy.py` | T18d 新 helper | 保留；单一职责为 feedback overlay prompt policy 的 Studio-state 白名单化。 |
| `apps/api/runtime_studio_state_context.py` | T18d 拆分源文件 | 保留；只负责 context bundle 主体和通用 `_text`/`_number`。 |
| `tests/test_api_runtime_studio_state_modules.py` | T18d 模块边界回归 | 更新；把新 helper 纳入 <=300 行和 route-helper split guard。 |
| `docs/handoff/AFS-FEEDBACK-OVERLAY-PROMPT-APPROVAL-GATE-20260630.md` | T18d 记录纠偏 | 修正 T18c 已 commit/push/preflight ready 的事实。 |
| `DEVLOG.md`, `TASK_TRACKER.md`, `docs/handoff/INDEX.md` | T18d 项目记录 | 本轮更新。 |
| external execution state YAML | T18d 执行状态 | 最小更新，仅记录 AFS 项目包状态。 |
| `docs/demo-docs-20260629/` | 既有 untracked do-not-touch | 未触碰、未 stage、未清理。 |

## 读取范围

- `AGENTS.md`
- `docs/company_operating_model.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- `docs/handoff/AFS-FEEDBACK-OVERLAY-PROMPT-APPROVAL-GATE-20260630.md`
- external execution state YAML
- `AFS-Task-Ledger-v0.1.md`
- `AFS-AI-Execution-Spec.yaml`
- Studio state sanitizer modules and tests

## 写入范围

- `apps/api/runtime_studio_state_feedback_policy.py`
- `apps/api/runtime_studio_state_context.py`
- `tests/test_api_runtime_studio_state_modules.py`
- `docs/handoff/AFS-FEEDBACK-OVERLAY-PROMPT-APPROVAL-GATE-20260630.md`
- 本 handoff
- `DEVLOG.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- external execution state YAML

## Contract 判断

这是维护性拆分，不是新 Runtime/Studio contract。外部可见行为保持：

- `feedback_context_overlay_prompt_policy` 仍从 `lastContextBundle` 进入 Studio state 安全摘要。
- `prompt_provider_gate` 仍是默认 blocked 的安全子对象。
- `provider_raw`、signed URL、local path、media bytes 等危险字段仍不能进入持久化 state。
- 没有新增 Runtime route、OpenAPI path、Studio fetch、provider gate 或 prompt injection 路径。

## 验证

Focused:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_studio_state_modules.py tests\test_api_runtime_studio_feedback_overlay_state.py tests\test_api_runtime_studio_state.py tests\test_api_runtime_studio_state_persistence.py -q
# 19 passed, 1 existing Starlette/httpx deprecation warning
```

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
structure_verified_studio_state_feedback_policy_sanitizer_split_pushed_branch_preflight_ready_no_merge
```

这只是本地 deterministic maintenance/contract evidence。它不是 provider smoke，不是 generated media evidence，不是 Runtime health verification，不是 server sync，不是 human creative acceptance，不是 business validation，也不是 durable memory promotion。

## Cleanup Review

- `runtime_studio_state_context.py` 已从 300 行降到 248 行。
- 新 helper `runtime_studio_state_feedback_policy.py` 为 84 行，低于维护 warning 阈值。
- 没有复制 `_text` 的 local-path 检查；新 helper 通过依赖注入复用原 sanitizer 边界。
- 没有新增重复 route/schema/component/provider path。
- `docs/demo-docs-20260629/` 保持 untouched/untracked。

## Deferred Items

- 若继续扩展 Studio state context bundle，应优先在现有拆分 helper 内按职责扩展，不再回填到 `runtime_studio_state_context.py`。
- `AFS-T19 Authorized Master Merge + Three-End Sync` 仍需要明确授权。
- Provider smoke 仍需要单独能力授权。

## Next Valid Task

```text
AFS-T19 Authorized Master Merge + Three-End Sync
```

只有在用户明确授权后才能执行 T19。若没有 T19 授权，应继续在 codex 分支选择下一个 provider-closed project-book slice。
