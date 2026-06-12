# AFS-PROVIDER-ADAPTER-V0-1 交接

分支：`codex/afs-provider-adapter-v0-1`

## 范围

- 新增 provider adapter contract 与 registry。
- 将 MiniMax image 标准化为第一个 Runtime-facing adapter。
- `apps/api/runtime_keyframes.py` 不再直接 import `run_minimax_image_smoke`。
- Runtime prompt 字符上限与参考图 slot 改由 provider descriptor 决定。

## 验证

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_provider_adapter_registry.py tests/test_api_runtime_creative_agent_keyframes.py tests/test_api_runtime_keyframe_reference_assets.py tests/test_api_runtime_context_resolver.py
.\.venv\Scripts\python.exe -m pytest tests/test_minimax_image_smoke.py tests/test_minimax_image_smoke_backends.py
.\.venv\Scripts\python.exe -m py_compile agentflow_studio/model_gateway/provider_adapter.py apps/api/runtime_keyframes.py apps/api/runtime_context_resolver.py apps/api/runtime_context_budget.py
```

结果：

- Adapter/keyframe/resolver 聚焦集：31 passed。
- MiniMax smoke 回归：9 passed。
- `py_compile`：passed。

## Provider Gate

未打开真实 provider gate。测试只覆盖 mocked dispatch 或 gate-closed 路径。

## 非目标

- Kling adapter 不在本切片实现。
- CLI 命令名保持兼容；更深的 CLI registry 化可后续处理。
- 仍然不引入外部 provider 网关。
