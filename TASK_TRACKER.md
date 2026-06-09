# AgentFlow Studio 任务账本

最后更新：2026-06-09 by Codex

本文件只保留当前工作、下一步队列、阻塞项和证据入口。旧 Alpha、旧 Web
bridge、旧 demo 和旧逐节点 handoff 不再作为当前任务入口。

公司源头知识库：

```text
D:\Learning materials\Learning_notes\10-Startup
```

AFS 仓库只保存执行投影：代码、contract、测试、runbook、维护账本和前端安全对接材料。

## 当前操作规则

- 不再新增编号式 memory advantage demo 模块。
- 不再恢复 `apps/web_bridge` 或 `web-bridge` CLI。
- provider smoke、deterministic tests、human acceptance、business validation、durable memory 必须分开。
- 不提交 secret、provider key、signed URL、cookie、本地媒体、模型缓存、生成 runtime artifact 或公司私密资料。
- 远程 provider 调用必须按能力显式 gate。

## 当前工作

| ID | Owner role | 范围 | 状态 | 证据 |
|---|---|---|---|---|
| AFS-MAINTENANCE-CLOSEOUT-001 | Maintainability Steward + Frontend Contract Steward | 强删旧 demo / Alpha / memory video pipeline / 旧 Web sample，调精维护审计，收紧当前 product spine | 已完成 | `docs/maintenance/AFS-MAINTENANCE-CLOSEOUT-001.zh-CN.md` |
| AFS-MAINTENANCE-DEBT-CLOSURE-001 | Architecture Reset Lead + QA / Release Gatekeeper | 解除剩余包级循环、收紧架构门禁、新增 CI 维护门禁 | 已完成 | `docs/maintenance/AFS-MAINTENANCE-DEBT-CLOSURE-001.zh-CN.md` |
| AFS-MODEL-GATEWAY-CYCLE-001 | Architecture Reset Lead | 解除 `agentflow_studio.model_gateway <-> agentflow_studio.production` 循环 | 已完成 | `docs/maintenance/AFS-MODEL-GATEWAY-CYCLE-001.zh-CN.md` |
| AFS-PRODUCT-SPINE-RESET-003 | Maintainability Steward + Architecture Reset Lead | 删除旧入口、压缩历史文档面、强化 retention review、消除旧包/CLI/Web surface | 已提交 | `docs/maintenance/AFS-PRODUCT-SPINE-RESET-003.zh-CN.md` |
| AFS-RUNTIME-SERVICE-V0-2-001 | Runtime/API Integrator + Frontend Contract Steward | Runtime Service、OpenAPI、frontend-safe refs、request fixture | 已合入基线 | `docs/frontend_integration/`；`docs/handoff/AFS-RUNTIME-SERVICE-V0-2-FRONTEND-CONTRACT-001.md` |
| AFS-LANDING-PREP-CONTENT-MEMORY-WEB-001 | AI-Native Operating Architect + Product / Engineering Orchestrator | 内容制作 / 记忆链路 Runtime Service 跑通证据、外部画布参考、Web 与后端协同开发规划 | 规划完成 | `docs/handoff/AFS-LANDING-PREP-CONTENT-MEMORY-WEB-001.md` |
| AFS-FRONTEND-WORKBENCH-INTEGRATION-001 | Product Integration Steward + Runtime/API Integrator | 外部画布前端接 Runtime Service，首屏只做 project、run、artifact、review safe view | 排队 | 前端不接触 CLI 内部、secret、私有路径、signed URL 或媒体字节 |

## 当前基线

| 模块 | 状态 | 证据 |
|---|---|---|
| Git | 当前分支 `codex/afs-landing-prep-web-plan-001` | `git status --short --branch` |
| Production Memory Asset Loop | deterministic 本地 contract chain 已具备 | `agentflow/memory/`；`apps/cli/production_memory_command_registry.py` |
| Runtime Service | 前端主对接面 | `apps/api/`；`apps/cli/runtime_service_command.py` |
| 过渡 Web | 只保留 read-only / local-only artifact viewer | `apps/web/README.md` |
| 维护审计 | 本地维护审计和 retention review 可运行 | `tools/maintenance_audit.py`；`tools/repository_retention_review.py` |

