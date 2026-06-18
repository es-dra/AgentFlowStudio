# AFS Algorithm Library 架构说明

日期：2026-06-18

## 定位

AFS 不是 provider UI，也不是把多个模型按钮拼在一个页面里。AFS 的核心是
Agent-native 内容生产操作层：用户在 Studio 显式操作，Runtime 负责安全边界与
artifact，`agentflow/algorithms/` 负责可测试、可复用、可迭代的智能体算法。

本轮算法库口径已经从“流程模块清单”调整为“模型调用前后的智能选择、归纳、
改写、约束、调度、投影和反馈控制”。因此：

- `provider_gate_manifest` 是工程护栏和 safe manifest，不是核心智能体算法。
- `artifact_lineage` 是证据设施，不是核心智能体算法。
- `skill_action_selection` 是未来自动化路由候选，不是当前内容生产核心算法。
- `storyboard_breakdown` 是未来高价值候选算法，但尚未进入当前六大实现层。

## 核心算法总表

| 核心算法 | 当前模块 / 落点 | 输入 | 输出 | 失败模式 | 证据边界 |
|---|---|---|---|---|---|
| 提示词智能优化 | `apps/api/runtime_prompt_memory_engine.py`, `creative_intent_control` | `ModelCallContext`, 专家知识库, 资产, 用户偏好, provider constraints | canonical prompt, prompt sections, provider prompt candidates, safe trace | missing intent, unsafe prompt, constraint conflict | prompt 是创作语义，不是 provider raw |
| 上下文智能调度 | `agentflow/algorithms/context_resolver/` | fixed assets, graph subgraph, upstream refs, exclusions, locks, visible prompt | context bundle, text channel, reference channel, included/excluded assets | invalid subgraph, draft rejected, budget truncated | 只读取 fixed asset memory |
| 图片/视频智能识别 | `agentflow/algorithms/visual_understanding/`, `asset_card_drafting` | safe media refs, provider/local vision observation, project need | normalized observation, draft asset card | missing safe ref, unsupported asset type, unsafe observation | draft evidence, 不写 fixed asset |
| 资产记忆与连续性约束 | `agentflow/algorithms/fixed_asset_memory/` | fixed/draft/rejected/retired assets, locks, exclusions | context-eligible fixed assets, blocked locks, continuity policy | draft pollution, unsafe projection, missing signature | 只有人工确认 safe fields 进入后续上下文 |
| 模型请求投影 | `agentflow/algorithms/request_projection/` | `ModelCallContext`, canonical brief, provider constraints | provider-neutral request plan, provider request body | unsupported target, missing context id, unsafe request | request plan only，不执行 provider |
| 质量反馈与漂移控制 | `quality_feedback_scoring`, `revision_drift_control` | raw feedback, generated refs, preserve/change intent | sanitized evidence, bounded scores, revision drift plan | unknown metric, unsafe text, preserve/change conflict | feedback 是 evidence，不是 memory |

## 新的统一入口

所有模型调用前都应能构建 `ModelCallContext`：

```text
project / node / user intent
-> ModelCallContext
-> context resolver
-> prompt optimization or request projection
-> provider gate / adapter
-> safe result
-> visual understanding / feedback
-> next ModelCallContext
```

当前 Runtime 已接入：

- `POST /projects/{project_id}/prompt-optimizations`
  - 写出 `model_call_context.json`
  - response 暴露 `model_call_context_id`
- `POST /projects/{project_id}/keyframe-generations`
  - 写出 `model_call_context.json`
  - 写出 `model_request_plan.json`
  - 旧 `keyframe_request_plan.json` 引用同一个 `model_call_context_id`
- `POST /projects/{project_id}/video-generations`
  - 写出 `model_call_context.json`
  - 写出 `model_request_plan.json`
  - safe manifest 引用同一个 `model_call_context_id`
- `POST /projects/{project_id}/asset-card-drafts`
  - 写出 `visual_inspect` 的 `model_call_context.json`
  - 写出 `visual_understanding_observation.json`
  - 输出仍为 draft asset card，不自动污染 fixed asset memory
- `POST /projects/{project_id}/video-revisions`
  - 写出 `revision_plan.json`
  - 写出 `model_call_context.json`
  - 写出 `model_request_plan.json`
  - 当前 provider/feature flag 仍按 gate 阻断，算法 evidence 先行

## 辅助层

| 对象 | 定位 | 为什么不是核心算法 |
|---|---|---|
| `provider_gate_manifest` | provider gate 和 safe manifest | 控制能不能调用 provider，不决定创作内容 |
| `artifact_lineage` | 证据和追溯设施 | 记录来源关系，不做智能调度或投影 |
| `skill_action_selection` | 后续自动化路由候选 | 当前主要是安全 action label，不参与内容生成核心 |

## 安全与非声明

- Provider gates 默认关闭。
- Runtime verification 不是 human acceptance。
- Provider smoke 不是 business validation。
- Feedback 是 raw evidence，不自动成为 memory。
- Candidate memory 不是 durable memory。
- Repo 只保存执行投影；Company OS 经验只能走 candidate/limited 流程。
