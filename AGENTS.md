# AGENTS.md

## 项目使命

AgentFlow Studio 是一个面向 Agent 的本地优先内容生产与分发工作台。

当前仓库分层：

```text
agentflow/             平台 contract、harness、router、memory、skills
examples/agentflow_production/  内容生产侧结构化 handoff 示例输入
agentflow_studio/      短视频分发侧包装、审查、报告
apps/                  CLI、Runtime Service、过渡 Web 工作台
```

当前 MVP 链路：

```text
subtitle/text -> hooks -> scripts -> clip_plans -> videos -> metadata
```

近期主线是本地内测可用，不是 SaaS，也不是商业试点。

## 规则层级

遇到多层规则时，按下面顺序理解：

```text
D:\Learning materials\Learning_notes\10-Startup
  -> 全局 workflow skills
  -> 本文件 AGENTS.md
  -> docs/company_operating_model.md
  -> TASK_TRACKER.md / branch handoff
  -> 当前任务
```

`10-Startup` 是公司源头知识库。AFS 仓库只保存执行投影：代码、测试、contract、runbook、handoff、可公开或半公开工程说明。

禁止把以下内容写入仓库：

- secret、token、cookie、provider key、signed URL。
- 本地私有素材字节、生成媒体、provider 原始响应。
- 未公开商业判断、真实成本、客户信息、合作方判断。
- 公司内部失败复盘原文。

## 启动规则

进入、恢复、扫描、调试或编辑本项目时：

1. 先使用 `project-development-workflow` skill。
2. 先做 startup scan，再改文件。
3. 读取本文件、`docs/company_operating_model.md`、`TASK_TRACKER.md`。
4. 按任务难度分类：`Light` / `Standard` / `Deep` / `Strategic`。
5. 明确写入范围、非目标、验证命令、provider gate、handoff 位置。

当前任务如果是维护、清理、重构、中文化，必须先有维护账本。

## Worktree 与分支

- 默认使用 `codex/*` 分支。
- 非 trivial、多文件、provider、Runtime Service、Web、架构或清理任务，优先使用隔离 worktree。
- 当前项目 worktree 约定路径：

```text
C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\
```

如果当前 checkout 已经有必须集成的未提交成果，可以在当前工作树切到新的 `codex/*` 维护分支，但必须记录 dirty ownership ledger。

禁止：

- `git reset --hard` 或无账本删除。
- 因为分支已 push 就直接合并。
- 多个任务并行修改同一 schema、registry、CLI 入口或核心 contract。

## Provider Gate

远程 provider 默认关闭，必须按能力单独授权：

| 能力 | 默认 | gate |
|---|---|---|
| LLM | 关闭 | `AFS_ALLOW_REMOTE_LLM=true` |
| ASR | 关闭 | `AFS_ALLOW_REMOTE_ASR=true` |
| image | 关闭 | `AFS_ALLOW_REMOTE_IMAGE=true` |
| video | 关闭 | 任务级显式授权，或后续独立 gate |
| external download | 关闭 | 任务级来源、用途、保存路径和清理策略 |

授权 image 不代表授权 video、LLM、ASR 或下载。

## 工程边界

- schema-first / contract-first。
- artifact-first，再做 UI。
- harness-first，再接 agent/provider。
- trace-first，再写结论。
- 本地 deterministic 先通过，再打开 provider。
- feedback 是 raw evidence，不自动成为 memory。
- candidate memory 不是 durable memory。
- runtime verification 不是 human acceptance。
- provider smoke 不是 business validation。

## 前后端边界

后端对接面是 Runtime Service，不是 CLI 内部实现。

前端可以使用：

- `project_id`
- `job_id`
- `artifact_id`
- safe summary
- safe manifest
- OpenAPI

前端不应接触：

- provider secret。
- 本地素材绝对路径。
- signed URL。
- 生成媒体字节。
- CLI 内部编排细节。

## 文件维护规则

- 理想单文件不超过 300 行。
- 301-500 行进入维护审计 warning。
- 超过 500 行必须有拆分计划或充分理由。
- 新模块只做一个职责。
- API route、job orchestration、artifact store、provider adapter、report writer、UI render 不要混在一个文件里。

## 本地配置

- 推荐 Python 3.12。
- 项目声明 `>=3.11,<3.13`。
- 不要切到 Python 3.13，除非媒体、ASR、model/provider 依赖已验证。
- 只提交 example config。
- `configs/models.yaml` 是本地配置，已被 git ignore。
- `.env`、`.dev.vars` 只用于本地，不能提交。

## 验证

改动完成前，按风险运行相关命令。基础命令：

```powershell
.\.venv\Scripts\python.exe -m apps.cli.main --help
.\.venv\Scripts\python.exe -m apps.cli.main version
.\.venv\Scripts\python.exe -m pytest
git diff --check
```

维护/清理/中文化任务追加：

```powershell
.\.venv\Scripts\python.exe tools\maintenance_audit.py
```

## 记录

有意义的工作必须更新项目记录：

- `TASK_TRACKER.md`
- `DEVLOG.md`
- `docs/handoff/`
- `docs/maintenance/`

需要反馈到 COS 的经验只能进入 `10-Startup` 的 candidate/limited 流程，不能由 Agent 自动晋升为 active rule。
