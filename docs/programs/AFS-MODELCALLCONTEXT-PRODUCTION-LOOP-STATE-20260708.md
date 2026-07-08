# AFS ModelCallContext 生产闭环试航状态

项目编号：`AFS-PROGRAM-MCC-PROD-LOOP-20260708`

状态：active trial

## 当前切片

切片编号：`MCC-001`

目标：让 prompt optimization 从 Runtime 到 Studio 返回并保留安全的 `ModelCallContext` 公开摘要。

选择这个切片的原因：

- 它横跨 Runtime、Studio、测试和项目状态。
- 它能验证 Program Mode 是否能推进真实产品代码，而不是退化成文档循环。
- 它在 provider 全关闭条件下可运行，不依赖真实生成服务。

## 事件记录

- `2026-07-08T19:12:25+08:00`：创建分支 `codex/program-mcc-production-loop-20260708`。
- `2026-07-08T19:14+08:00`：扫描 `ModelCallContext`、prompt optimization、Studio optimizer 和现有测试。
- `2026-07-08T19:16+08:00`：实现 Runtime 公开 summary 与 Studio optimizer 证据保留。
- `2026-07-08T19:17+08:00`：第一轮聚焦验证通过。
- `2026-07-08T19:19+08:00`：更宽测试发现 OpenAPI snapshot 需要刷新。
- `2026-07-08T19:20+08:00`：刷新 OpenAPI snapshot，重跑通过。
- `2026-07-08T19:21+08:00`：维护审计通过失败门槛，结果为 warning。
- `2026-07-08T19:25+08:00`：#109 GitHub maintenance 在 OpenAPI snapshot 失败；定位为本地 `.venv` 依赖漂移。
- `2026-07-08T19:28+08:00`：创建临时 CI-like venv，按 `.[dev]` fresh install 后重导 OpenAPI snapshot，snapshot 单测通过。

## 证据

已通过命令：

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_model_call_context_contract.py::test_runtime_prompt_optimization_registers_model_call_context_artifact -q
.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_prompt_script_static.py::test_text_prompt_optimization_uses_and_updates_visible_content -q
npm run check:studio-js
.\.venv\Scripts\python.exe -m pytest tests\test_model_call_context_contract.py tests\test_model_call_context_runtime_routes.py -q
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_prompt_memory_loop.py tests\test_api_runtime_prompt_node_contract.py -q
.\.venv\Scripts\python.exe -m pytest tests\test_web_studio_prompt_script_static.py tests\test_web_studio_static.py::test_studio_asset_context_workflow_is_single_canvas tests\test_api_runtime_openapi_snapshot.py -q
.\.venv\Scripts\python.exe tools\maintenance_audit.py --fail-on failed
```

结果：

- Runtime / ModelCallContext 聚焦测试：12 passed。
- Prompt memory / node contract 聚焦测试：40 passed。
- Studio prompt optimizer / OpenAPI 组合测试：21 passed。
- Studio JS 语法检查：152 files passed。
- 维护审计：0 failed，3 passed，4 warning。
- CI-like 临时环境：FastAPI 0.115.14 / Pydantic 2.13.4，OpenAPI snapshot test passed。

## 发现的问题

架构问题：

- `prompt-optimizations` 原先只返回 `model_call_context_id`，Studio 无法保留足够的安全摘要，后续续跑、检查和 evaluator review 都缺少轻量状态。

实现问题：

- Studio `normalizeOptimization` 原先保留了 `context_bundle`，但丢弃了 `ModelCallContext` 证据。Runtime 已经写出 `model_call_context.json`，但前端闭环没有接上。

流程问题：

- Program Gate 明确后，真实跨层切片很快达到第一轮绿色证据；这说明“单主线程 + 项目书包 + 状态面 + 证据门禁”比重型治理线程更适合推进中等复杂任务。
- OpenAPI snapshot 及时失败并引导刷新，说明集成门禁有效。
- 维护审计提示新文档应满足中文覆盖率规则，说明项目状态文档也需要接受维护约束。
- 本地 `.venv` 存在依赖漂移：FastAPI 0.136.3 超出 `pyproject.toml` 的 `<0.116` 约束，不能作为 OpenAPI snapshot 权威环境。

## 效率快照

- 从创建分支到第一轮聚焦绿色证据：约 5 分钟。
- 本轮代码和测试触达文件：7 个。
- 新增 Program 状态文件：2 个。
- provider calls：0。
- 服务器写入：0。
- 人工审批门：0。
- 额外 CI debug 耗时：约 8 分钟，主要用于复现依赖环境差异并重导 snapshot。

## 待处理工作

- 提交并推送试航分支。
- 打开堆叠在 #107 之后的 draft PR。
- 对 public summary 白名单做 evaluator review。
- 后续清理本地 `.venv` 依赖漂移，或把 OpenAPI 导出固定到项目约束环境。
- 后续考虑把 `lastModelCallContextSummary` 显示到 inspector 或算法上下文面板。
- 继续清理维护审计 warning 中的长期超大文件和 legacy frozen 面。

## 当前非声明

本状态只记录结构和本地运行验证，不声明 provider QA、generated-media QA、public readiness、服务器已加载当前分支代码、Owner acceptance、human acceptance、business acceptance 或 legal acceptance。
