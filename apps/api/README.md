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

Runtime Service v0.1 的职责：

- 包装现有 deterministic CLI/core functions。
- 给前端工作台提供稳定 API。
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

前端对接文档：

```text
docs/frontend_integration/
```
