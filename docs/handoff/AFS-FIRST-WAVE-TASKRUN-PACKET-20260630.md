# AFS 第一波 TaskRun Packet - 2026-06-30

## 范围

本文关闭 AgentFlow Studio 第一波工程启动任务。它只负责 startup scan、
真实状态修正、第一波任务包和交接记录，不是功能开发任务。

## 项目状态

- 产品定位：AFS 是 AI 原生漫剧 / 视频 / 图片内容生产工作台。目标导向执行、
  worktree、技能、自动化和 eval loop 只作为工程机制，不改写产品身份。
- 分支状态：本地 AFS repo 位于 `master...origin/master`，HEAD 为
  `ed292f6b752c9150e9a4b9a85fccdcfef5135b14`。
- AFS 既有脏改：`docs/demo-docs-20260629/` 是进入本轮前已存在的未跟踪目录，
  本轮不读取、不清理、不提交。
- Source KB 既有脏改：`D:\Learning materials\Learning_notes` 位于
  `codex/cos-evidence-promotion-v03...origin/master [ahead 3]`，存在
  `.obsidian`、Week Planner、Company OS、workflow adapter 和项目包相关既有改动。
- 当前证据等级：仅为 `structure_verified`。Runtime health、provider smoke、
  human acceptance、business validation 和 memory promotion 都不是本轮声明。

## Dirty Ownership Ledger

| 分类 | 路径 / 表面 | 归属判断 |
|---|---|---|
| 既有脏改 | `D:\Projects\AgentFlowStudio\docs\demo-docs-20260629/` | 本轮不触碰。 |
| 既有脏改 | `D:\Learning materials\Learning_notes\.obsidian\workspace.json` | 本轮不触碰。 |
| 既有脏改 | `D:\Learning materials\Learning_notes\Week Planner\2026\2026-06\2026-06 plan.md` | 本轮不触碰。 |
| 既有脏改 | `D:\Learning materials\Learning_notes\Week Planner\2026\2026-06\月末总结.md` | 本轮不触碰。 |
| 既有脏改 / 需复核 | `10-Startup\00-Company-OS\` 下已修改文件 | 本轮不 stage、不清理、不晋升。 |
| 既有项目包 | `10-Startup\70-Projects\AI-Native-Project-Books\2026-06-30-COS-AFS-autonomous-project-book\` | 本轮只更新 execution state。 |
| 本轮拥有 | `AFS-Goal-Driven-Execution-State-v0.1.yaml` | 写入真实 repo 状态和 packet 路径。 |
| 本轮拥有 | `docs/handoff/AFS-FIRST-WAVE-TASKRUN-PACKET-20260630.md` | 保留为第一波任务包和交接。 |
| 本轮拥有 | `DEVLOG.md`、`docs/handoff/INDEX.md` | 保留为项目本地记录和索引。 |

## 已确认主入口

- Runtime Service：`apps/api/runtime_service.py`，FastAPI 入口，包含 `/health`、
  Studio 静态服务、auth/runtime 路由和安全 Runtime 边界模块。
- OpenAPI：`docs/openapi/afs-runtime-service.openapi.json`，OpenAPI `3.1.0`，
  标题 `AgentFlow Runtime Service`，版本 `0.2.0`，共 34 个路径。
- Studio：`apps/studio/`，当前用户入口为 `/studio/`；根 `package.json` 提供
  `npm.cmd run check:studio-js`。
- Algorithms：`agentflow/algorithms/`，包含资产卡草稿、上下文解析、创作意图控制、
  fixed asset memory、provider gate manifest、request projection、revision drift
  control、skill action selection、visual understanding 和 quality feedback scoring。
- Python / test contract：`pyproject.toml` 声明 Python `>=3.11,<3.13`、包版本
  `0.1.0`，默认 pytest 排除 `legacy`。
- 当前交接入口：`docs/handoff/INDEX.md` 指向活跃 Studio、Runtime、内测和维护证据；
  旧 Workbench / 旧静态 Web 不是当前入口。

## 第一波 TaskRun Packet

- Task IDs：`AFS-T0 Startup Scan`；相邻只读上下文为 `AFS-T1 Product Scope` 和
  `AFS-T2 Runtime Contract`。
- Objective：冻结真实仓库状态、dirty ownership、Runtime / Studio / OpenAPI /
  algorithm 入口，并在功能开发前留下可验证交接。
- Read scope：AFS repo 规则与文档、2026-06-30 项目包、`pyproject.toml`、
  Runtime Service 入口、OpenAPI snapshot、Studio 目录、algorithm library 目录、
  AFS 与 Learning_notes 的 git 状态。
- Write scope：本文、`DEVLOG.md`、`docs/handoff/INDEX.md`、
  `AFS-Goal-Driven-Execution-State-v0.1.yaml`。
- Non-goals：不改 Runtime / Studio / 产品代码，不破坏 schema，不调用 provider，
  不 commit / push / deploy，不 external download，不晋升 COS active rule，不声明
  human acceptance 或 business validation。
- Provider / tool gates：所有远程 provider 本轮保持关闭；commit / push 需要人工授权。
- Verification route：CLI help、CLI version、maintenance audit、Studio JS check、
  `git diff --check`。
- Evidence target：`structure_verified`。
- Cleanup requirement：只分类本轮记录文件；不清理既有 demo docs、Week Planner、
  `.obsidian`、Company OS 源头改动、provider config 或运行/生成 artifact。
- Handoff path：本文。
- Stop conditions：需要 secret/provider/customer/cost；dirty ownership 影响安全编辑；
  需要 provider/video 授权；需要 commit/push/deploy；需要公开、商业或人工验收声明；
  cleanup 触及公共 API、schema、provider adapter、用户数据或既有生产行为。

## 已完成工作

- 已读取：`AGENTS.md`、`README.md`、`docs/company_operating_model.md`、
  `TASK_TRACKER.md`、`docs/handoff/INDEX.md`、
  `docs/GFR_EXECUTION_PROJECTION.md`、项目包 v0.1、`pyproject.toml`、
  `apps/api/runtime_service.py`、`docs/openapi/afs-runtime-service.openapi.json`、
  `apps/studio/` 和 `agentflow/algorithms/`。
- 已修改：本文、`DEVLOG.md`、`docs/handoff/INDEX.md`、
  `AFS-Goal-Driven-Execution-State-v0.1.yaml`。
- Execution state：已在 `AFS-Goal-Driven-Execution-State-v0.1.yaml` 写入真实状态、
  first-wave packet 路径、cleanup review 和下一步。
- Cleanup review：本轮新增记录文件保留；没有新增重复 route、schema、component、
  adapter、fixture、prompt、provider path 或临时代码路径。
- COS feedback candidate：不创建。现有规则已经覆盖本轮启动行为。

## 验证

```text
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe tools\maintenance_audit.py
# failed=0; status=warning; passed=3; warning=4
# human_doc_chinese_coverage=22, all tracked
# oversized_files=59, source_summary tracked=57 and untracked=2
# secret_like_fragments=9, high_confidence_count=0

npm.cmd run check:studio-js
# JS syntax check passed: 125 files

git diff --check
# passed

YAML parse check for AFS-Goal-Driven-Execution-State-v0.1.yaml
# evidence_state=structure_verified
# cleanup_status=completed_for_first_wave_startup_records
# feedback_status=none_needed_for_first_wave
```

## 下一步

下一轮应单独为 `AFS-T1 Product Scope` 或 `AFS-T2 Runtime Contract` 编译 TaskRun。
在新的读写范围、验证路径、cleanup review 和 human gate 明确前，不进入大范围功能开发。
