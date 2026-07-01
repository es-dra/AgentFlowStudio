---
doc_type: maintenance_ledger
status: verified
last_updated: 2026-06-08
owner_role: Architecture Reset Lead
branch: codex/afs-maintenance-debt-closure-001
confidentiality: internal
---

# AFS Maintenance Debt Closure 001

## 目标

一次性关闭当前可安全自动解决的维护债务：

```text
包级循环豁免 -> 0
Runtime artifact writer 所属权混乱 -> 中立模块
CI / 维护门禁缺失 -> GitHub Actions gate
维护账本状态不清 -> 当前记录收口
```

## 非目标

- 不调用 live provider。
- 不删除仍被测试和文档引用的 hidden CLI 兼容命令。
- 不重建前端画布工作台。
- 不把 COS / 10-Startup candidate rule 晋升为 active。
- 不声明 human acceptance、business validation 或 durable memory。

## 已执行

- 新增 `agentflow_studio/workflow_run_artifacts.py`，承载 workflow trace 与 run manifest 写入。
- `workflow_engine.runner` 改为依赖中立 run artifact writer，不再依赖 `harness`。
- `harness.trace` 与 `harness.run_manifest` 改为兼容导出层。
- 架构测试从“冻结已知循环债务”升级为“不允许任何包级循环”。
- 新增 `.github/workflows/maintenance.yml`：
  - Python 3.12。
  - CLI help/version。
  - `maintenance_audit`。
  - 全量 pytest。
  - `git diff --check`。
  - provider gate 默认 false。
- 新增 CI workflow 静态测试，确保维护门禁存在且不打开 live provider。
- 更新 `tools/repository_retention_policy.py`，将 `.github` 与维护 workflow 登记为 `operations_spine`。

## 剩余不在本切片硬删的内容

- Hidden CLI support commands：仍有大量测试和文档依赖，当前应视为兼容支持面；后续如要删除，必须单独做 CLI 协议迁移。
- `maintenance_audit` oversized warning：多数是测试、历史 fixture、Web 过渡文件或 schema 相关文件；应逐个拆分，不做批量盲删。
- `secret_like_fragments` warning：当前 high confidence 为 0，多数是测试假 key、文档字段名或 tool catalog 文本；不作为泄密结论。

## 验证计划

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_architecture_audit_gates.py tests\test_workflow_run_contract.py tests\test_workflow_runner.py tests\test_ci_maintenance_workflow.py -q
.\.venv\Scripts\python.exe -m apps.cli.main --help
.\.venv\Scripts\python.exe -m apps.cli.main version
.\.venv\Scripts\python.exe tools\maintenance_audit.py
.\.venv\Scripts\python.exe -m pytest
git diff --check
```

已完成：

```text
red gate: removing harness/workflow_engine exemption exposed the cycle
focused architecture/workflow/CI tests: 12 passed
static import search: no harness <-> workflow_engine cross-import found
retention focused tests: 12 passed
repository_retention_review: delete_candidate_count=0, manual_review_required_count=0
CLI help: passed
CLI version: 0.1.0
maintenance_audit: failed=0, passed=4, warning=2
full pytest: 994 passed, 1 warning
git diff --check: passed
```
