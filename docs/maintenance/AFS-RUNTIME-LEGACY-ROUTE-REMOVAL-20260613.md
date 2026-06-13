# AFS Runtime Legacy Route Removal - 2026-06-13

## 摘要

本轮是一个 Standard 维护切片：从当前 Runtime Service 合约中退出
Production Memory 的 HTTP 暴露面，同时保留 `agentflow/memory`、
production-memory CLI 和 production-memory harness/function 测试。

已确认定位句：

```text
AgentFlow Studio 是 AI 内容生产的 Agent-native 生产操作层。
```

## 范围

从当前 Runtime HTTP 合约中移除：

- `POST /runs/asset-test`
- `POST /runs/two-round-validate`
- `POST /provider/validation-plan`

明确保留：

- `agentflow/memory` 模块和 production-memory CLI 命令。
- `tests/test_production_memory_*` 里的函数级、CLI 级 harness 覆盖。
- `POST /provider/script-draft-plan`，它属于当前 LLM script 纵切能力。
- `AFS_ENABLE_LEGACY_RUNTIME_V02=true` 后才开启的 v02 legacy 路由。

## 决策

- OpenAPI 按默认环境导出，不设置 `AFS_ENABLE_LEGACY_RUNTIME_V02=true`。
- 默认 OpenAPI 快照会同步清掉旧快照里陈旧的 v02 路由，以及本轮退役的
  三条 Production Memory 路由。
- 前端 Runtime 示例目录删除退役路由对应的 request fixture。本 worktree 中
  还存在一个陈旧的 `two_round_validate.request.example.json`，因此也随同删除；
  如果后续分支中该文件不存在，删除步骤应当跳过而不是报错。
- `apps/api/runtime_events.py` 改为 Runtime 本地常量，但 artifact 字段值不变：
  `production-memory-loop/v1`。
- 当前默认 Runtime 路由不再把 `str(exc)` 直接投影到响应 detail。剩余
  `detail=str(exc)` 只存在于 legacy v02 路由中，作为后续风险记录。

## 已验证

Focused verification 已通过：

```text
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests/test_api_runtime_service.py tests/test_api_runtime_service_v02.py tests/test_cli_command_registry_boundaries.py tests/test_studio_mainline_cleanup.py tests/test_maintenance_audit.py

31 passed, 2 warnings
```

默认 OpenAPI 已重新导出：

```text
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main runtime-service-openapi-export --output docs\openapi\afs-runtime-service.openapi.json
```

解析后的默认 OpenAPI 不再包含：

- `/runs/asset-test`
- `/runs/two-round-validate`
- `/provider/validation-plan`
- `/projects/import`
- `/projects/{project_id}/source-assets`
- `/projects/{project_id}/content-cards`
- `/projects/{project_id}/canvas-draft`
- `/projects/{project_id}/scene-inspector`
- `/projects/{project_id}/review-decisions`
- `/projects/{project_id}/export`

解析后的默认 OpenAPI 仍包含：

- `/provider/script-draft-plan`

完整验证已通过：

```text
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe tools\maintenance_audit.py
status=warning, failed=0, passed=4, warning=2

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main --help
exit 0

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main version
0.1.0

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest
886 passed, 2 warnings

git diff --check
exit 0, Windows CRLF notices only
```

## 残余风险

- Legacy v02 路由仍存在直接 `detail=str(exc)` 投影，需要在独立 legacy-only
  切片中退役或收口。
- lock 文件生成、CRLF 归一化和 provider gate 隔离测试没有混入本轮，已进入
  BACKLOG。
- 三条退役 POST 路径有 `include_in_schema=False` 的隐藏 404 tombstone。它们
  不属于 OpenAPI 合约，只用于避免 `/runs/{job_id}` 把已退役 POST 路径投影成
  `405 Method Not Allowed`。
