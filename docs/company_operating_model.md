# AFS 公司运营模型执行投影

本文是 `10-Startup` 源头知识库在 AgentFlow Studio 仓库中的执行投影。它只保留项目开发需要的规则摘要，不复制公司私密战略、真实成本、客户信息、内部复盘或 secret。

源头知识库：

```text
D:\Learning materials\Learning_notes\10-Startup
```

## 规则层级

```text
10-Startup 源头知识库
  -> 全局 workflow skills
  -> AGENTS.md
  -> docs/company_operating_model.md
  -> TASK_TRACKER.md / branch handoff
  -> 当前任务
```

## 目录职责

| 层级 | 职责 |
|---|---|
| `10-Startup` | 公司源头规则、判断、候选记忆、战略、反模式、治理规则 |
| workflow skill | 从源头规则抽取的可执行流程 |
| AFS repo | 代码、测试、contract、runbook、handoff、执行投影 |
| worktree / branch | 某条开发线的实际变更 |
| Agent | 执行具体任务，不能自动晋升公司规则或商业结论 |

## 任务难度

| 模式 | 适用场景 | 执行形态 |
|---|---|---|
| Light | 小问题、只读扫描、单文件轻微修改 | 当前 checkout 可完成 |
| Standard | 普通功能、局部 bug、CLI/schema/docs | 一条开发线，必要时 worktree |
| Deep | 多模块、Runtime Service、Web、provider、架构、清理 | 维护账本、隔离分支、明确验证 |
| Strategic | 公司规则、产品方向、商业验证、记忆晋升 | Agent 只准备 evidence/candidate，人工决策 |

## 当前主线

当前目标是本地内测可用，不是 SaaS。

AFS 当前对外和对内主打主题是：

```text
Harness-first Agentic Delivery System
```

它在本项目中的含义是：用本地优先的工作台验证 Agent 项目交付方法，把提示词、上下文、工具、规则、执行轨迹、质量报告和反馈信号组织成可重复、可审计、可维护的项目执行闭环。

术语分工：

| 术语 | 在 AFS 中的用途 |
|---|---|
| AI-Native Company OS | 公司级总系统，源头在 `10-Startup`。 |
| Harness-first Agentic Delivery System | AFS 当前主打项目交付主题。 |
| Evidence-backed Context Runtime | 任务执行时的上下文装配层。 |
| Governed Memory / Memory OS | 记忆、候选经验和知识晋升子系统，不作为当前主标题。 |
| AgentFlow Studio | 第一条本地验证项目线。 |

核心对象：

```text
Task Brief
Project Prefix
Context Bundle
Prompt / Skill Pack
Execution Router
Tool Contract
Run Trace
Quality Report
Feedback Signal
Memory Candidate
Promotion Ledger
```

已具备：

- deterministic Production Memory asset loop。
- read-only Web Memory Workbench。
- Asset Profile Review Screen。
- Real Asset Test Run Harness。
- Two-Round Context Runtime Validation。
- Project Manifest v0.1。
- Provider Validation Gate。
- Runtime Service v0.1。

下一步重点：

- 维护性重置与中文化。
- Runtime Service v0.2。
- OpenAPI / 前端 client 对接。
- 前端画布工作台接入。
- provider gate 继续保持默认 blocked。

## Worktree 政策

默认分支前缀：

```text
codex/
```

默认 worktree 根：

```text
C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\
```

正常开发应使用隔离 worktree。若当前 checkout 已有必须保留的未提交成果，可以在当前 checkout 切到新的维护分支，但必须记录 dirty ownership ledger。

## Provider Gate

远程能力默认关闭，必须按能力单独授权：

| 能力 | 默认状态 | gate |
|---|---|---|
| LLM | 关闭 | `AFS_ALLOW_REMOTE_LLM=true` |
| ASR | 关闭 | `AFS_ALLOW_REMOTE_ASR=true` |
| image | 关闭 | `AFS_ALLOW_REMOTE_IMAGE=true` |
| video | 关闭 | 任务级显式授权或后续独立 gate |
| external download | 关闭 | 任务级来源、用途和保存策略 |

Provider smoke 只代表 runtime verification，不代表 human acceptance、business validation 或 durable memory。

## 维护规则

涉及清理、中文化、重构或删除时：

1. 先写维护账本。
2. 分类为保留、归档、删除候选、暂缓。
3. 明确替代路径。
4. 运行维护审计。
5. 再执行删除或拆分。

维护审计入口：

```powershell
.\.venv\Scripts\python.exe tools\maintenance_audit.py
```

## AgentOps 最小层

AFS 近期不接外部观测 SaaS，但保留本地 artifact：

- `agentflow_run_trace`
- `agentflow_quality_report`
- `agentflow_guardrail_result`
- `agentflow_handoff_record`
- `agentflow_maintenance_audit_report`

这些 artifact 只作为证据，不能自动写长期记忆或公司知识库。

## 前后端协作

后端对接面：

```text
Runtime Service v0.1+
```

前端只使用安全引用：

- `project_id`
- `job_id`
- `artifact_id`
- safe summary
- safe manifest

前端不接触：

- CLI 内部实现。
- provider secret。
- 本地素材绝对路径。
- signed URL。
- 生成媒体字节。

## 记录规则

有意义的工作必须更新：

- `TASK_TRACKER.md`
- `DEVLOG.md`
- `docs/handoff/`
- `docs/maintenance/`

可复用经验回流 `10-Startup` 时只能进入 candidate/limited 流程。Agent 不能自行把候选规则晋升为 active。

## 外部项目思想协助标准投影

AFS 执行投影采用 `10-Startup/80-Workflow/ai-native-company-workflow/agent-assistance-standard.md` 的 candidate guidance。

项目内执行规则：

- 外部项目只作为机制来源，不默认安装、复刻或引入为依赖。
- 先在对话中总结核心思想，再映射到 AFS 已有对象：Project Prefix、Context Bundle、Memory Candidate、Feedback Signal、Quality Report、repo map、maintenance audit。
- 不为外部项目默认创建单独 intake 文档；只有用户明确要求时才创建。
- 涉及共享 contract、schema、Runtime Service、CLI、provider adapter 或维护清理时，先做仓库结构和影响面理解，再执行修改。
- 项目经验只能作为 evidence / candidate memory 回流 `10-Startup`，不能在 AFS repo 内直接晋升为 Company OS active rule。
