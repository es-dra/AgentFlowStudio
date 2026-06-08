# AFS Runtime Service 前端对接交接 001

日期：2026-06-08

Owner role：Runtime/API Integrator + Product Integration Steward

## 范围

本切片完成外部前端团队接入前所需的后端基线：

```text
AFS Core Engine / CLI contracts
-> AFS Runtime Service v0.1
-> safe job and artifact refs
-> frontend integration package
```

这只是本地前端集成准备，不是 SaaS、数据库层、账号系统、live provider execution、durable memory、human acceptance 或 business validation。

## 已实现

- 新增 FastAPI / uvicorn 依赖。
- 新增 `apps.api.runtime_service.create_runtime_app`。
- 新增 `apps.api.runtime_store.RuntimeStore`，管理本地 runtime jobs、project manifests 和 safe artifact refs。
- 新增 request models，覆盖 project creation、Round 1 asset test、Round 2 validation、raw feedback、provider validation plan。
- 新增 `apps.api.main` ASGI entrypoint。
- 新增 CLI 启动命令：

```powershell
.\.venv\Scripts\python.exe -m apps.cli.main runtime-service --host 127.0.0.1 --port 8790
```

## Runtime Service endpoints

- `GET /health`
- `GET /capabilities`
- `POST /projects`
- `GET /projects/{project_id}/manifest`
- `GET /artifacts/{artifact_id}`
- `GET /runs/{job_id}`
- `POST /runs/asset-test`
- `POST /runs/two-round-validate`
- `POST /feedback`
- `POST /provider/validation-plan`

## 前端对接包

目录：

```text
docs/frontend_integration/
```

文件：

- `README.md`
- `AFS_FRONTEND_HANDOFF.zh-CN.md`
- `AFS_FRONTEND_INTEGRATION_BRIEF.md`
- `AFS_API_ADAPTER_PLAN.md`
- `AFS_ARTIFACT_CONTRACT_MAP.md`
- `AFS_UI_WORKBENCH_REQUIREMENTS.md`

Request fixtures：

```text
examples/frontend_runtime_service/
```

## 对接边界

- 前端接收 `artifact_id`、job state 和 safe artifact payload。
- Runtime Service API response 不暴露 private local output path。
- 不暴露 provider config、key、signed URL、media bytes、provider response body 或 private material path。
- `/provider/validation-plan` 只生成 readiness / blocker evidence，不启动 live provider call。
- Raw feedback 仍是 raw evidence，不是 durable memory。
- Runtime verification 必须和 human acceptance、business validation 分开。

## 已验证

实现时已通过：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_api_runtime_service.py -q
.\.venv\Scripts\python.exe -m pytest tests/test_api_runtime_service.py tests/test_cli_command_registry_boundaries.py -q
.\.venv\Scripts\python.exe -m pytest
git diff --check
```

记录结果：

- Runtime Service API tests：6 tests passed。
- API + CLI boundary tests：12 tests passed。
- Focused Web static tests：15 tests passed。
- Contract 和 Project Manifest tests：27 tests passed。
- Full pytest：1004 tests passed。
- `git diff --check` passed，仅 Windows LF-to-CRLF warning。
- FastAPI TestClient 有 Starlette deprecation warning，提示未来 `httpx2`，不阻塞本切片。

## 后续

- 外部前端 workbench 可用后，再补 browser/UI smoke。
- live provider execution endpoint 必须作为独立 gated 切片，不在 v0.1 默认暴露。
- Runtime Service v0.2 优先补 project list/import/export、job progress、OpenAPI 固定导出、前端 client 生成说明。
- `10-Startup` / COS 更新保持 candidate-only，等待人工 review。

## 非声明边界

- 不声明 human acceptance。
- 不声明 business validation。
- 不写 durable memory。
- 不保存 secret、signed URL、本地私有素材字节、生成媒体或 provider response body。
