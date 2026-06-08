---
doc_type: maintenance_ledger
status: in_progress
last_updated: 2026-06-08
owner_role: Maintainability Steward
branch: codex/afs-product-spine-reset-003
confidentiality: internal
---

# AFS Product Spine Reset 003

## 目标

本切片不再以“减少几个超长文件 warning”为目标，而是把 AFS 仓库压回一条清晰产品脊柱：

```text
agentflow contracts / harness / memory / agentops
  -> agentflow_studio production pipeline / provider adapters
  -> apps/api Runtime Service
  -> frontend-safe refs and artifacts
```

旧 demo、旧 bridge、过渡 Web、历史 docs 和隐藏 CLI 如果不服务当前产品脊柱，就必须进入删除、隔离或退休队列。

## 非目标

- 不调用 live provider。
- 不提交 runtime media、secret、signed URL 或 provider 原始响应。
- 不把 COS candidate 规则晋升为 active。
- 不把历史 evidence 直接删除到无法追溯；删除前必须有替代入口或明确迁移路径。

## Product Spine 分类

`tools/repository_retention_review.py` 已从温和保留语义改为产品脊柱语义：

| 分类 | 含义 | 默认动作 |
|---|---|---|
| `production_spine` | 当前产品主线代码、API、维护工具、当前对接文档 | 保留并继续收敛 |
| `operations_spine` | 本地 CLI / deterministic harness 运维入口 | 保留，但不应暴露旧 demo |
| `supporting_contract` | examples、configs、contract fixture | 保留或拆分 |
| `verification_surface` | 当前自动化测试 | 保留，旧 demo 测试随旧 demo 迁移 |
| `transition_surface` | 过渡 Web / hidden support registry | 必须有退休条件 |
| `quarantine_candidate` | 旧 bridge、编号 demo、旧 demo CLI / tests | 默认隔离，满足条件后删除 |
| `historical_reference` | handoff、task brief、archive | 只作为历史证据，继续摘要归档和删减 |
| `mixed_docs_surface` | 未完全分层的 docs 当前/历史混合面 | 复审当前性 |

当前 summary：

```text
product_surface_counts:
  production_spine: 348
  operations_spine: 50
  supporting_contract: 110
  verification_surface: 248
  transition_surface: 86
  quarantine_candidate: 19
  historical_reference: 120
  mixed_docs_surface: 71
```

这说明仓库已经不应再被描述为“没有删除候选”，而是有明确的旧面和过渡面待处理。

## 已执行动作

### 1. 封存 provider cleanup baseline

在进入 Product Spine Reset 前，已将上一轮 provider/test 拆分提交为：

```text
001def9 chore: seal provider cleanup baseline
```

该提交包含：

- Harness-first 定位投影。
- Kling completion 拆分。
- Kling / MiniMax / PosterFlow provider 测试边界拆分。
- `AFS-ACTUAL-CLEANUP-002` 维护账本。

验证：

```text
63 passed
maintenance_audit failed=0, passed=4, warning=2
git diff --check exit 0
```

### 2. 改造 repository_retention_review 为 Product Spine 审查

修改：

```text
tools/repository_retention_review.py
tests/test_repository_retention_review.py
```

变化：

- 新增 `product_surface` 字段。
- summary 新增 `product_surface_counts`。
- `apps/web_bridge` 被标记为 `quarantine_candidate / legacy_runtime_surface`。
- 编号 memory advantage demo modules 被标记为 `quarantine_candidate / legacy_demo_runtime`。
- 编号 memory demo tests 被标记为 `quarantine_candidate / legacy_demo_verification`。
- `apps/web` 被标记为 `transition_surface / retire_when_replaced`。
- `docs/handoff`、`docs/task_briefs` 被标记为 `historical_reference / archive_or_delete_when_indexed`。

