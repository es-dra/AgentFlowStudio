# AFS TaskRun - 反馈 Overlay Prompt Approval Gate - 2026-06-30

## 任务

Task ID: `AFS-T18c Feedback Overlay Prompt Authorization Design Gate`

分支: `codex/afs-project-book-full-goal-20260630`

起始 HEAD: `d1c8f509ab62b43573b8af938ec8f1602723679a`

状态: 已实现；focused 验证、相关验证、Studio JS、CLI、全量 pytest、提交、push 和分支 preflight 已完成。

## 中文摘要

T17b 已证明：即使 Studio 选择了某个 feedback overlay，它也只停留在本地 context evidence，不会进入 `keyframe_request_plan.provider_prompt` 或 `model_request_plan.provider_request.prompt`。T18b 已把这条 prompt policy 显示到 Studio review surface。T18c 的最小切片是在同一个安全 policy 对象里加入结构化的 `prompt_provider_gate`，让未来“是否允许 overlay 文本进入 provider prompt”有明确的阻断合同。

代码里没有使用可持久化字段名 `authorization`。原因是 Studio state 的通用 sanitizer 会拒绝这个安全敏感词，这是既有安全边界。本轮保留这个边界，用 `prompt_provider_gate`、`requires_human_approval`、`gate_record_ref` 表达同一审批含义，而不是放宽 sanitizer。

本轮没有打开 provider gate，没有执行 prompt 注入，没有新增 Runtime route，没有更新 OpenAPI path，没有生成媒体，没有 merge `master`，没有部署或服务器同步，没有 Runtime health 核验，也没有声明人类创意验收、业务验证、durable memory 或 Company KB 写入。

## Dirty Ownership Ledger

| Surface | Ownership | Handling |
|---|---|---|
| `agentflow/algorithms/feedback_overlay_prompt_policy.py` | T18c 共享 policy contract | 新增默认阻断的 `prompt_provider_gate`。 |
| `apps/api/runtime_studio_state_context.py` | T18c Studio state sanitizer | 新增嵌套白名单；没有放宽 forbidden-key 检查。 |
| `apps/studio/src/feedback-context-overlays.js` | T18c Studio helper | 只读规范化 `prompt_provider_gate`，不触发 fetch 或 provider。 |
| `tests/test_api_runtime_feedback_candidate_context_consumption.py` | T18c Runtime 传播回归 | 覆盖 context bundle、model context、request plan、safe manifest、generation bridge。 |
| `tests/test_api_runtime_studio_feedback_overlay_state.py` | T18c state 持久化回归 | 覆盖安全 gate 字段保存和嵌套危险字段裁剪。 |
| `tests/test_web_studio_feedback_candidate_static.py` | T18c Studio 静态回归 | 覆盖 helper local-only、无 provider gate/env 依赖。 |
| `DEVLOG.md`, `TASK_TRACKER.md`, `docs/handoff/INDEX.md` | T18c 项目记录 | 本轮更新。 |
| external execution state YAML | T18c 执行状态 | 最小更新，仅记录 AFS 项目包状态。 |
| `docs/demo-docs-20260629/` | 既有 untracked do-not-touch | 未触碰、未 stage、未清理。 |

## 读取范围

