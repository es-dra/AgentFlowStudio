# AFS Runtime Service v0.2 前端契约交接

日期：2026-06-08

Owner role：Runtime/API Integrator + Frontend Contract Steward

## 范围

本切片把 Runtime Service 从 v0.1 的“可跑后端基线”推进到 v0.2 的“前端可对接契约”：

- 项目列表。
- 项目 manifest JSON 导入。
- 项目 manifest JSON 导出。
- job progress 终态字段。
- OpenAPI schema 固定导出。
- 前端 request fixture 补齐。

## 新增接口

```text
GET  /projects
POST /projects/import
GET  /projects/{project_id}/export
```

已有接口保持：

```text
GET  /health
GET  /capabilities
POST /projects
GET  /projects/{project_id}/manifest
GET  /artifacts/{artifact_id}
GET  /runs/{job_id}
POST /runs/asset-test
POST /runs/two-round-validate
POST /feedback
POST /provider/validation-plan
```

## OpenAPI 导出

前端团队可直接使用已提交的 schema：

```text
docs/frontend_integration/openapi/afs-runtime-service.openapi.json
```

也可以本地重新生成：

```powershell
.\.venv\Scripts\python.exe -m apps.cli.main runtime-service-openapi-export --output docs\frontend_integration\openapi\afs-runtime-service.openapi.json
```

## 前端可使用

- `project_id`
- `job_id`
- `artifact_id`
- project summary
- job progress
- safe manifest
- selected artifact payload
- OpenAPI schema

## 前端不可使用

- CLI 内部函数。
- provider secret。
- 本地素材绝对路径。
- signed URL。
- 生成媒体字节。
- provider 原始响应。
- durable memory 写入。

## 新增 fixture

```text
examples/frontend_runtime_service/project_import.request.example.json
```

## 边界

- 本切片不做数据库、账号、SaaS、云同步。
- 本切片不启动 live provider。
- `/provider/validation-plan` 仍只输出 blocker / safe manifest evidence。
- feedback 仍是 raw evidence，不自动进入 durable memory。
- runtime verification 不等于 human acceptance 或 business validation。

## 验证

本切片 focused regression：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_api_runtime_service.py tests/test_cli_command_registry_boundaries.py -q
```

已通过：

```text
15 passed, 1 warning
```

warning 为 FastAPI TestClient / Starlette deprecation warning，不阻塞本切片。
