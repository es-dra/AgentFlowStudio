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

本切片把仓库压回一条清晰产品主干：

```text
agentflow contracts / harness / memory / agentops
  -> agentflow_studio production pipeline / provider adapters
  -> apps/api Runtime Service
  -> frontend-safe refs and artifacts
```

旧 demo、旧 bridge、旧 production-mode Web、旧 Alpha 文档、旧逐节点 handoff 和隐藏旧 CLI，如果不服务当前产品主干，直接删除，不再迁移或归档。

## 非目标

- 不调用 live provider。
- 不提交 runtime media、secret、signed URL 或 provider 原始响应。
- 不把 COS candidate 规则晋升为 active。
- 不声明 human acceptance、business validation 或 durable memory。

## 已执行删除

### 旧 Web bridge

删除：

```text
apps/web_bridge/
tests/test_web_production_bridge.py
```

CLI 变化：

```text
web-bridge retired, not hidden
```

Runtime Service 是前端唯一主对接面。

### 旧 Web Production Mode

删除：

```text
apps/web/app-shell-production-template.js
apps/web/production-bridge-client.js
apps/web/production-mode-buttons.js
apps/web/production-mode.js
apps/web/production-render.js
apps/web/production-workflows.js
apps/web/production.css
tests/test_web_production_feedback_static.py
tests/test_web_production_mode_static.py
```

`apps/web` 仅保留 read-only / local-only artifact viewer。

### 旧 Alpha / Web / Demo 文档面

删除：

```text
docs/local_alpha_0_*.md
docs/task_briefs/AFS-ALPHA-*.md
docs/task_briefs/AFS-WEB-*.md
docs/task_briefs/AFS-MEMORY-*.md
docs/task_briefs/AFS-POSTER-*.md
docs/task_briefs/AFS-PROD-*.md
docs/workbench/web_workbench_reference.md
docs/workbench/web_workbench_milestones.md
```

### 旧 handoff 面

`docs/handoff` 直接删除旧 demo、competition、Company KB、generic Production
Memory operator node handoff。当前仅保留：

```text
AFS-LOCAL-INTERNAL-TEST-LANDING-001.md
AFS-RUNTIME-SERVICE-FRONTEND-INTEGRATION-001.md
AFS-RUNTIME-SERVICE-V0-2-FRONTEND-CONTRACT-001.md
AFS-PRODUCTION-MEMORY-ASSET-*.md
INDEX.md
```

### Contract 命名收敛

保留仍有测试价值的 `agentflow_memory_evidence_reuse_review` contract，但将旧
`local_alpha_0_4` 命名改为通用 `production_memory` 命名。

### Retention Review 策略

`tools/repository_retention_policy.py` 更新：

- Git 已删除文件统一标记为 `remove_applied_pending_stage`。
- `apps/web_bridge` 重新出现时仍标记为删除候选。

## 验证状态

已通过：

```text
CLI help 可运行
CLI version: 0.1.0
focused pytest: 56 passed
Web JS syntax checks: passed
maintenance_audit: failed=0, passed=4, warning=2
repository_retention_review: delete_candidate_count=0, manual_review_required_count=0, remove_applied_pending_stage=132
full pytest: 992 passed, 1 warning
git diff --check: passed
```

最终提交前仍需完成：

```powershell
git diff --check
```

## 下一步

本切片提交后，下一刀做循环依赖：

```text
agentflow_studio.model_gateway <-> agentflow_studio.production
agentflow_studio.harness <-> agentflow_studio.workflow_engine
```

拆分原则：

- provider error contract 下沉到 shared 层；
- workflow contract 下沉到 shared 层；
- architecture gate 移除对应 known cycle；
- 每一刀先测试，再拆分，再回归。
