# Frontend Runtime Service Examples

中文摘要：本目录保存给 Studio 与 Runtime Service 对接使用的安全请求示例。示例只包含 project id、node prompt、safe asset refs、节点参数和 provider gate 所需的非敏感字段；不得加入 secret、本地素材路径、signed URL、媒体字节或 provider 原始响应。当前重点是 prompt optimization 和 keyframe generation 契约。

These request examples are safe local fixtures for AFS Studio and Runtime
Service integration.

Start the local service:

```powershell
.\.venv\Scripts\python.exe -m apps.cli.main runtime-service --host 127.0.0.1 --port 8790
```

Current OpenAPI export:

```powershell
.\.venv\Scripts\python.exe -m apps.cli.main runtime-service-openapi-export --output docs\openapi\afs-runtime-service.openapi.json
```

Core fixtures:

- `create_project.request.example.json`
- `project_import.request.example.json`
- `asset_test_run.request.example.json`
- `two_round_validate.request.example.json`
- `feedback_record.request.example.json`
- `provider_validation_plan.request.example.json`

Node prompt optimizer fixtures:

```text
prompt_optimizer_nodes/
```

Key Runtime endpoints for Studio:

- `POST /projects/{project_id}/prompt-optimizations`
- `POST /projects/{project_id}/keyframe-generations`

Provider gates are closed by default. Fixtures must not contain provider
secrets, local private paths, signed URLs, provider raw responses, or media
bytes. Replace the placeholder `round_1_job_id` in `two_round_validate` with the
`job.job_id` returned by `/runs/asset-test` during live local smoke.
