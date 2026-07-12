# AFS ModelCallContext 契约

日期：2026-06-18

本文定义 AFS Studio 每次模型调用前的统一内部契约。它是算法层入口，不是
普通 UI 字段，也不是 provider payload。Runtime 可以把它登记为 safe artifact，
Studio 只消费 `context_id`、safe summary 和 artifact ref。

## GFR 启动包

| 字段 | 本任务取值 |
|---|---|
| identity | Engineering Delivery Lead + Runtime/API Integrator + Rule Steward + QA Gatekeeper |
| task type | Deep contract / algorithm hardening |
| context pack | `engineering_delivery`, `afs_project`, `rule_steward` |
| write scope | `agentflow/algorithms/`, `apps/api/`, `tests/`, `docs/architecture/`, current project records |
| non-goals | SaaS 化、live provider smoke、human acceptance、business validation、durable memory promotion |
| provider gates | 全部默认关闭；本契约不授权任何 provider call |
| evidence | deterministic tests, safe artifacts, PR body or focused current program state |
| feedback route | repo 记录执行投影；COS 只走 candidate/limited，不自动 active |

## 契约定位

`ModelCallContext` 回答一个问题：

```text
这一次模型调用前，系统根据项目、节点、资产、上下文、用户偏好、专家知识、
provider 能力和反馈证据，准备把什么安全上下文提交给后续算法？
```

它位于以下链路中：

```text
用户意图
-> ModelCallContext
-> 上下文智能调度
-> 提示词智能优化或模型请求投影
-> provider gate / adapter
-> safe result / evidence
-> 视觉理解与资产卡草稿
-> fixed asset 或 feedback
-> 下一次 ModelCallContext
```

## 最小字段

| 字段 | 说明 |
|---|---|
| `schema_version` | 当前为 `afs_model_call_context.v0.1` |
| `context_id` | `mctx_*` 稳定安全摘要 id |
| `project_id` | 项目 id |
| `node_ref` | `node_id`, `node_type`, upstream refs |
| `operation_intent` | `prompt_optimize`, `image_generate`, `video_generate`, `visual_inspect`, `revision` |
| `generation_target` | `prompt`, `image`, `video`, `asset_card`, `revision` |
| `input_prompt` | 脱敏后的用户可见输入和字符统计 |
| `context_sources` | context bundle 是否存在、纳入/排除资产计数、上游引用计数 |
| `asset_context` | fixed/draft/rejected/retired 分组；只有 fixed 进入 `context_eligible_asset_ids` |
| `reference_context` | context bundle 与请求显式 refs 合并后的安全 reference image refs |
| `preference_context` | 用户偏好和命中的专家规则 id |
| `feedback_context` | sanitized feedback evidence；不是 memory |
| `provider_constraints` | capability、provider service、prompt limit、reference slots、required gate |
| `safety_boundary` | provider raw、credentialed URL、本地路径、media bytes、draft memory 全部禁止 |
| `outputs` | 后续 `context_bundle`, `canonical_brief`, `request_plan`, `safe_manifest` 引用占位 |
| `trace_summary` | 纳入/排除资产、warning、draft 拒绝、raw evidence 非 memory |

## Operation 映射

| `operation_intent` | 默认 `generation_target` | 主要后续算法 |
|---|---|---|
| `prompt_optimize` | `prompt` | 提示词智能优化 |
| `image_generate` | `image` | 上下文调度 + 请求投影 |
| `video_generate` | `video` | 上下文调度 + 请求投影 + 连续性约束 |
| `visual_inspect` | `asset_card` | 视觉理解资产化 |
| `revision` | `revision` | 质量反馈与漂移控制 |

## 六大算法边界

| 核心算法 | 当前落点 |
|---|---|
| 提示词智能优化 | `apps/api/runtime_prompt_memory_engine.py` 消费上下文，Runtime 写 `model_call_context.json` |
| 上下文智能调度 | `agentflow/algorithms/context_resolver/` 仍是最成熟锚点 |
| 图片/视频智能识别 | `agentflow/algorithms/visual_understanding/` 归一化观察，`asset_card_drafting` 生成 draft |
| 资产记忆与连续性约束 | `fixed_asset_memory.asset_continuity_context` 明确 fixed-only eligible |
| 模型请求投影 | `agentflow/algorithms/request_projection/` 生成 provider-neutral request plan |
| 质量反馈与漂移控制 | `quality_feedback_scoring` 与 `revision_drift_control` 输出下一次 context evidence |

## Runtime artifact

Prompt optimization 写出：

```text
model_call_context.json
creative_brief.json
prompt_assembly_trace.json
prompt_optimization_safe_manifest.json
```

Keyframe generation 写出：

```text
model_call_context.json
model_request_plan.json
keyframe_request_plan.json
keyframe_candidates_summary.json
keyframe_generation_safe_manifest.json
```

旧 `keyframe_request_plan.json` 保留兼容，但必须引用：

```text
model_call_context_id
model_request_plan_ref = model_request_plan.json
```

Video generation 写出：

```text
model_call_context.json
model_request_plan.json
video_generation_safe_manifest.json
task_state.json
```

`video_generation_safe_manifest.json` 必须引用：

```text
model_call_context_id
model_request_plan_ref = model_request_plan.json
```

Asset-card draft / visual inspect 写出：

```text
model_call_context.json
model_request_plan.json
visual_understanding_observation.json
asset_card_draft_safe_manifest.json
asset_card_draft.json
```

其中 `visual_understanding_observation.json` 是 draft evidence，不能自动写入 fixed asset。

Video revision 写出：

```text
revision_plan.json
model_call_context.json
model_request_plan.json
video_revision_safe_manifest.json
```

其中 `revision_plan.json` 来自漂移控制算法，作为下一次调用的 preserve/change evidence，
不是 human acceptance，也不是 provider 成功证明。

## 安全边界

`ModelCallContext` 不允许包含：

- provider raw response。
- secret、token、cookie、provider key。
- credentialed URL。
- 本地绝对路径。
- media bytes。
- signed provider URL 或 provider 原始下载地址。
- 未确认 draft asset 作为 context truth。
- 未确认 feedback 作为 durable memory。

## 验收测试

当前契约测试入口：

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_model_call_context_contract.py tests\test_model_call_context_runtime_routes.py -q
.\.venv\Scripts\python.exe -m pytest tests\test_algorithm_library_contracts.py -q
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_prompt_memory_loop.py -q
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_creative_agent_keyframes.py tests\test_api_runtime_asset_card_drafts.py tests\test_api_runtime_video_revisions.py -q
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_context_resolver.py -q
```

本契约通过的是 structure/runtime verification，不是 provider smoke、human
acceptance、business validation 或 durable memory promotion。
