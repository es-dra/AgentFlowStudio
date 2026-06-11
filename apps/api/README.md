# API

本目录保存 AgentFlow Runtime Service。

当前入口：

```powershell
.\.venv\Scripts\python.exe -m apps.cli.main runtime-service --host 127.0.0.1 --port 8790
```

ASGI app：

```text
apps.api.main:app
```

Runtime Service 的职责：

- 包装现有 deterministic CLI/core functions。
- 给 AFS Studio 提供稳定 API。
- 输出安全的 `project_id`、`job_id`、`artifact_id` 和 safe manifest。
- 每个 run 生成 `agentflow_run_trace`，用于本地 AgentOps 证据链。

本服务当前不做：

- SaaS runtime。
- 数据库。
- 账号系统。
- 浏览器持久化。
- live provider execution endpoint。
- durable memory write。
- human acceptance 或 business validation 声明。

当前前端和 API 文档：

```text
docs/architecture/AFS_STUDIO_FRONTEND_ARCHITECTURE_V1.zh-CN.md
docs/architecture/AFS_NODE_PROMPT_OPTIMIZER_CONTRACT.zh-CN.md
docs/openapi/
```