- `AGENTS.md`
- `docs/company_operating_model.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- 最新 goal-mode execution prompt
- `docs/handoff/AFS-FEEDBACK-OVERLAY-PROMPT-POLICY-REVIEW-SURFACE-20260630.md`
- external execution state YAML
- feedback overlay policy/helper/state/runtime 传播代码
- 相关 Runtime、Studio state、Studio static 测试

## 写入范围

- `agentflow/algorithms/feedback_overlay_prompt_policy.py`
- `apps/api/runtime_studio_state_context.py`
- `apps/studio/src/feedback-context-overlays.js`
- `tests/test_api_runtime_feedback_candidate_context_consumption.py`
- `tests/test_api_runtime_studio_feedback_overlay_state.py`
- `tests/test_web_studio_feedback_candidate_static.py`
- 本 handoff
- `DEVLOG.md`
- `TASK_TRACKER.md`
- `docs/handoff/INDEX.md`
- external execution state YAML

## Contract 判断

当前合同保持不变：`feedback_context_overlays` 是本地安全 context evidence，不是 provider prompt 文本。

`feedback_context_overlay_prompt_policy` 现在同时记录：

- `provider_prompt_includes_context_overlays=false`
- `prompt_provider_gate.status=blocked_by_default`
- `prompt_provider_gate.provider_prompt_inclusion_allowed=false`
- `prompt_provider_gate.requires_human_approval=true`
- `prompt_provider_gate.requires_provider_gate=true`
- `prompt_provider_gate.requires_prompt_budget_review=true`
- `prompt_provider_gate.requires_safety_filter=true`

这只是 design/contract gate，不是 prompt inclusion 实现。Studio 可以读取安全摘要，但仍然没有 UI 命令、Runtime route、OpenAPI operation、request projection 或 provider adapter 路径会把 feedback overlay 文本注入 provider prompt。

## 安全边界

- remote provider gates 对本轮任务仍视为关闭。
- 没有 live LLM/image/video/vision/ASR 调用。
- 首次 focused run 发现：如果把 `authorization` 作为可持久化字段写入 Studio state，会触发 forbidden-key guard。最终修复是保留 guard，并改用 approval/gate 字段。
- Studio state 只保存安全 gate 白名单字段，仍然裁剪 `provider_raw`、signed URL、local path、media bytes。
- Studio helper 仍是 local-only：无 `fetch(`，无 overlay 创建调用，无 `AFS_ALLOW_REMOTE` 依赖。

## 验证

Focused:

```text
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_feedback_candidate_context_consumption.py::test_selected_feedback_overlay_stays_out_of_provider_prompt_and_records_policy tests\test_api_runtime_studio_feedback_overlay_state.py tests\test_web_studio_feedback_candidate_static.py -q
# 10 passed, 1 existing Starlette/httpx deprecation warning

.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_feedback_candidate_context_consumption.py tests\test_api_runtime_studio_feedback_overlay_state.py tests\test_web_studio_feedback_candidate_static.py tests\test_api_runtime_studio_state.py tests\test_api_runtime_studio_state_persistence.py tests\test_model_call_context_contract.py tests\test_api_runtime_keyframe_generation_bridge.py -q
# 37 passed, 1 existing Starlette/httpx deprecation warning

npm.cmd run check:studio-js
# JS syntax check passed: 130 files
```

Closeout:

```text
.\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

.\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

.\.venv\Scripts\python.exe -m pytest
# 737 passed, 520 deselected, 2 warnings

.\.venv\Scripts\python.exe tools\maintenance_audit.py
# status=warning; failed=0; passed=3; warning=4
# existing warnings remain: legacy_frozen_surface=10,
# human_doc_chinese_coverage=22, secret_like_fragments=9,
# oversized_files=59

git diff --check
# passed

YAML parse check for external execution state
# yaml_parse_ok

git commit
# 98ca7477964fe9bb428ca0343e6c4d20dc224865

git push origin codex/afs-project-book-full-goal-20260630
# pushed to origin/codex/afs-project-book-full-goal-20260630

.\.venv\Scripts\python.exe tools\afs_goal_mode_branch_integration_review.py --report runs\goal_mode_branch_integration_review_t18c_post_push.json
# status=ready_for_human_merge_review; blocker_count=0
```

## Evidence State

```text
structure_verified_feedback_overlay_prompt_approval_gate_pushed_branch_preflight_ready_no_merge
```

这只是本地 deterministic Runtime/Studio contract evidence。它不是 provider smoke，不是 generated media evidence，不是 Runtime health verification，不是 server sync，不是 human creative acceptance，不是 business validation，也不是 durable memory promotion。

## Cleanup Review

- 没有新增 Runtime route 或 OpenAPI path。
- 没有创建第二套 feedback overlay subsystem。
- `runtime_studio_state_context.py` 当前正好 300 行；后续再加 context policy 字段前应先拆 helper。
- `feedback-context-overlays.js`、`tests/test_api_runtime_feedback_candidate_context_consumption.py` 仍低于 300 行 warning 阈值。
- `docs/demo-docs-20260629/` 保持 untouched/untracked。

## Deferred Items

- 未来若真的允许 feedback overlay 文本进入 provider prompt，仍需要单独 UI、Runtime gate、policy record、prompt budget、安全过滤、provider-gated tests 和用户明确授权。
- 如需继续扩展 Studio state context policy，应先拆分 `runtime_studio_state_context.py`，避免新增维护债。
- `AFS-T19 Authorized Master Merge + Three-End Sync` 仍需要明确授权。
- Provider smoke 仍需要单独能力授权。

## Next Valid Task

```text
AFS-T19 Authorized Master Merge + Three-End Sync
```

只有在用户明确授权后才能执行 T19。若没有 T19 授权，应继续在 codex 分支选择下一个 provider-closed project-book slice。