验证：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_repository_retention_review.py -q
```

结果：

```text
3 passed
```

同时拆分维护工具自身：

```text
tools/repository_retention_review.py -> 124 行，只负责收集、汇总和 CLI 输出
tools/repository_retention_policy.py -> 188 行，只负责目录/文件分类策略
```

验证：

```powershell
.\.venv\Scripts\python.exe tools\repository_retention_review.py --root . --summary-only
```

结果：脚本入口可直跑，并输出 `product_surface_counts`。

### 3. 删除编号 memory advantage demo 的 CLI 可执行入口

删除：

```text
apps/cli/memory_demo_commands.py
```

修改：

```text
apps/cli/support_command_registry.py
tests/test_cli_command_registry_boundaries.py
tests/test_architecture_audit_gates.py
tests/test_memory_advantage_demo_012.py
tests/test_memory_advantage_demo_015.py
```

变化：

- `support_command_registry` 不再 import 或注册：
  - `memory-advantage-demo-012-plan`
  - `memory-advantage-demo-012-i2i-runtime`
  - `memory-advantage-demo-012-i2v-runtime`
  - `memory-advantage-demo-015-plan`
  - `memory-advantage-demo-015-i2v-runtime`
- `KNOWN_HIDDEN_COMMAND_DEBT` 移除上述 5 个旧 demo hidden CLI。
- DEMO-012 / DEMO-015 的历史模块测试仍保留，用于迁移前 evidence 校验，但不再测试 CLI 入口。

验证：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_cli_command_registry_boundaries.py tests/test_architecture_audit_gates.py tests/test_memory_video_pipeline_workflow.py tests/test_memory_advantage_demo_012.py tests/test_memory_advantage_demo_015.py tests/test_repository_retention_review.py -q
```

结果：

```text
32 passed
```

### 4. 将旧 Web bridge 从可见产品 CLI 降级

修改：

```text
apps/cli/command_registry.py
tests/test_cli_command_registry_boundaries.py
```

变化：

- `web-bridge` 仍可通过显式命令调用，用于尚未迁移完成的本地诊断路径。
- `web-bridge` 不再出现在默认 CLI help 的可见产品命令列表中。
- Runtime Service 继续作为前端唯一主对接面。

验证：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_cli_command_registry_boundaries.py tests/test_web_production_bridge.py tests/test_memory_video_pipeline_workflow.py -q
```

结果：

```text
22 passed
```

CLI smoke：

```powershell
.\.venv\Scripts\python.exe -m apps.cli.main --help
```

结果：默认 help 不再显示 `web-bridge`。

### 5. 本切片最终聚焦验证

```powershell
.\.venv\Scripts\python.exe -m apps.cli.main --help
.\.venv\Scripts\python.exe -m apps.cli.main version
.\.venv\Scripts\python.exe -m pytest tests/test_cli_command_registry_boundaries.py tests/test_architecture_audit_gates.py tests/test_memory_video_pipeline_workflow.py tests/test_memory_advantage_demo_012.py tests/test_memory_advantage_demo_015.py tests/test_repository_retention_review.py tests/test_web_production_bridge.py tests/test_maintenance_audit.py -q
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe tools\maintenance_audit.py
git diff --check
```

结果：

```text
CLI version: 0.1.0
50 passed
1023 passed, 1 warning
maintenance_audit failed=0, passed=4, warning=2
git diff --check exit 0，仅 Windows 换行提示
```

## 下一步

### P0：旧 Web bridge 降级 / 删除

当前状态：

```text
apps/web_bridge -> quarantine_candidate / legacy_runtime_surface
```

建议下一刀：

- 判断 `tests/test_web_production_bridge.py` 中哪些能力已由 Runtime Service v0.2 覆盖。
- 能覆盖的旧 bridge API 删除。
- 不能覆盖的能力迁入 Runtime Service 或明确放弃。
- `web-bridge` CLI 从可见产品命令中移除。

### P0：解除 `model_gateway <-> production` 循环

当前问题：

```text
agentflow_studio.model_gateway -> agentflow_studio.production
agentflow_studio.production -> agentflow_studio.model_gateway.errors
```

下一步：

- 下沉 provider error contract。
- 更新 PosterFlow provider 和 model gateway 引用。
- 从 architecture gate 中移除该 known cycle。

### P1：解除 `workflow_engine <-> harness` 循环

当前问题：

```text
agentflow_studio.harness -> agentflow_studio.workflow_engine.context / definitions
agentflow_studio.workflow_engine.runner -> agentflow_studio.harness
```

下一步：

- 抽出 workflow contract。
- runner 与 harness 只依赖 shared contract。

## 非声明边界

- 本轮是结构维护，不是 human acceptance。
- 本轮不是 business validation。
- 本轮不是 durable memory。
- 本轮未调用 provider。
- 本轮未写入 `10-Startup`。
