# AFS 前端对接包

状态：Runtime Service v0.2 对接包。

这组文档给外部画布/工作台前端团队使用。前端只对接 Runtime Service，不需要理解 CLI 内部实现，也不应读取私有本地路径、provider secret 或浏览器侧执行逻辑。

建议阅读顺序：

1. `AFS_FRONTEND_HANDOFF.zh-CN.md`
2. `AFS_FRONTEND_INTEGRATION_BRIEF.md`
3. `AFS_API_ADAPTER_PLAN.md`
4. `AFS_ARTIFACT_CONTRACT_MAP.md`
5. `AFS_UI_WORKBENCH_REQUIREMENTS.md`

示例 request payload：

```text
examples/frontend_runtime_service/
```

OpenAPI 固定导出：

```text
docs/frontend_integration/openapi/afs-runtime-service.openapi.json
```

重新导出命令：

```powershell
.\.venv\Scripts\python.exe -m apps.cli.main runtime-service-openapi-export --output docs\frontend_integration\openapi\afs-runtime-service.openapi.json
```

Runtime Service 启动：

```powershell
.\.venv\Scripts\python.exe -m apps.cli.main runtime-service --host 127.0.0.1 --port 8790
```

OpenAPI：

```text
http://127.0.0.1:8790/docs
http://127.0.0.1:8790/openapi.json
```

前端可以使用：

- `project_id`
- `job_id`
- `artifact_id`
- safe summary
- safe manifest
- selected JSON payload
- project summary
- job progress

前端不能使用：

- CLI 内部函数。
- provider secret。
- 本地素材绝对路径。
- signed URL。
- 生成媒体字节。
- provider 原始响应。

本切片边界：

- 本地内测和私有部署优先。
- 不做 SaaS。
- 不做账号系统。
- 不做数据库。
- 不做云同步。
- 不做多租户权限模型。
- provider call 默认不启动。
- runtime verification 不等于 human acceptance 或 business validation。
