---
doc_type: maintenance_ledger
status: active
last_updated: 2026-06-08
owner_role: Release Integrator + Maintainability Steward
branch: codex/afs-maintenance-localization-cleanup-001
confidentiality: internal
---

# AFS 维护性重置与中文化账本 001

## 目标

本切片把 AFS 从“功能不断堆叠的本地项目”整理成一个更可维护的本地内测后端基线。

本切片要完成：

- 把当前未提交的 Runtime Service、本地内测、provider recovery、前端对接材料纳入同一个维护分支。
- 建立维护审计脚本，让旧路径、英文人类文档、secret-like 文本、超长文件、runtime artifact 入库风险可以被持续发现。
- 建立 AFS 本地轻量 AgentOps artifact：trace、quality report、guardrail result、handoff record、maintenance audit report。
- 将关键入口文档改为中文，并把旧 `Company` 源头路径修正为 `10-Startup`。
- 将公司级 Agent 项目维护规范写入 `10-Startup`，但只作为 candidate。

本切片不做：

- 不引入 LangGraph、Dapr、CrewAI、Langfuse、AgentOps SaaS 依赖。
- 不删除未分类文件。
- 不写 secret、provider config、signed URL、私有素材字节或生成媒体。
- 不声明 human acceptance、business validation 或 durable memory。
- 不把 COS 候选规则自动晋升为 active。

## Dirty Ownership Ledger

| 类别 | 当前处理 | 说明 |
|---|---|---|
| Runtime Service v0.1 | 保留并纳入本分支 | 后端对接基线，前端团队应只接 Runtime Service，不接 CLI 内部。 |
| 本地内测 landing | 保留 | Round 1、Round 2、Project Manifest、Provider Gate 是当前本地内测闭环。 |
| provider recovery | 保留 | Kling fallback/retry 是 live provider smoke 的恢复证据，但 provider 仍默认关闭。 |
| Asset Review Screen worktree | 暂缓删除 | 该 worktree 与主分支同 commit，但仍有未提交 UI 文件；等本分支完成后再做最终 branch/worktree 清理。 |
| 英文历史文档 | 归档/摘要候选 | 不逐字翻译历史长文，优先保留中文入口和当前执行文档。 |
| Web 旧工作台 | 过渡保留 | 外部前端团队将重建画布工作台，本仓库只维持 read-only 过渡视图。 |
| runtime/generated data | 不提交 | 只允许引用 ignored runtime evidence，不复制路径、媒体或 provider 响应。 |

## 保留清单

- `apps/api/`：Runtime Service 是后端唯一对接面。
- `apps/cli/`：CLI 继续作为本地运维入口，不暴露给前端团队作为主对接面。
- `agentflow/memory/production_asset_*`：deterministic Production Memory asset loop。
- `agentflow/contracts/`：机器契约和 example registry。
- `docs/frontend_integration/`：前端对接包。
- `docs/local_internal_test_runbook.md`：测试人员可跑的本地内测 runbook。
- `docs/project_manifest_contract.md`：本地项目工作台 contract。
- `tools/repository_retention_review.py`：逐目录逐文件保留性审查，输出 `agentflow_repository_retention_review`。
- `docs/archive/HISTORICAL_DOCS_SUMMARY.zh-CN.md`：历史英文文档中文摘要索引，作为旧 handoff、旧路线图和旧验收记录的替代入口。

## 归档/删除候选

以下内容必须先被审计脚本和测试证明不再被引用，才允许删除：

- 已被 deterministic harness 覆盖的 numbered demo。
- 重复 handoff 长文。
- 已被 Runtime Service v0.1 替代的旧前端对接说明。
- patch-equivalent 的 stale branch 和 stale worktree。
- 已合并到 `README.md` 的 `README.zh-CN.md` 旧中文入口。

## 暂缓项

- `apps/web/*` 不做深度重构。原因：未来前端工作台会由外部团队重建，本仓库只保留 read-only 过渡视图和 contract 测试。
- 历史 Markdown 不做一次性逐字翻译。原因：风险高、收益低；当前策略是中文入口 + 维护审计 + `docs/archive/HISTORICAL_DOCS_SUMMARY.zh-CN.md` 摘要归档。
- Provider Validation Gate 不升级为 live provider endpoint。原因：provider smoke 仍必须 capability gate 显式打开。

## 新增本地 AgentOps artifact

| artifact_type | 用途 | 边界 |
|---|---|---|
| `agentflow_run_trace` | Runtime Service job 的输入、gate、产物、blocked refs、feedback 记录 | 不保存私有路径，不写长期记忆 |
| `agentflow_quality_report` | 本地结构/运行质量报告 | 不等于人工验收 |
| `agentflow_guardrail_result` | secret/provider/memory/prompt injection 等 guardrail 结果 | 不自动阻断所有任务，先作为证据 |
| `agentflow_handoff_record` | 当前任务交接摘要 | 不替代 DEVLOG/TASK_TRACKER |
| `agentflow_maintenance_audit_report` | 维护审计脚本输出 | 不等于代码质量最终结论 |

