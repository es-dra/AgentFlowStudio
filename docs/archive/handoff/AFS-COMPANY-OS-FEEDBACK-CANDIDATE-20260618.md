---
doc_type: company_os_feedback_packet
status: candidate
session_date: 2026-06-18
confidentiality: internal
---

# Company OS 反馈包：AFS 核心算法与操作链路

本文记录 AFS Studio 核心技术框架对齐过程中产生的 Company OS 候选反馈。

这不是 active rule，也不自动晋升为长期规则。后续是否进入 Company OS 的
limited 或 active_review 状态，需要人工复核和下一轮实现证据。

## 1. 项目上下文

- 项目：AgentFlow Studio
- 仓库路径：`D:\Projects\AgentFlowStudio`
- 会话日期：2026-06-18
- 任务：澄清 AFS 核心智能体算法层和用户操作链路
- 工作模式：Strategic
- 项目内记录：`docs/architecture/AFS_CORE_ALGORITHM_AND_OPERATION_MAP.zh-CN.md`
- 保密级别：internal

## 2. 使用的 Company OS 上下文

| 来源 | 是否使用 | 说明 |
|---|---|---|
| AI-Native-Company-OS-MAP.md | 是 | 通过 AFS GFR 投影和项目规则层级使用。 |
| candidate-rule-ledger.md | 否 | 本次不直接更新候选规则账本。 |
| Harness-first rule | 是 | 保持算法、Runtime、provider、证据、人审边界分离。 |
| ai-native-company-workflow templates | 是 | 按反馈包模板沉淀候选证据。 |
| contracts / validator | 否 | 本次没有修改 contract 或 schema。 |

## 3. Harness 层映射

| ETCLOVG 层 | 是否触达 | 证据 |
|---|---|---|
| E - Execution | 是 | 当前分支集成和验证路线已执行。 |
| T - Tooling | 是 | Studio / Runtime / provider 边界继续保持明确。 |
| C - Context | 是 | 核心关注每次模型调用前的上下文智能调度。 |
| L - Lifecycle | 是 | 澄清 draft asset、fixed asset、feedback 与下一轮复用关系。 |
| O - Observability | 是 | safe manifest、trace、feedback 仍是证据，不是自动记忆。 |
| V - Verification | 是 | 验证、真人验收、商业验证继续分离。 |
| G - Governance | 是 | provider gate 与 COS 晋升边界继续显式化。 |

## 4. 产出证据

| Artifact | 路径 | 状态 |
|---|---|---|
| strategy evidence | `docs/architecture/AFS_CORE_ALGORITHM_AND_OPERATION_MAP.zh-CN.md` | draft |
| routing trace | `docs/GFR_EXECUTION_PROJECTION.md` | verified existing projection |
| quality report | 本次终端验证输出 | verified |
| memory candidate | 本反馈包 | draft |

## 5. 本项目产生的可复用经验

- 可复用经验：AI-native 内容生产产品的核心架构应围绕“模型调用前的智能准备”来定义，而不是围绕 provider 按钮或 UI 流程节点来定义。
- 发现或预防的问题：上一版算法地图把流程编排、provider gate、artifact lineage、action routing 等对象过度计入核心算法层。修正后，核心算法只保留会选择、归纳、改写、约束、裁剪、排序或投影模型调用输入的模块。
- 起作用的规则：GFR 的 evidence / feedback 边界防止讨论草案被直接晋升为 Company OS active rule。
- 仍不够清晰的规则：AFS 需要稳定命名并 contract 化“模型调用准备内循环”，包括上下文调度、提示词优化、视觉理解、请求投影、资产记忆和漂移反馈。
- 不应晋升为公司规则的项目细节：AFS 具体文件名、Studio 面板、provider 细节和当前 UI 实现方式。

## 6. 候选反馈

| 反馈类型 | 目标 | 候选动作 |
|---|---|---|
| workflow_update | GFR / AI-native 项目启动框架 | keep_candidate |
| memory_candidate | Company memory candidate | keep_candidate |
| template_update | 未来 AI 项目架构图谱模板 | keep_candidate |

候选表述：

```text
对 AI-native 生成类产品，判断一个模块是否属于核心算法层，应看它是否会
选择、归纳、改写、约束、调度、评分或投影模型调用输入。

单纯 job 编排、provider gate、artifact manifest、UI action 不应被归类为
核心智能体算法。
```

## 7. 路由决策

按以下规则路由：

```text
10-Startup/80-Workflow/ai-native-company-workflow/feedback-routing.md
```

已选择目的地：

- [x] Project-local DEVLOG / HANDOFF / BACKLOG
- [x] Company memory candidate
- [ ] Candidate rule ledger
- [ ] Workflow template update
- [ ] Contract/schema update
- [ ] Strategy evidence
- [ ] No Company OS update needed

## 8. 人工复核门槛

- Reviewer：human owner pending
- Review date：pending
- Decision：keep_candidate
- Reason：该架构口径有复用价值，但还需要后续实现和重复使用证据，才能进入 limited 或 active_review。
- Next validation task：定义并验证 AFS 统一模型调用 request context contract。

## 9. 声明边界

- 已验证：项目内已经有一份讨论草案，记录修正后的算法图谱和操作链路口径。
- 仅推断：该口径适合作为其他 AI-native 项目的长期 Company OS 规则。
- 需要用户验收：最终算法分类和用户核心操作链路。
- 需要商业验证：该架构是否提升生产效率、内容质量或留存。
- 不得写入公开项目仓库：私有战略、provider secret、真实客户材料、真实成本、未公开商业判断。