## 下一步队列

| ID | 范围 | 状态 |
|---|---|---|
| AFS-FLOW-RUN-READY-001 | 基于当前低成本维护基线，进入自研轻量 Web 前的流程跑通准备 | 已完成首轮 Runtime Service 链路证据；下一步补 workbench-state adapter |
| AFS-WORKBENCH-STATE-ADAPTER-001 | Web 实现前补 Runtime Service UI state、canvas card、blocker、action vocabulary、event history 和 safe preview contract | 已完成首轮实现；`tests/test_api_runtime_workbench_state.py` |
| AFS-WEB-FOUNDATION-001 | 新自研轻量 Web 基础：runtime client、state adapter、app shell、project hub、workspace layout、Runtime-hosted entry | 已完成基础壳；`apps/workbench`、`/workbench/`、`tests/test_web_workbench_foundation.py` |
| AFS-WEB-PROJECT-SETUP-001 | Project Hub / setup / asset-reference library：项目创建、导入导出、目标平台、素材和参考入口 | 进行中：create/open/import/export、asset/reference library、source presets 和 Draft Canvas 入口已落地 |
| AFS-WEB-CREATION-WORKSPACE-001 | 创作画布主工作区：scene/content cards、inspector、filmstrip、first generation check | 进行中：Draft Canvas、scene/content cards、Inspector、filmstrip、first generation check control、safe artifact panel 和 Review Room candidate comparison 已落地 |
| AFS-WEB-REVIEW-STYLE-MEMORY-001 | 审片反馈与 Project Style Memory：keep/revise/reject、raw feedback、下一轮复用 | 进行中：raw feedback、keep/revise/reject、candidate-bound review decisions、Style Memory product view 和 next-round controls 已落地 |
| AFS-PROVIDER-GATED-REAL-SMOKE-001 | deterministic Web flow 稳定后，再按 capability gate 接真实模型 smoke | readiness-only gate 已跑通并写入 ignored runtime evidence：`data/processed/runs/web_rc_provider_gate_readiness/`；provider calls 未启动；仍需先完成人工验收，再由用户显式授权 image/video gate |
| AFS-WEB-QA-RELEASE-GATE-001 | 浏览器截图、响应式检查、HTTP smoke、focused tests、maintenance audit、diff check | 发布候选 QA 已完成：Stage 7 浏览器主路径、1440x900 / 1366x768 / 390x844 截图、console/internal-leak/text-overflow 检查和 provider-gated 边界记录已落地 |
| AFS-WEB-HUMAN-ACCEPTANCE-001 | 人工验收当前 Web release candidate，确认项目 -> 素材 -> 画布 -> 分镜 -> 审片 -> 记忆 -> 任务路径是否符合低学习成本创作工作台定位 | 待人工验收：验收包已落地到 `docs/frontend_integration/AFS_WEB_RELEASE_CANDIDATE_ACCEPTANCE_PACKET.zh-CN.md`，可视化演示索引已落地到 `docs/frontend_integration/AFS_WEB_RC_DEMO_INDEX.zh-CN.html`，draft PR handoff 已落地到 `docs/handoff/AFS-WEB-RC-DRAFT-PR-001.md` |

## 当前阻塞和残留

- `maintenance_audit` 的 secret-like warning 和 oversized warning 已清零；后续触碰模块时仍按 300 行理想线继续拆分。
- Hidden CLI support commands 仍是兼容支持面；删除前必须做独立 CLI 协议迁移。
- Provider validation 默认关闭，除非显式授权对应 capability gate。
- 维护审计当前为通过状态；新的前端模块仍按单职责和 300 行理想线维护。
- 当前 Web release candidate 还没有人工验收结论；不得把 Stage 7 浏览器 QA 说成 human acceptance。
- Provider smoke 准备包已落地，但尚未执行；不得把 readiness-only plan 说成真实模型接入成功。

## 2026-06-09 - Oversized Maintenance Closure 001

