# 前端 Runtime Service 请求示例

这些 request examples 用于本地 AFS Runtime Service v0.1。

启动服务：

```powershell
.\.venv\Scripts\python.exe -m apps.cli.main runtime-service --host 127.0.0.1 --port 8790
```

第一轮前端集成 smoke 可以直接把这些文件作为 request body：

- `create_project.request.example.json`
- `asset_test_run.request.example.json`
- `two_round_validate.request.example.json`
- `feedback_record.request.example.json`
- `provider_validation_plan.request.example.json`

`two_round_validate` fixture 里有占位 `round_1_job_id`。实际联调时，用 `/runs/asset-test` 返回的 `job.job_id` 替换它。
