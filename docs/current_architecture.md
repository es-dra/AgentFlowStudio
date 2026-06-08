# 当前架构

本文是 AFS 当前工程基线的中文架构入口。旧 Alpha、Phase、Golden Path、编号 demo 和历史路线图不再作为当前任务入口。

## 当前定位

AgentFlow Studio 是本地优先的 Agent-native 内容生产工作台验证线。近期目标是本地内测可用，而不是 SaaS、商业试点或大规模 provider 平台。

当前工程主线：

```text
Runtime Service / CLI
  -> deterministic asset loop
  -> run trace / quality report / safe manifest
  -> read-only artifact review
  -> tester feedback
  -> candidate / promotion / context projection
  -> two-round runtime validation
```

所有通过项只代表结构验证或运行验证，不自动代表 human acceptance、business validation 或 durable memory。

## 代码分层

```text
apps/api/              Runtime Service，对前端的唯一正式后端对接面
apps/cli/              本地运维、deterministic harness 和 smoke 入口
apps/web/              过渡 read-only artifact viewer，不作为新 Web 基础
agentflow/             平台 contract、memory loop、harness、router、skills
agentflow_studio/      内容生产、分发、workflow、provider adapter
configs/               示例配置和 tool catalog contract
examples/              可提交 contract fixture
workflows/             YAML workflow definition
docs/                  当前中文入口、runbook、contract、维护账本
tests/                 自动化验证面
data/                  ignored runtime data，只保留 .gitkeep
```

## 正式对接面

前端只对接 Runtime Service：

```powershell
.\.venv\Scripts\python.exe -m apps.cli.main runtime-service --host 127.0.0.1 --port 8790
```

OpenAPI：

```text
http://127.0.0.1:8790/docs
http://127.0.0.1:8790/openapi.json
```

前端可使用：

- `project_id`
- `job_id`
- `artifact_id`
- safe summary
- safe manifest
- OpenAPI request / response fixture

前端不应接触：

- CLI 内部编排。
- provider secret。
- 本地素材绝对路径。
- signed URL。
- provider 原始响应。
- 私有素材字节或生成媒体字节。

## 当前核心能力

- Production Memory asset loop。
- Asset Profile Review Screen。
- Real Asset Test Run Harness。
- Two-Round Context Runtime Validation。
- Project Manifest v0.1。
- Provider Validation Gate。
- Runtime Service v0.2 前端 contract。
- 本地轻量 AgentOps artifact：run trace、quality report、guardrail result、handoff record、maintenance audit report。

## 质量与治理边界

- provider 默认关闭，按能力显式 gate。
- feedback 是 raw evidence，不自动成为 memory。
- candidate 不是 durable memory。
- blocked refs 必须保留原因，并且不能进入下一轮 context。
- Runtime Service 输出 safe refs，不暴露私有路径或 secret。
- 维护清理先记录账本，再删除；已验证退出主线的旧 demo 和旧文档直接删除。

## 下一阶段

进入轻量 Web 和完整流程跑通前，应先完成低成本维护基线：

```text
维护门禁通过
  -> repository retention review 无 delete/manual blocker
  -> deterministic Loulan/fixture full loop
  -> Runtime Service/OpenAPI 对齐
  -> 简单 Web 工作台
  -> provider smoke gate
```