| ID | Owner role | 范围 | 状态 | 证据 |
|---|---|---|---|---|
| AFS-OVERSIZED-MAINTENANCE-CLOSURE-001 | Maintainability Steward + Architecture Reset Lead | 删除退休成片后处理 surfaces，拆分剩余超长核心文件，清零 `maintenance_audit` oversized warning | 验证中 | `docs/maintenance/AFS-OVERSIZED-MAINTENANCE-CLOSURE-001.zh-CN.md` |

当前边界：

- 保留 Runtime Service、Production Memory Asset Loop、Project Manifest、Provider Gate、maintenance audit、read-only artifact viewer、纯切片与内容制作 workflow。
- 直接删除不再服务主线的 BGM、cover、subtitle burn、final package、delivery readiness 等后处理 pipeline、demo、SOP、旧测试。
- 本轮不写入 COS active rule；只生成 project-local Company OS feedback candidate packet。
- provider 默认关闭；未写入 secret、signed URL、本地私有素材、provider 原始响应或生成媒体字节。
最终验证：CLI help/version、`maintenance_audit`、focused pytest、full pytest、`git diff --check` 已通过；`oversized_files=0`。

## 2026-06-09 - Web Workbench Industrialization Update

Current branch:

```text
codex/afs-landing-prep-web-plan-001
```

Current Web/API queue state:

| ID | Scope | Status |
|---|---|---|
| AFS-WEB-RUNTIME-HOSTED-ENTRY-001 | Serve Workbench through Runtime Service for same-origin frontend/backend integration | Landed: `/workbench/` and `/workbench/src/app.js` served from a temporary Runtime Service smoke |
| AFS-WEB-DRAFT-CANVAS-001 | Draft Hook / Proof / CTA canvas cards from safe source summaries | Landed: `POST /projects/{project_id}/canvas-draft`, Workbench `Draft Canvas`, OpenAPI export |
| AFS-WEB-PROJECT-SETUP-001 | Project Hub, setup, asset/reference library | In progress: create/open/import/export, safe asset/reference summary registration, Reference Library panel, Project Hub templates, and source-type presets landed |
| AFS-WEB-CREATION-WORKSPACE-001 | Creation workspace, scene/content cards, inspector, filmstrip, first generation check | In progress: safe scene/content card registration, backend `creation_workspace` projection, split Creation Workspace renderer/state/CSS, inspector, filmstrip, first generation control, safe artifact report panel, and Review Room candidate comparison landed |
| AFS-WEB-REVIEW-STYLE-MEMORY-001 | Review feedback into project style memory | In progress: backend `memory_workspace` projection, review candidates, feedback controls, style profile reuse, next-round controls, and split memory renderer/state landed |
| AFS-WEB-OPERATIONS-WORKSPACE-001 | Runtime operations, provider preflight, and job/activity navigation | Landed in current branch: backend `operations_workspace` projection, frontend Operations Workspace panel, provider controls, and split operations state/render modules |
| AFS-WEB-JOB-CENTER-001 | Runtime job progress, blocker guidance, and artifact navigation | In progress: backend `job_center` projection, frontend Job Center view, artifact navigation, and auto-refresh polling landed |
| AFS-WEB-PROJECT-READINESS-001 | Project readiness, next action, and visible workflow gates | Landed: backend `project_readiness`, frontend Project Readiness panel, action mapping, and split readiness CSS |
| AFS-WEB-STAGE-NAVIGATION-001 | Stage-based Workbench navigation and view-specific control groups | Landed: `activeView`, functional rail navigation, and grouped action panel rendering |
| AFS-WEB-ACTIVITY-TIMELINE-001 | Runtime activity timeline, blocker visibility, and safe artifact navigation | Landed: backend `activity_timeline`, frontend Activity Timeline panel, safe primary artifact refs, and split activity modules |
| AFS-WEB-PRODUCTION-BOARD-001 | Product-facing source -> draft -> check -> review -> style memory -> next round -> provider gate board | Landed: backend `production_board`, frontend Production Board panel, 7-lane flow state, and split board modules |
| AFS-WEB-COMMAND-HUB-001 | User-facing next command, action mapping, required input hints, and provider gate blocker visibility | Landed: backend `command_hub`, frontend Command Hub panel, action mapping, and split command modules |
| AFS-WEB-PROJECT-HUB-001 | Product-facing active project summary, safe counts, next command, and recent job navigation | Landed in current branch: backend `project_hub`, frontend Project Hub panel, state adapter, and split CSS |
| AFS-WEB-STUDIO-WORKSPACE-001 | 将 Create 视图改为产品化 Studio Workspace：统一承载画布、素材参考、风格记忆、审片队列、runtime 摘要和 safe artifact 导航 | 已在当前分支落地：后端 `studio_workspace`、前端 Studio Workspace 面板、state adapter 和独立 CSS |
| AFS-WEB-VERTICAL-FLOW-001 | Workbench deterministic 纵向主路径：从空项目到 ready_for_next_round，不接触 CLI 或手写 JSON | 已完成浏览器级主路径证据：API vertical flow、mutation `flow` summary、空工作区创建入口、Review decision 主入口、Production Board 全宽布局、Playwright browser smoke 到 `ready_for_next_round` |
| AFS-WEB-UX-REFOUNDATION-001 | 将 Workbench 从工程状态面板重构为中文多工作区创作应用：项目、创作画布、素材库、分镜台、审片室、项目记忆、任务中心、诊断 | 阶段 0-7 已落地到发布候选：中文 IA/术语/QA 账本、多工作区外壳、项目设置向导、创作画布节点流、素材库分组、独立分镜台、独立审片室、独立项目记忆、任务中心、Provider Gate、Runtime 中文显示适配、no-store 静态入口、浏览器主路径和响应式截图 QA 已完成；下一步进入人工验收和 provider-gated smoke 前置整理 |