## 维护审计

新增脚本：

```powershell
.\.venv\Scripts\python.exe tools\maintenance_audit.py
```

默认行为：

- 输出 `agentflow_maintenance_audit_report` JSON。
- 默认不失败退出，便于先看完整风险。
- 如需把 failed 检查作为门禁：

```powershell
.\.venv\Scripts\python.exe tools\maintenance_audit.py --fail-on failed
```

当前检查：

- 旧 `Company` 源头路径或旧文案。
- 人类 Markdown 中文化覆盖；fenced code block 和 inline code 不计入比例，避免误伤机器契约。
- secret / signed URL / token-like 文本。
- 超过 300 行的非归档文本文件。
- 已被 Git 跟踪的 runtime artifact。

## 本轮中文化进展

已改为中文或中文短版的当前入口：

- `README.md`
- `AGENTS.md`
- `TASK_TRACKER.md`
- `DEVLOG.md`
- `docs/README.md`
- `docs/company_operating_model.md`
- `docs/frontend_integration/`
- `docs/local_internal_test_runbook.md`
- `docs/project_manifest_contract.md`
- `docs/handoff/AFS-LOCAL-INTERNAL-TEST-LANDING-001.md`
- `docs/handoff/AFS-RUNTIME-SERVICE-FRONTEND-INTEGRATION-001.md`
- `apps/api/README.md`
- `apps/web/README.md`
- `configs/README.md`
- `prompts/README.md`
- `skills/README.md`
- `workflows/README.md`

历史英文长文已通过 `docs/archive/HISTORICAL_DOCS_SUMMARY.zh-CN.md` 统一摘要归档。维护审计只在该摘要索引存在时豁免历史文档，避免把旧英文证据误认为当前产品文档。

## 验证命令

基础验证：

```powershell
.\.venv\Scripts\python.exe -m apps.cli.main --help
.\.venv\Scripts\python.exe -m apps.cli.main version
.\.venv\Scripts\python.exe -m pytest tests/test_agentflow_agentops_contracts.py tests/test_maintenance_audit.py tests/test_api_runtime_service.py tests/test_contract_examples.py tests/test_cli_command_registry_boundaries.py -q
.\.venv\Scripts\python.exe tools\maintenance_audit.py
.\.venv\Scripts\python.exe tools\repository_retention_review.py --root . --summary-only
git diff --check
```

最终验证：

```powershell
.\.venv\Scripts\python.exe -m pytest
git status --short
git branch -vv
git worktree list
```

当前最新验证：

```text
focused regression: 72 passed, 1 warning
maintenance focused regression: 8 passed
full pytest: 1015 passed, 1 warning
maintenance_audit: failed=0, passed=4, warning=2
maintenance_audit human_doc_chinese_coverage: passed, historical_docs_exempted_count=187, total_markdown_files=217
repository_retention_review: directory_count=82, file_count=997, delete_candidate_count=0, manual_review_required_count=0
git diff --check: passed, only LF-to-CRLF warnings
legacy Company path scan: no hits
```

## 回滚方式

- AgentOps contract 可单独回滚：移除 `agentflow/contracts/agentops.py`、五个 `examples/agentflow/agentops_*.json`、registry entries、Runtime Service trace 写入和对应测试。
- 维护审计可单独回滚：移除 `tools/maintenance_audit.py` 和 `tests/test_maintenance_audit.py`。
- 文档中文化可单独回滚到上一 commit，但不得恢复旧 `Company` 源头路径作为当前规则。

## 外部参考吸收方式

- LangGraph：借鉴 durable execution、human-in-the-loop、observability，不引入图框架。
- OpenAI Agents SDK：借鉴 Agent / Tool / Handoff / Guardrail / Tracing 五件套。
- OpenHands：借鉴 sandbox、REST API、本地 GUI、前后端分层。
- Dapr Agents / Restate：作为后续 COS durable runtime 方向，近期不引入。
- CrewAI：借鉴 role/task/tool/artifact/gate 分开声明。
- Promptfoo / Langfuse / AgentOps：借鉴 eval、trace、cost、prompt/version、feedback，不接 SaaS。
- FastAPI full-stack template：后端通过 OpenAPI 给前端对接。
- Agentic Workflow Injection 研究：后续 GitHub PR/Issue/comment 必须视为 untrusted input。

## 当前结论

本切片把 AFS 的维护方向固定为：

```text
先 contract
  -> 再 artifact
  -> 再 harness
  -> 再 trace
  -> 再本地 deterministic runtime
  -> 最后再打开 provider gate
```

所有通过项只代表 structure/runtime verification，不代表 human acceptance、business validation 或 durable memory。
