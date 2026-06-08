# AFS 低成本维护收口 001

日期：2026-06-09

## 目标

本切片用于在进入自研轻量 Web 和完整流程跑通前，收掉会持续增加维护成本的噪声和过渡结构。

本切片不是 Web 开发，不启动 provider，不声明 human acceptance、business validation 或 durable memory。

## 写入范围

- `tools/maintenance_audit*`
- `configs/tool_catalog*`
- `agentflow_studio/workflow_engine/tool_catalog.py`
- `apps/web/*artifact-workspace*`
- `apps/web/*inspector*`
- `tests/test_maintenance_audit.py`
- `tests/test_tool_catalog.py`
- 相关 Web 静态测试

## 已处理

### 1. 维护审计安全噪声

原问题：

- `secret_like_fragments` 把 schema 字段名、测试假值、环境变量名、函数参数传递都当成 warning。
- 结果是维护人员需要反复解释低置信噪声，真正风险反而不突出。

处理：

- 拆出 `tools/maintenance_audit_secret_scan.py`。
- 区分高置信 secret、schema 字段、环境变量引用、参数引用和测试 fixture。
- 增加回归测试，确认真实 `sk-...` 形态仍会被抓住。

当前结果：

```text
secret_like_fragments: passed
high_confidence_count: 0
```

### 2. Tool Catalog 大文件

原问题：

- `configs/tool_catalog.yaml` 超过 1100 行，是当前最大的配置维护点。

处理：

- `configs/tool_catalog.yaml` 改为小索引。
- 实际条目拆到 `configs/tool_catalog/*.yaml`。
- 新增 `agentflow_studio/workflow_engine/tool_catalog.py`，让 CLI planning 和测试共享同一加载路径。

边界：

- 不改变 tool contract 内容。
- 不新增 runtime registry。
- 不新增 agent execution。

### 3. 过渡 Web 大文件

原问题：

- `apps/web/memory-workbench-production-inspector-facts.js`、`memory-workbench-inspector.js`、`artifact-workspace.js` 都把多类映射逻辑堆在单文件里。

处理：

- production inspector facts 拆成 next / feedback / asset / operator / utils 分片。
- memory inspector 拆出 label、focus routing、status routing。
- artifact workspace 拆出 artifact parsing/type detection。

边界：

- 仍然只是 read-only / local-only artifact viewer。
- 不作为后续正式 Web 架构。
- 后续自研轻量 Web 应优先接 Runtime Service，而不是继续扩展这些过渡文件。

## Hidden CLI 边界

当前 hidden CLI 仍保留两类：

- provider smoke / recovery support commands。
- production memory loop 的历史兼容命令。

本切片不直接删除它们，原因是仍有测试和历史流程引用。后续删除条件：

1. 对应能力已经有公开 Runtime Service 或公开 CLI protocol。
2. 迁移文档写清旧命令到新命令的映射。
3. `tests/test_architecture_audit_gates.py` 的 hidden command debt 清单同步减少。
4. 全量测试通过。

禁止继续新增 hidden tester-facing command。

## 剩余 warning

维护审计当前仍保留 oversized warning，主要集中在：

- 历史/综合测试文件。
- `agentflow/memory/*` contract-heavy 文件。
- `agentflow_studio/harness/*` 质量与报告文件。
- 旧 workflow / package 报告实现。

本切片已处理最影响后续维护的配置和 Web 过渡大文件；剩余文件不再阻塞进入下一阶段，但后续每次触碰对应模块时应顺手拆分。

## 验证命令

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_maintenance_audit.py tests\test_tool_catalog.py tests\test_workflow_plan_draft.py tests\test_repository_retention_review.py -q
.\.venv\Scripts\python.exe -m pytest tests\test_web_static_artifact_workspace.py tests\test_web_static_artifact_registry.py tests\test_web_static_artifact_boundaries.py tests\test_web_static_artifact_viewer.py tests\test_web_memory_static_structure.py tests\test_web_memory_artifact_summary_static.py -q
.\.venv\Scripts\python.exe tools\maintenance_audit.py
.\.venv\Scripts\python.exe tools\repository_retention_review.py --root . --summary-only
```

## 当前证据

已完成的局部验证：

```text
maintenance/tool catalog/retention focused tests: 29 passed
Web artifact workspace / inspector focused tests: 26 passed
maintenance_audit: failed=0, passed=5, warning=1
secret_like_fragments: passed, count=0, high_confidence_count=0
oversized_files: 24
repository_retention_review: delete_candidate_count=0, manual_review_required_count=0
full pytest: 997 passed, 1 warning
git diff --check: passed
```

## 下一步

1. 跑架构门禁、CLI smoke、全量 pytest、`git diff --check`。
2. 生成 COS feedback packet，作为 `AI-Agent项目可维护性与中文化规范` 的 candidate / limited 证据。
3. 进入自研轻量 Web 前，先确认 Runtime Service/OpenAPI 仍是唯一正式对接面。
4. 再跑 Loulan/fixture 的完整 deterministic 流程。
