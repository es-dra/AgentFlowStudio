# AFS-STUDIO-MAINLINE-CLEANUP-001 交接

分支：`codex/afs-studio-mainline-cleanup-001`

## 范围

- 更新 `AGENTS.md` 与 `docs/current_architecture.md`，明确 Studio 是当前 MVP 主线。
- legacy Runtime v02 路由默认隐藏，只有 `AFS_ENABLE_LEGACY_RUNTIME_V02=true` 时注册。
- 增加默认 OpenAPI 隐藏旧接口、显式开启 legacy 的测试。
- 增加静态 guard，防止新的 Studio/Runtime 模块继续 import `agentflow.memory`。
- 对被点名的 `*_sop` 清理目标执行 tracked 文件审计，只删除无引用的 `agentflow_studio/compliance/__init__.py` 空壳。

## 验证

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_api_runtime_service_v02.py tests/test_studio_mainline_cleanup.py tests/test_web_studio_static.py
.\.venv\Scripts\python.exe tools\maintenance_audit.py
git diff --check
```

当前结果：

- cleanup 聚焦测试：15 passed。
- `git diff --check`：仅 Windows CRLF notice。
- `maintenance_audit.py`：无 failed；仍有 oversized files warning，作为后续维护债处理。

## 边界

- 本分支不删除 `agentflow/memory`。
- ignored pycache 和本地空目录不算产品代码删除成果。
- 未打开 provider gate。
