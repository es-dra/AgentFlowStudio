# AgentFlow Studio Docs

中文摘要：本目录是当前 AFS 文档入口。新任务应从本文件、`TASK_TRACKER.md`、当前架构文档和最新 handoff 开始，不再从旧 Web、旧 Workbench、历史 RC 或过期浏览器 QA 文档恢复上下文。仓库只保存工程实现、接口、测试、safe artifact 和安全摘要；详细算法讨论、专利候选点和公司知识沉淀应留在 `10-Startup` 私有知识库，不写入公开 repo 投影。

保留理由：本文负责把当前可执行入口收敛到少数文件，降低维护成本。后续如果某份文档没有被这里、任务跟踪、测试命令或架构说明引用，就不再默认归档，而是按收口规则删除。任何 provider、模型或媒体相关结论，都必须带 gate、测试证据和非声明边界。

This directory is the current documentation entrypoint. Start new work from this
file, `TASK_TRACKER.md`, and the current architecture docs. Do not resume from
retired Web/Workbench handoffs or old smoke logs.

## Current Required Reading

- [Company operating projection](company_operating_model.md)
- [Current architecture](current_architecture.md)
- [Project Manifest contract](project_manifest_contract.md)
- [Task tracker](../TASK_TRACKER.md)
- [Devlog](../DEVLOG.md)

## Current Product Surface

- [AFS Studio frontend architecture](architecture/AFS_STUDIO_FRONTEND_ARCHITECTURE_V1.zh-CN.md)
- Current Web entry: `http://127.0.0.1:8790/studio/`
- Current frontend source: `apps/studio/`

AFS Studio is the only current user-facing frontend. Retired Workbench and
static memory-workbench paths are not task entrypoints.

## Architecture And Contracts

- [Current architecture](current_architecture.md)
- [Node prompt optimizer contract](architecture/AFS_NODE_PROMPT_OPTIMIZER_CONTRACT.zh-CN.md)
- [Creative intent control agent engineering summary](architecture/AFS_CREATIVE_INTENT_CONTROL_AGENT_ENGINEERING_SUMMARY.zh-CN.md)
- [Production Memory architecture](architecture/production_memory_architecture.md)
- [Production Memory Asset Profile](architecture/production_memory_asset_profiles.md)
- [Skill contract](agentflow_skill_contract.md)
- [Router contract](agentflow_router_contract.md)

## Useful Commands

```powershell
.\.venv\Scripts\python.exe -m apps.cli.main --help
.\.venv\Scripts\python.exe -m apps.cli.main version
.\.venv\Scripts\python.exe -m pytest
git diff --check
```

Maintenance cleanup:

```powershell
.\.venv\Scripts\python.exe tools\maintenance_audit.py
```

Runtime Service:

```powershell
.\.venv\Scripts\python.exe -m apps.cli.main runtime-service --host 127.0.0.1 --port 8790
```

OpenAPI:

```text
http://127.0.0.1:8790/docs
http://127.0.0.1:8790/openapi.json
docs/openapi/afs-runtime-service.openapi.json
```

## Cleanup Policy

Old, unused, or misleading docs should be deleted once replacement paths and
tests are clear. Keep only current architecture, contract, verification, and
handoff material that helps land the MVP.
