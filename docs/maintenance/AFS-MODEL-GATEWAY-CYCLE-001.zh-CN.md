---
doc_type: maintenance_ledger
status: verified
last_updated: 2026-06-08
owner_role: Architecture Reset Lead
branch: codex/afs-model-gateway-cycle-001
confidentiality: internal
---

# AFS Model Gateway Cycle 001

## 目标

关闭已知包级循环债务：

```text
agentflow_studio.model_gateway <-> agentflow_studio.production
```

## 非目标

- 不调用 live provider。
- 不改动 provider 授权 gate。
- 不声明 provider smoke 等于 human acceptance、business validation 或 durable memory。
- 不把 COS / 10-Startup candidate 规则晋升为 active rule。

## 改动

- 新增 `agentflow_studio/provider_contracts.py`，承载 provider 边界异常和 MiniMax 默认值。
- `agentflow_studio.model_gateway.errors` 改为兼容导出，保持旧 import 面可用。
- `production.posterflow` 不再从 `model_gateway.errors` 取异常。
- `model_gateway.minimax_image_plan` 不再从生产侧 provider 取 MiniMax 默认值。
- `model_gateway.minimax_image_smoke` 不再实例化 `production.posterflow.minimax_provider.MiniMaxImageProvider`。
- `model_gateway.minimax_image_runtime` 独立完成 MiniMax image smoke 的请求、候选文件写入和 safe output summary。
- 架构门禁移除 `model_gateway <-> production` 循环豁免。

## 验证

已通过：

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_architecture_audit_gates.py::test_package_level_cycle_debt_is_frozen tests\test_minimax_image_smoke.py tests\test_posterflow_provider.py tests\test_posterflow_openai_provider.py -q
.\.venv\Scripts\python.exe -m pytest tests\test_architecture_audit_gates.py tests\test_minimax_image_smoke.py tests\test_minimax_image_smoke_cli.py tests\test_posterflow_provider.py tests\test_posterflow_openai_provider.py tests\test_kling_video_smoke.py tests\test_kling_video_completion.py tests\test_kling_video_curl_smoke.py tests\test_kling_video_task_recovery.py tests\test_kling_video_request_plan.py -q
.\.venv\Scripts\python.exe -m apps.cli.main --help
.\.venv\Scripts\python.exe -m apps.cli.main version
```

结果：

```text
focused provider/architecture: 20 passed
expanded provider/architecture/CLI: 47 passed
CLI version: 0.1.0
```

最终验证已通过：

```powershell
.\.venv\Scripts\python.exe tools\maintenance_audit.py
.\.venv\Scripts\python.exe -m pytest
git diff --check
```

结果：

```text
maintenance_audit: failed=0, passed=4, warning=2
full pytest: 992 passed, 1 warning
git diff --check: passed
static import search: no model_gateway <-> production cross-import found
```

## 剩余队列

下一刀继续关闭：

```text
agentflow_studio.harness <-> agentflow_studio.workflow_engine
```