Verification so far:

- Latest focused Web/API verification after Reference Library and polling extension:
  `.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_service_v02.py tests\test_api_runtime_workbench_state.py tests\test_web_workbench_foundation.py -q`
- Result after Reference Library / polling slice: `22 passed, 1 warning`.
- Latest focused Web/API verification after Project Hub template / module split slice: `22 passed, 1 warning`.
- Latest focused Web/API verification after Runtime-hosted Workbench entry:
  `23 passed, 1 warning`.
- Latest focused Web/API verification after Draft Canvas integration:
  `24 passed, 1 warning`.
- Latest focused Web/API verification after Project Readiness integration:
  API readiness/action tests `7 passed, 1 warning`; Web foundation `7 passed`.
- Final Project Readiness slice verification:
  focused Runtime/Web/API `24 passed, 1 warning`; Runtime-hosted HTTP smoke passed; full pytest `835 passed, 1 warning`.
- Latest focused Web/API verification after Stage Navigation integration:
  Web foundation `8 passed`; focused Runtime/Web/API `25 passed, 1 warning`; Runtime-hosted HTTP smoke passed; full pytest `836 passed, 1 warning`.
- Latest focused Web/API verification after Activity Timeline integration:
  Activity state/Web foundation `10 passed, 1 warning`; Web foundation after artifact-ref handler fix `9 passed`; focused Runtime/Web/API `26 passed, 1 warning`.
- Final Activity Timeline slice verification:
  CLI help/version passed; `maintenance_audit` `failed=0, passed=6, warning=0`;
  retention review `delete_candidate_count=0`, `manual_review_required_count=0`;
  Runtime-hosted Activity Timeline HTTP smoke passed; full pytest `837 passed, 1 warning`.
- Production Board slice verification:
  red tests failed before implementation; focused state/Web tests `11 passed, 1 warning`;
  focused Runtime/Web/API `26 passed, 1 warning`; Runtime-hosted Production Board HTTP smoke passed;
  full pytest `837 passed, 1 warning`.
- Command Hub slice verification:
  red tests failed before implementation; focused state/Web tests `11 passed, 1 warning`;
  focused Runtime/Web/API/action suite `18 passed, 1 warning`; Runtime-hosted Command Hub HTTP smoke passed.
- Project Hub slice verification:
  red tests failed before implementation; focused state/Web tests `11 passed, 1 warning`;
  focused Runtime/Web/API/action suite `18 passed, 1 warning`; Runtime-hosted Project Hub HTTP smoke passed;
  full pytest `837 passed, 1 warning`.
