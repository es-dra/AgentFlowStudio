---
doc_type: maintenance_ledger
status: verified
last_updated: 2026-06-09
owner_role: Maintainability Steward + Architecture Reset Lead
branch: codex/afs-oversized-maintenance-closure-001
work_mode: Deep
confidentiality: internal
---

# AFS Oversized Maintenance Closure 001

## 目标

本轮是低成本维护基线的最后收口，不以保护历史功能为目标，而以保护 Agent-native 工程主线的未来可维护性为目标。

保留标准：

```text
Runtime Service
Production Memory Asset Loop
Project Manifest
Provider Gate
maintenance audit
read-only artifact viewer
纯切片与内容制作 workflow
```

不服务这些主线、且没有当前测试或当前文档依赖的旧 demo、旧 handoff、旧 Web surface、旧 pipeline，直接删除。

## 身份与工作模式

- 主身份：Maintainability Steward + Architecture Reset Lead。
- 辅助身份：Runtime/API Integrator、Production Memory Steward、QA/Release Gatekeeper、Company OS Feedback Curator。
- 工作模式：Deep。原因是涉及 workflow registry、tool catalog、harness、CLI、测试、维护账本和验证门槛。
- 多 agent 策略：不并行启动多个写入 agent 修改同一工作树；用多角色审查框架组织判断。如需外部审查，只使用只读审查任务。

## ETCLOVG 映射

| 层 | 本轮处理 |
|---|---|
| Execution | 删除退休后处理 workflow，拆分超长核心模块，保持切片/内容制作主线可执行。 |
| Tooling | 收窄 workflow node registry 与 static tool catalog，不再暴露旧成片交付工具。 |
| Context | 以 AGENTS、Company OS、TASK_TRACKER 和本账本为约束，不把 COS 私有内容写入仓库。 |
| Lifecycle | 更新 TASK_TRACKER、DEVLOG/维护账本、Company OS feedback packet。 |
| Observability | 以 maintenance_audit、pytest、git diff --check 作为证据。 |
| Verification | 运行 CLI help/version、审计、focused pytest、必要时全量 pytest。 |
| Governance | provider 默认关闭；不写入 secret、signed URL、本地私有素材、provider 原始响应；不自动晋升 COS 规则。 |

## 当前审计基线

2026-06-09 当前分支 `codex/afs-oversized-maintenance-closure-001`。

`tools/maintenance_audit.py` 当前结果：

```text
failed=0
passed=5
warning=1
oversized_files=14
```

当前 oversized warning：

- `agentflow/memory/agentflow_production_assets.py`：306 行。
- `agentflow/memory/production_acceptance_feedback_candidate_overlay.py`：303 行。
- `agentflow/memory/production_asset_consistency_review.py`：335 行。
- `agentflow/memory/production_asset_profiles.py`：311 行。
- `agentflow/memory/production_operator_run_package.py`：310 行。
- `agentflow/memory/promotion.py`：311 行。
- `agentflow_studio/harness/agentflow_production_quality.py`：314 行。
- `agentflow_studio/harness/package_quality.py`：331 行。
- `agentflow_studio/harness/reviewer.py`：353 行。
- `agentflow_studio/harness/video_artifacts.py`：329 行。
- `agentflow_studio/package_sop/report.py`：330 行。
- `agentflow_studio/workflow_engine/highlight_nodes.py`：344 行。
- `apps/cli/production_memory_operator_command.py`：309 行。
- `examples/agentflow/contract_audit_report.example.json`：305 行。

## 本轮直接删除标准

以下类型不再维护：

- 成片拼接、字幕烧录、BGM 混音、封面导出、finished package、delivery readiness 生成链路。
- 以 finished package 为主入口的旧 YAML workflow。
- 只服务上述链路的 demo input、tool catalog 条目、workflow node、SOP、harness quality profile、CLI 命令和测试。

保留边界：

- `apps/web` 的 read-only artifact viewer 可以继续识别历史 artifact 文件名，但不能因此保留旧生成 pipeline。
- `subtitle_sop` 的纯字幕导出如果仍服务切片/高亮计划，可保留；`subtitle_burn_sop` 属于成片后处理，删除。
- `video_artifacts.py` 如服务纯切片/真实 clip 质量检查，保留或拆分，不按旧成片逻辑删除。

## 当前处理计划

1. 删除退休后处理 workflow、SOP、node registry、tool catalog、CLI 命令和对应测试。
2. 拆分或删除剩余 oversized 文件；合理保留的 fixture/schema/example 必须写明原因。
3. 更新 workflow README、TASK_TRACKER、Company OS feedback packet。
4. 运行验证门槛。

## 验证门槛

```powershell
.\.venv\Scripts\python.exe -m apps.cli.main --help
.\.venv\Scripts\python.exe -m apps.cli.main version
.\.venv\Scripts\python.exe tools\maintenance_audit.py
.\.venv\Scripts\python.exe -m pytest <focused tests> -q
.\.venv\Scripts\python.exe -m pytest
git diff --check
```

## 执行结果

截至 2026-06-09 本轮收口分支：

- `maintenance_audit`: `failed=0, passed=6, warning=0`。
- `oversized_files`: 从本轮接手时的 24 个历史债务清到 0 个。
- 本轮相对当前 `master` staged 统计：新增 2,496 行，删除 11,196 行，净删减 8,700 行。
- 当前项目统计：747 个文本文件约 83,328 行。

删除范围：

- 退休成片后处理链路：assembly、subtitle export、subtitle burn、BGM、cover、finished package、delivery readiness。
- 对应旧 workflow YAML、demo input、SOP、workflow node、harness quality profile、tool catalog entry、CLI report command 和测试。
- 不再把这些历史表面迁移、归档或兼容保留。

拆分范围：

- Production Memory Asset Loop：asset validation、promotion checks、operator run package render、acceptance overlay validation、asset consistency validation、asset profile seed validation。
- Harness / workflow engine：video artifact review、review recommendations、production quality review、highlight node input parsing。
- CLI：production memory operator command 保留 Typer 参数声明，执行主体下沉到 runner。

保留理由：

- Runtime Service、Production Memory Asset Loop、Project Manifest、Provider Gate、maintenance audit、read-only artifact viewer、纯切片和内容制作 workflow 是当前 Agent-native 工程基线的一部分。
- `examples/agentflow/contract_audit_report.example.json` 是 contract registry 的静态审计示例，字段仍有验证价值；本轮只做无语义排版压缩并降到审计阈值内。
- read-only artifact viewer 可继续识别既有 artifact shape，但不反向要求保留旧生成 pipeline。

维护性判断：

当前主线已经达到低维护成本基线：审计无失败和无 warning，旧后处理链路不再占据测试、CLI、workflow registry、tool catalog 或 SOP 面，剩余核心模块按职责拆分，后续开发可以围绕 Runtime Service / Production Memory Asset Loop / Project Manifest / Provider Gate / read-only artifact viewer / 纯切片和内容制作 workflow 继续推进。

## Claim Boundary

- 本账本记录工程维护证据，不代表 human acceptance。
- deterministic test pass 不代表 business validation。
- Company OS feedback packet 只能作为 candidate feedback，不自动晋升 active rule。
