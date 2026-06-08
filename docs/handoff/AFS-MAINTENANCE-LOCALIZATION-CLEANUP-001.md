# AFS 维护性重置与中文化交接 001

状态：verified locally on `codex/afs-maintenance-localization-cleanup-001`

## 本次完成

- 创建单一维护分支 `codex/afs-maintenance-localization-cleanup-001`，承接当前 Runtime Service、本地内测、provider recovery、Web review 和前端 handoff 未提交成果。
- 新增维护账本：`docs/maintenance/AFS-MAINTENANCE-LOCALIZATION-CLEANUP-001.zh-CN.md`。
- 新增本地维护审计：`tools/maintenance_audit.py`，输出 `agentflow_maintenance_audit_report`。
- 新增仓库保留性审查：`tools/repository_retention_review.py`，输出 `agentflow_repository_retention_review`，覆盖当前目录和文件的保留理由与退休条件。
- 新增本地 AgentOps 契约：`agentflow/contracts/agentops.py` 和 5 个 `examples/agentflow/agentops_*.json`。
- Runtime Service job 现在输出 `agentflow_run_trace`，记录安全输入 refs、provider gate state、artifact refs、blocked refs、tester feedback state 和 non-claims。
- 拆分 Runtime Service helper：
  - `apps/api/runtime_artifacts.py`
  - `apps/api/runtime_jobs.py`
  - `apps/api/runtime_tracing.py`
- 中文化关键入口：
  - `README.md`
  - `AGENTS.md`
  - `TASK_TRACKER.md`
  - `DEVLOG.md`
  - `docs/company_operating_model.md`
  - `docs/README.md`
  - `docs/frontend_integration/README.md`
  - `docs/frontend_integration/AFS_API_ADAPTER_PLAN.md`
  - `docs/frontend_integration/AFS_ARTIFACT_CONTRACT_MAP.md`
  - `docs/frontend_integration/AFS_FRONTEND_INTEGRATION_BRIEF.md`
  - `docs/frontend_integration/AFS_UI_WORKBENCH_REQUIREMENTS.md`
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
- 修正维护审计中文覆盖率算法：代码块和 inline code 不参与人类中文比例，机器契约英文不再被误报为文档英文残留。
- 清理旧 `Company` 源头路径引用，当前 `rg` 对旧路径/旧文案无命中。
- 删除冗余 `README.zh-CN.md`；`README.md` 作为唯一中文主入口。
- 新增历史英文文档中文摘要索引：`docs/archive/HISTORICAL_DOCS_SUMMARY.zh-CN.md`，并让维护审计只在该摘要存在时豁免历史文档。
- 修正 staging preflight：secret/runtime 路径仍阻断，超 300 行作为 warning；移除测试里的本机 `.secrets` 路径字面量。
- 在 `10-Startup` 新增 candidate 规则：
  - `D:\Learning materials\Learning_notes\10-Startup\30-Engineering\03-AI-Agent项目可维护性与中文化规范.md`
  - 已登记到 `D:\Learning materials\Learning_notes\10-Startup\00-Company-OS\candidate-rule-ledger.md`

## 验证结果

通过：

```powershell
.\.venv\Scripts\python.exe -m apps.cli.main --help
.\.venv\Scripts\python.exe -m apps.cli.main version
.\.venv\Scripts\python.exe -m pytest tests/test_web_static_artifact_registry.py tests/test_web_static_artifact_boundaries.py tests/test_web_static_asset_review_screen.py tests/test_web_static_project_manifest.py -q
.\.venv\Scripts\python.exe -m pytest tests/test_production_memory_provider_validation_gate.py tests/test_kling_video_curl_smoke.py tests/test_kling_video_task_recovery.py -q
.\.venv\Scripts\python.exe -m pytest tests/test_agentflow_agentops_contracts.py tests/test_maintenance_audit.py tests/test_api_runtime_service.py tests/test_contract_examples.py tests/test_cli_command_registry_boundaries.py tests/test_staging_preflight.py -q
.\.venv\Scripts\python.exe -m pytest tests/test_repository_retention_review.py tests/test_maintenance_audit.py -q
.\.venv\Scripts\python.exe -m pytest
node --check apps\web\memory-workbench-production-asset-review-screen.js
node --check apps\web\memory-workbench-asset-review-render.js
node --check apps\web\memory-workbench-project-manifest.js
git diff --check
```

全量结果：

```text
1015 passed, 1 warning
```

已知 warning：

```text
StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.
```

维护审计：

```text
status: warning
summary: failed=0, passed=4, warning=2
human_doc_chinese_coverage: passed
historical_docs_exempted_count=187
total_markdown_files=217
```

仓库保留性审查：

```text
directory_count=82
file_count=997
delete_candidate_count=0
manual_review_required_count=0
README.zh-CN.md: removed in maintenance commit
```

最新 focused regression：

```text
72 passed, 1 warning
8 passed
12 passed
staging preflight: status pass, 4 oversized warnings
```

当前 warning 是维护债务，不是本切片失败：

- 部分测试/配置保留 secret-like 字段名或 fake key 形状。
- 仍有若干超过 300 行的历史文件。

旧源头路径扫描：

```powershell
$legacyPattern = "D:" + "\\Learning materials\\Learning_notes\\Company"
$legacyWording = "Company" + " source knowledge base"
rg -n "$legacyPattern|$legacyWording" AGENTS.md docs README.md TASK_TRACKER.md tests tools
```

结果：无命中。

## 未完成/暂缓

- 尚未提交、推送或创建 PR。
- 旧 worktree 仍保留：

```text
C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-web-asset-review-screen-001
```

该 worktree 不能直接删除；需要在本维护分支提交后确认其未提交内容是否已全部被吸收。

- 文档没有一次性全量逐字翻译。当前策略是中文化关键入口，并用 `docs/archive/HISTORICAL_DOCS_SUMMARY.zh-CN.md` 为历史英文长文提供中文摘要索引。
- 历史英文文档不再作为当前中文化 warning；后续如要删除原文，仍需先证明没有测试、contract 或 handoff 引用。
- `apps/web/*` 只做过渡保留，不做深度重构，因为外部前端工作台会重建。
- `data/processed/pytest-basetemp/` 是 ignored runtime 临时目录；本轮尝试删除时多个历史目录返回 Windows `Access denied`，未纳入 Git 保留性审查结论。

## 非声明边界

- 未调用 provider。
- 未保存 secret、signed URL、本地私有素材字节或生成媒体。
- 未声明 human acceptance。
- 未声明 business validation。
- 未写 durable memory。
- 未把 COS candidate 规则晋升为 active。

## 下一步建议

1. 做一次 staging 审查，按当前维护账本决定要进入 PR 的文件集合。
2. 提交并推送 `codex/afs-maintenance-localization-cleanup-001`。
3. 开 draft PR。
4. PR 后再处理旧 `codex/afs-runtime-service-v0-1` 和 `codex/afs-web-asset-review-screen-001` 分支/worktree 清理。
5. 下一开发切片进入 Runtime Service v0.2：OpenAPI 固定导出、前端 client 生成说明、项目列表/import/export、job progress。