- Creation Workspace projection slice verification:
  red tests failed before implementation; focused state/Web tests `11 passed, 1 warning`;
  focused Runtime/Web/API/action suite `18 passed, 1 warning`; Runtime-hosted Creation Workspace HTTP smoke passed with `creation_workspace.status = ready_for_first_check`, `selected_card_id = draft-hook`, `canvas_cards = 4`, `filmstrip_items = 3`, and `primary_action = start_first_generation_check`.
- Memory Workspace projection slice verification:
  red tests failed before implementation; focused state/Web tests `11 passed, 1 warning`;
  focused Runtime/Web/API/action suite `18 passed, 1 warning`; Runtime-hosted Memory Workspace HTTP smoke passed with `memory_workspace.status = ready`, 2 candidates, 1 profile version, and enabled feedback controls.
- UX Refoundation Stage 5 verification:
  focused Web/API tests `11 passed, 1 warning`; browser smoke opened `proj_demo_reference_flow_1781004364` from the project list, verified Review Room with 5 candidates and 3 recorded review decisions, verified Project Memory with profile version / reusable preference / evidence ledger / next-round reuse, and confirmed no checked internal action/job id leaks, local path leaks, or provider secret leaks in those two views. Screenshot: `data/processed/runs/workbench_live_demo/qa/stage5-review-memory-smoke.png`.
- UX Refoundation Stage 6 verification:
  focused Web/API tests `11 passed, 1 warning`; browser smoke verified Jobs as a focused Task Center with 6 job cards, Provider Gate visible, no shared readiness/command/production panels in the task window, and no checked internal action/job id, local path, or provider secret leaks. Screenshot: `data/processed/runs/workbench_live_demo/qa/stage6-jobs-provider-smoke.png`.
- UX Refoundation Stage 0-6 final verification:
  CLI help/version passed; focused Runtime/Web/API `23 passed, 1 warning`; full pytest `844 passed, 1 warning`; `maintenance_audit` `failed=0, passed=6, warning=0`; `git diff --check` passed with line-ending warnings only.
- UX Refoundation Stage 7 release-candidate browser QA:
  project `proj_stage7_rc_1781016167554` completed the UI path through Assets -> Draft Canvas -> Create -> Storyboard -> Review -> first check -> feedback -> next round -> Style Memory -> Jobs -> Provider preflight -> Settings/Diagnostics. Browser QA recorded `consoleErrorCount=0`, visible English `false`, main-view internal leak `false`, text overflow `0`, 1 asset, 4 canvas nodes, 3 storyboard shots, 1 style preference, 6 jobs, and 4 provider blockers. Screenshots: `data/processed/runs/workbench_live_demo/qa/stage7-rc-1440x900-diagnostics.png`, `data/processed/runs/workbench_live_demo/qa/stage7-rc-1366x768.png`, `data/processed/runs/workbench_live_demo/qa/stage7-rc-390x844.png`.
- Draft Canvas HTTP smoke on port 8792: `draft_canvas succeeded`, 3 generated
  cards, 3 filmstrip items, `/workbench/` returned `200`.
- Runtime HTTP smoke on port 8791: `/health`, `/workbench/`, and
  `/workbench/src/app.js` returned `200` with expected shell/module content.
- Broader focused Runtime/Web/API verification: `22 passed, 1 warning`.
- CLI help/version passed; version output: `0.1.0`.
- `maintenance_audit`: `failed=0`, `passed=6`, `warning=0`.
- `repository_retention_review --summary-only`: `delete_candidate_count=0`, `manual_review_required_count=0`.
- Full pytest: `833 passed, 1 warning`.
- Earlier foundation verification before the Review Room / Job Center extension:
  `.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_service.py tests\test_api_runtime_workbench_state.py tests\test_web_workbench_foundation.py -q`
- Earlier result: `21 passed, 1 warning`.
- CLI help/version passed.
- `maintenance_audit`: `failed=0, passed=6, warning=0`.
- `repository_retention_review --summary-only`: `delete_candidate_count=0`, `manual_review_required_count=0`.
- Full pytest: `832 passed, 1 warning`.
- `git diff --check` passed with CRLF normalization warnings only.
