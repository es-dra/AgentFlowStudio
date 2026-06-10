# AgentFlow Studio 任务账本

最后更新：2026-06-10 by Codex

本文件只保留当前工作、下一步队列、阻塞项和证据入口。旧 Alpha、旧 Web
bridge、旧 demo 和旧逐节点 handoff 不再作为当前任务入口。

公司源头知识库：

```text
Company OS source knowledge base (local private path omitted)
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
| AFS-WEB-HUMAN-ACCEPTANCE-001 | 人工验收当前 Web release candidate，确认项目 -> 素材 -> 画布 -> 分镜 -> 审片 -> 记忆 -> 任务路径是否符合低学习成本创作工作台定位 | 待人工验收：验收包、可视化演示索引、draft PR handoff 已落地；验收前浏览器演练已通过自动连接和 8 个工作区切换，但仍不等于人工验收 |
| AFS-WEB-LIBTV-RESOURCE-ENTRY-001 | LibTV 添加资源入口：上传素材 / 从生成历史选择的本地安全投影 | 已完成 TDD、HTTP 资源检查、全量 pytest 和本地 Playwright 点击 QA；manifest `data/processed/runs/workbench_libtv_add_node_state_browser_qa/workbench_libtv_add_node_browser_qa.json` 覆盖 `resource_upload` / `resource_history`，selector 可见、console/page errors `0`、forbidden matches `[]`、provider_request_urls `[]` |

## 当前阻塞和残留

- `maintenance_audit` 的 secret-like warning 和 oversized warning 已清零；后续触碰模块时仍按 300 行理想线继续拆分。
- Hidden CLI support commands 仍是兼容支持面；删除前必须做独立 CLI 协议迁移。
- Provider validation 默认关闭，除非显式授权对应 capability gate。
- 维护审计当前为通过状态；新的前端模块仍按单职责和 300 行理想线维护。
- 当前 Web release candidate 还没有人工验收结论；不得把 Stage 7 浏览器 QA 说成 human acceptance。
- Provider smoke 准备包已落地，但尚未执行；不得把 readiness-only plan 说成真实模型接入成功。
- LibTV 添加资源入口已是本地安全投影，不等于真实上传、真实历史读取或生成资产复用验收。

## 2026-06-10 - Web RC Freeze / Provider Vertical Prep

| ID | 范围 | 状态 | 证据 |
|---|---|---|---|
| AFS-WEB-RC-FREEZE-2026-06-10 | 冻结当前 Web Workbench 工程 RC：收口 dirty worktree、模块体量、验收包、QA 账本和残留风险，不再横向扩展 LibTV 功能面 | 进行最终 QA；等待人工验收 | `docs/frontend_integration/AFS_WEB_RC_FREEZE_CLOSEOUT_2026-06-10.zh-CN.md` |
| AFS-PROVIDER-LLM-SCRIPT-VERTICAL-001 | provider 最小纵切从 LLM/script 开始：用户目标 -> 脚本/分镜 safe artifact -> 审片反馈 -> 第二轮复用反馈 | gate-closed 工程骨架和本地确定性脚本草案已落地；第二轮 candidate constraints 已覆盖；未执行真实 provider smoke | `docs/frontend_integration/AFS_PROVIDER_LLM_SCRIPT_VERTICAL_PREP_2026-06-10.zh-CN.md` |
| AFS-PROVIDER-LLM-SCRIPT-COS-FEEDBACK-001 | 形成 provider 纵切前置规则候选：先落 gate-closed safe artifact plan，再开真实 provider smoke | candidate | `docs/frontend_integration/AFS_PROVIDER_LLM_SCRIPT_COMPANY_OS_FEEDBACK_2026-06-10.zh-CN.md` |
| AFS-WEB-RC-COS-FEEDBACK-001 | 形成外部产品复刻节奏的 Company OS candidate feedback，不自动晋升 active rule | candidate | `docs/frontend_integration/AFS_WEB_RC_COMPANY_OS_FEEDBACK_2026-06-10.zh-CN.md` |

冻结边界：

- 当前状态是 engineering RC，不是 human acceptance。
- Browser QA / pytest / maintenance audit 只是 runtime verification。
- Provider smoke 需要单独显式 gate；第一条建议从 LLM/script 开始，不从 image/video 开始。
- AFS 差异化继续通过任务状态、证据链、质量门、反馈复用、项目记忆、Provider Gate 和组织复盘逐步显性化，不强塞进主界面。

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
| AFS-WEB-CREATION-WORKSPACE-001 | Creation workspace, scene/content cards, inspector, filmstrip, first generation check | Landed as safe projection and folded into current UI: `studio_workspace` / `storyboard` are the active render paths; old `render-creation-workspace.js` retired |
| AFS-WEB-REVIEW-STYLE-MEMORY-001 | Review feedback into project style memory | Landed as separate Review Room and Project Memory workspaces; old mixed `render-memory-workspace.js` retired |
| AFS-WEB-OPERATIONS-WORKSPACE-001 | Runtime operations, provider preflight, and job/activity navigation | Landed in current branch: backend `operations_workspace` projection, frontend Operations Workspace panel, provider controls, and split operations state/render modules |
| AFS-WEB-JOB-CENTER-001 | Runtime job progress, blocker guidance, and artifact navigation | Landed through `operations_workspace` and `render-operations-workspace.js`; old English `render-jobs.js` retired |
| AFS-WEB-PROJECT-READINESS-001 | Project readiness, next action, and visible workflow gates | Landed: backend `project_readiness`, frontend Project Readiness panel, action mapping, and split readiness CSS |
| AFS-WEB-STAGE-NAVIGATION-001 | Stage-based Workbench navigation and view-specific control groups | Landed: `activeView`, functional rail navigation, and grouped action panel rendering |
| AFS-WEB-ACTIVITY-TIMELINE-001 | Runtime activity timeline, blocker visibility, and safe artifact navigation | Landed: backend `activity_timeline`, frontend Activity Timeline panel, safe primary artifact refs, and split activity modules |
| AFS-WEB-PRODUCTION-BOARD-001 | Product-facing source -> draft -> check -> review -> style memory -> next round -> provider gate board | Landed: backend `production_board`, frontend Production Board panel, 7-lane flow state, and split board modules |
| AFS-WEB-COMMAND-HUB-001 | User-facing next command, action mapping, required input hints, and provider gate blocker visibility | Landed: backend `command_hub`, frontend Command Hub panel, action mapping, and split command modules |
| AFS-WEB-PROJECT-HUB-001 | Product-facing active project summary, safe counts, next command, and recent job navigation | Landed in current branch: backend `project_hub`, frontend Project Hub panel, state adapter, and split CSS |
| AFS-WEB-STUDIO-WORKSPACE-001 | 将 Create 视图改为产品化 Studio Workspace：统一承载画布、素材参考、风格记忆、审片队列、runtime 摘要和 safe artifact 导航 | 已在当前分支落地：后端 `studio_workspace`、前端 Studio Workspace 面板、state adapter 和独立 CSS |
| AFS-WEB-VERTICAL-FLOW-001 | Workbench deterministic 纵向主路径：从空项目到 ready_for_next_round，不接触 CLI 或手写 JSON | 已完成浏览器级主路径证据：API vertical flow、mutation `flow` summary、空工作区创建入口、Review decision 主入口、Production Board 全宽布局、Playwright browser smoke 到 `ready_for_next_round` |
| AFS-WEB-UX-REFOUNDATION-001 | 将 Workbench 从工程状态面板重构为中文多工作区创作应用：项目、创作画布、素材库、分镜台、审片室、项目记忆、任务中心、诊断 | 阶段 0-7 已落地到发布候选：中文 IA/术语/QA 账本、多工作区外壳、项目设置向导、创作画布节点流、素材库分组、独立分镜台、独立审片室、独立项目记忆、任务中心、Provider Gate、Runtime 中文显示适配、no-store 静态入口、浏览器主路径和响应式截图 QA 已完成；下一步进入人工验收和 provider-gated smoke 前置整理 |
| AFS-WEB-CANVAS-V2-001 | 将 Create 从状态卡片式 Studio Workspace 推进为媒体优先画布：暗色舞台、节点预览、素材缩略、检查器预览、分镜条、生成能力术语清洗、内部聚焦窗口、操作模式和低标签密度画布 | 当前分支按 LibTV 画布页复刻第一轮落地：Create 旧窗口头隐藏，主视图改为全屏暗色点阵画布、紧凑生产节点、底部工具坞、添加节点/资产/历史/快捷键/检查器/生成门浮层，支持轻量平移和缩放；focused Web 测试与 `maintenance_audit` 已通过，仍等待人工体验复核 |
| AFS-WEB-LIBTV-HOME-PORTAL-001 | 按 LibTV 登录首页/创作门户复刻 Projects 页：活动/能力横幅、最近项目、开始创作、精选画布案例和搜索筛选 | 当前分支已落地：Projects 改为全屏暗色创作门户，隐藏旧全局顶栏和侧栏，不再堆叠项目就绪度/命令/制作流程状态面板；浏览器复核英文 provider/durable memory 命中 `0`，raw project id/type 可见为 `false` |
| AFS-WEB-LIBTV-PROJECT-DIRECTORY-001 | 按 LibTV `/project` 全部项目页复刻 Projects 内的项目列表模式：返回、全部项目、新建文件夹、开始创作卡和项目卡片 | 当前分支已落地：点击门户“全部项目”切换到项目列表模式；浏览器复核返回/新建文件夹/开始创作/没有更多了均可见，项目卡 `9` 张，英文 provider/durable memory 命中 `0`，raw project id/type 可见为 `false` |
| AFS-WEB-LIBTV-SHOWCASE-PROCESS-001 | 按 LibTV 案例详情和“查看制作过程”复刻 Projects 精选画布：沉浸式成片详情、只读过程弹层、节点关系和复制到项目入口 | 当前分支已落地：精选画布卡片进入案例详情，详情页可打开只读制作过程弹层；浏览器复核滚动刷新保留、详情按钮、只读提示、`10` 个过程节点、`6` 条连线、节点详情切换均可用；Provider 未启动 |
| AFS-WEB-LIBTV-GLOBAL-DRAWER-001 | 按 LibTV 左侧菜单复刻 Projects 全局工作台抽屉：账号席位、首页、模式切换、生成能力门、退出占位和规则边界 | 当前分支已落地：左上菜单打开暗色抽屉，会员/席位行高度 `38px`，导航行 `4` 个，默认 UI 未命中 `OPENAI_API_KEY`、`signed URL`、`provider_config`；不处理真实账号凭据 |
| AFS-WEB-LIBTV-SHOWCASE-FILTER-001 | 按 LibTV 门户筛选/搜索复刻 Projects 精选画布入口：分类筛选、搜索框和无结果空态 | 当前分支已落地：筛选“生成门”后只显示 `产品短片自动化画布`；搜索“不存在”后显示“没有匹配的画布”；仅前端内存态过滤，不请求后端、不启动 provider |
| AFS-WEB-LIBTV-CREATE-ENTRY-001 | 按 LibTV “开始创作”复刻从门户到空画布的生产入口：未命名项目画布、四个起步生成节点、底部工具坞和回到实际画布 | 当前分支已落地：Projects“开始创作”进入 Create 起步画布，显示故事脚本生成、角色三视图、首帧图生视频、音频生视频四个入口；保留“实际画布”切回 Runtime 投影；本轮浏览器复核 starter 高度 `58px`，未出现 provider 已启动声明 |
| AFS-WEB-LIBTV-CANVAS-TOOLS-001 | 按 LibTV 空画布底部工具坞复刻添加节点与资产管理：紧凑节点调色板、左侧素材抽屉、分组生产入口和空态素材入口 | 当前分支已落地：添加节点浮层收敛为起步生成、链路组织、治理与记忆 `3` 组 `6` 个核心生产节点；资产管理抽屉显示项目输入、生成候选、记忆证据 `3` 组；浏览器复核 provider 未启动 |
| AFS-WEB-LIBTV-CANVAS-UTILITY-001 | 按 LibTV 空画布底部工具坞复刻工具箱和帮助中心：画布辅助、快捷说明、安全边界和低学习成本入口 | 当前分支已落地：工具箱显示整理画布、切换小地图、网格吸附、跟随选中 `4` 个辅助入口；帮助中心显示画布操作、素材安全、生成能力门、审片记忆 `4` 个中文说明；浏览器复核英文残留为 `false` |
| AFS-WEB-LIBTV-TV-TOOLBOX-001 | 按 LibTV 画布主体功能补齐 TV 工具箱骨架：多角度、运镜标记、首尾帧、图片高清、文字生音乐、角色库和画布辅助 | 当前分支已落地：Create 底部工具箱从单纯画布辅助提升为 `TV工具箱`，包含 `6` 个创作工具和 `4` 个画布辅助；本地 Playwright QA 覆盖 desktop/tablet/mobile 三视口，manifest `qa_status=passed`、required labels missing `[]`、provider_request_urls `[]`、console/page errors `0`、horizontal viewport overflow `false` |
| AFS-WEB-LIBTV-TOOLBOX-INTENT-001 | 将 TV 工具箱主体功能从静态入口提升为本地工具意图状态流 | 当前分支已落地：点击 `多角度`、`运镜标记`、`首尾帧`、`图片高清`、`文字生音乐`、`角色库` 会写入 `studioToolIntent`，工具行 active，并显示 `本地工具意图已登记`、`未创建真实任务`、`未启动 provider` 的工具回执；工具箱渲染拆到 `render-studio-toolbox.js`，样式拆到 `styles-studio-toolbox.css`，避免 utility 文件越界；三视口 QA 逐项点击 6 个创作工具，provider_request_urls 为 `[]` |
| AFS-WEB-LIBTV-CANVAS-HEADER-001 | 按 LibTV 画布顶栏复刻项目名输入和画布选择器：本地标题编辑、画布 1/画布 2/审片画布菜单、新建画布意图回执 | 当前分支已落地：`studioProjectTitle`、`studioActiveCanvasId`、`studioCanvasMenuOpen`、`studioCanvasIntent` 组成本地 Canvas Workspace 状态；标题输入只保存在浏览器内存，选择或新建画布只显示 `本地画布意图已登记`、`未创建真实画布`、`未启动 provider`；浏览器 QA 覆盖 desktop/tablet/mobile 三视口，provider_request_urls `[]`，并修复画布菜单被执行脚手架截获点击的层级问题 |
| AFS-WEB-LIBTV-EXECUTION-SCAFFOLD-001 | 按 LibTV 画布主体链路补齐执行骨架：节点连接、参数抽屉和待执行动作队列 | 当前分支已落地：Create 实际画布显示 `节点连接`、`参数抽屉`、`待执行动作`，包含 3 条本地连接关系、6 个参数占位和 3 个执行意图按钮；本地 Playwright QA 覆盖 desktop/tablet/mobile 三视口，manifest `qa_status=passed`、required labels missing `[]`、provider_request_urls `[]`、console/page errors `0`、horizontal viewport overflow `false`；仍只登记本地执行意图，不启动真实生成 |
| AFS-WEB-LIBTV-EXECUTION-INTENT-001 | 将执行骨架里的待执行动作从静态按钮提升为本地执行意图状态流 | 当前分支已落地：点击 `生成预检`、`登记执行意图`、`等待能力授权` 会写入 `studioExecutionIntent`，按钮进入 active 状态，并显示 `本地意图已登记`、`未创建真实任务`、`未启动 provider` 的执行回执；浏览器 QA 已逐视口点击 3 个意图并记录 `intent_clicks`，provider_request_urls 仍为 `[]`；移动端 execution layer 已收敛为单列脚手架，避免顶部栏遮挡 |
| AFS-WEB-LIBTV-HISTORY-ASSETS-001 | 按 LibTV 空画布历史入口复刻历史资产浮层：图片/视频/音频历史、可复用筛选、批量选择、缩放和资产卡片网格 | 当前分支已收口：历史资产浮层显示 `6` 条可复用记录，图片/视频/音频标签、倒序/批量/可复用控制和关闭/缩放入口可见；浏览器复核 `consoleErrorCount=0`、`overflowCount=0`、安全命中 `0`，Provider 未启动 |
| AFS-WEB-LIBTV-SCRIPT-NODE-001 | 按 LibTV “故事脚本生成”起步节点复刻脚本结果节点：剧本内容卡、下游承接节点、编辑提示、底部生成控制卡和模型选择占位 | 当前分支已落地：真实 LibTV 取证显示点击故事脚本生成后进入“剧本”内容节点而非纯表单；AFS Create 起步画布点击故事脚本生成后显示脚本内容节点、连线、`双击剧本内容，可直接编辑或替换` 提示、`GVLM 3.1` 与 `Provider 未启动`；浏览器复核 `console_error_count=0`、空画布提示不可见、安全命中 `0` |
| AFS-WEB-LIBTV-CHARACTER-NODE-001 | 按 LibTV “角色三视图”起步节点复刻角色图与三视图结果节点：角色图输入、三视图结果、顶部能力条、替换提示和生成器边界 | 当前分支已落地：真实 LibTV 取证显示点击角色三视图后进入“角色图 / 角色三视图”双节点，能力条含 `全景`、`多角度`、`打光`、`九宫格`、`高清`、`宫格切分`；AFS Create 起步画布点击角色三视图后显示安全占位角色图、三视图占位、`点击按钮，可替换上传你的角色图` 提示、`生成器未启动` 与 `Provider Gate 未授权`；浏览器复核 `consoleErrorCount=0`、旧 inspector 不可见、安全命中 `0` |
| AFS-WEB-LIBTV-IMAGE-VIDEO-NODE-001 | 按 LibTV “首帧图生视频”起步节点复刻首帧图与视频结果节点：首帧输入、视频预览、模式 tabs、辅助工具、模型参数和视频生成边界 | 当前分支已落地：真实 LibTV 取证显示点击首帧图生视频后进入“首帧 / 视频”双节点，控制区含 `文生视频`、`全能参考`、`图生视频`、`首尾帧`、`图片参考`、`标记`、`运镜`、`角色库`、`Seedance 2.0 VIP`、`16:9 · 720P · 5s`；AFS Create 起步画布点击首帧图生视频后显示安全占位首帧、视频占位、替换提示和 `视频生成未启动`；浏览器复核 `consoleErrorCount=0`、旧 inspector 不可见、安全命中 `0`，并修复紧凑布局下滚轮误触画布缩放 |
| AFS-WEB-LIBTV-AUDIO-VIDEO-NODE-001 | 按 LibTV “音频生视频”起步节点复刻音频与视频结果流：音频输入、波形/时长、视频预览、模式 tabs、辅助工具、模型参数、联网搜索/自动校验素材和音频驱动边界 | 当前分支已落地：真实 LibTV 取证显示点击音频生视频后进入“音频 / 视频”双节点，显示 `00:00 / 00:03`、`图片`、`文生视频`、`全能参考`、`图生视频`、`首尾帧`、`图片参考`、`标记`、`运镜`、`角色库`、`Seedance 2.0 VIP`、`16:9 · 720P · 5s`、`1个`、`135`、`联网搜索`、`自动校验素材` 和“点击按钮，可替换上传你的音频文件”；AFS Create 起步画布点击音频生视频后显示安全音频波形、视频占位、控制卡和 `音频驱动未启动`；浏览器复核空画布提示/旧 inspector 不可见、安全命中 `0`，Provider 未启动 |
| AFS-WEB-LIBTV-ADD-NODE-MENU-001 | 按 LibTV 真实“添加节点”菜单复刻 Create 底部工具坞：文本、图片、视频、视频合成、导演台、音频、脚本，以及上传/生成历史资源入口 | 当前分支已落地：真实 LibTV 取证显示菜单包含 `添加节点`、`文本`、`剧本、广告词、品牌文案`、`视频合成 Beta`、`导演台 NEW`、`添加资源`、`上传`、`从生成历史选择`；AFS Create 起步画布对应浮层显示 `7` 个节点入口和 `2` 个资源入口，`data-add-node-kind` / `data-add-resource-kind` 正确落到 DOM；浏览器复核 `missingLabels=[]`、`badgeCount=3`、`forbiddenMatches=[]`，未点击上传/历史/生成，Provider 未启动 |
| AFS-WEB-LIBTV-ADD-NODE-FLOW-001 | 补齐添加菜单点击后的本地节点态：文本、图片、视频、视频合成、导演台、音频、脚本的安全占位节点和控制卡 | 当前分支已落地并补齐本地 Playwright 点击截图证据：点击 `data-add-node-kind` 后进入 `studioAddedNodeKind` 节点态，覆盖 `node_text`、`node_image`、`node_video`、`node_audio`、`node_script`、`node_director`、`node_video_merge`；QA manifest 显示 7 个节点态 selector 均可见、console/page errors `0`、forbidden matches `[]`、provider_request_urls `[]`，截图位于 `data/processed/runs/workbench_libtv_add_node_state_browser_qa/screenshots/` |
| AFS-WEB-LIBTV-DIRECTOR-MERGE-001 | 深化 LibTV 添加节点后的特色能力：`导演台` 进入 3D 导演台控制面，`视频合成` 进入安全时间线控制面 | 当前分支已落地并纳入统一 Playwright 点击 QA：基于真实 LibTV `13-director-node.json` / `14-director-workspace.json` 取证，AFS `导演台` 节点显示 `3D导演台`、导演/机位/场景视角、对象搜索、`机位1`、`角色A`、摄像机属性、`FOV 50°`、位置/注视坐标、截图/AI 识图/全屏入口和 `导演台未启动`；`视频合成` 显示 3 段安全引用时间线、片段排序、转场、节奏、统一画幅和 `视频合成未启动`；`node_director` / `node_video_merge` 截图已产出，Provider 未启动 |
| AFS-WEB-LIBTV-IMAGE-ADD-NODE-001 | 深化 LibTV 添加菜单里的 `图片` 节点：上传入口、图生图/高清/风格/标记、Lib Image 模型和基础参数控制 | 当前分支已落地：基于真实 LibTV `15-image-node.json/png`，AFS `图片` 添加节点显示 `图片节点`、`上传`、`尝试：`、`图生图`、`图片高清`、`风格`、`标记`、`Lib Image`、`自适应 · 标准画质 · 2K`、`摄像机 · 全景`、`1张 · 18` 和 `图片生成未启动`；TDD 与 HTTP 资源检查通过，不读取文件字节、不启动 image provider |
| AFS-WEB-LIBTV-SCRIPT-ADD-NODE-001 | 深化 LibTV 添加菜单里的 `脚本` 节点：脚本生成器、参考文本节点、三种分镜脚本尝试和 GVLM 控制卡 | 当前分支已落地：基于真实 LibTV `12-script-node.json/png`，AFS `脚本` 添加节点显示 `脚本生成器`、`尝试：`、`剧本生成分镜脚本`、`视频参考生成分镜脚本`、`角色生成分镜脚本`、`文本节点 2`、`自己编写内容`、`文生视频`、`图片反推提示词`、`文字生音乐`、`GVLM 3.1` 和 `脚本生成未启动`；样式拆分到 `styles-studio-script-generator-flow.css`，TDD 与 HTTP 资源检查通过，不上传参考文本、不启动 LLM/provider |
| AFS-WEB-LIBTV-TEXT-ADD-NODE-001 | 深化 LibTV 添加菜单里的 `文本` 节点：文本节点 2、四种尝试入口、GVLM 控制卡和安全摘要边界 | 当前分支已落地：基于真实 LibTV `03-text-node.json/png`，AFS `文本` 添加节点显示 `文本节点 2`、`尝试：`、`自己编写内容`、`文生视频`、`图片反推提示词`、`文字生音乐`、故事/场景/角色设定提示、`GVLM 3.1`、`1` 和 `文本生成未启动`；样式拆分到 `styles-studio-text-node-flow.css`，红灯先失败在缺失 `renderTextNodeFlow`，实现后 add-node flow 与 foundation/studio focused 测试通过，不上传文本、不启动 LLM/provider |
| AFS-WEB-LIBTV-VIDEO-ADD-NODE-001 | 深化 LibTV 添加菜单里的 `视频` 节点：视频节点、视频生成模式、辅助工具、Seedance 模型参数和安全摘要边界 | 当前分支已落地：基于真实 LibTV 视频控制参考 `08-image-video-node-state-summary.json`，AFS `视频` 添加节点显示 `视频节点`、`文生视频`、`全能参考`、`图生视频`、`首尾帧`、`图片参考`、`标记`、`运镜`、`角色库`、`Seedance 2.0 VIP`、`16:9 · 720P · 5s`、`1个`、`135`、`联网搜索`、`自动校验素材` 和 `视频生成未启动`；渲染拆到 `render-studio-video-node-flow.js`，样式拆到 `styles-studio-video-node-flow.css`，TDD 与 HTTP 资源检查通过，不上传素材、不启动 video provider |
| AFS-WEB-LIBTV-AUDIO-ADD-NODE-001 | 深化 LibTV 添加菜单里的 `音频` 节点：音频节点、波形/时长、音频驱动视频模式、Seedance 参数和安全摘要边界 | 当前分支已落地：基于真实 LibTV 音频控制参考 `10-audio-video-node-state-summary.json`，AFS `音频` 添加节点显示 `音频节点`、`00:00 / 00:03`、`图片`、`视频`、`文生视频`、`全能参考`、`图生视频`、`首尾帧`、`图片参考`、`标记`、`运镜`、`角色库`、`Seedance 2.0 VIP`、`16:9 · 720P · 5s`、`1个`、`135`、`联网搜索`、`自动校验素材` 和 `音频生成未启动`；渲染拆到 `render-studio-audio-node-flow.js`，样式拆到 `styles-studio-audio-node-flow.css`，TDD 与 HTTP 资源检查通过，不读取本地文件字节、不启动 audio/video provider |

Verification so far:

- LibTV add-node/resource state browser QA:
  `.\.venv\Scripts\python.exe tools\workbench_libtv_add_node_browser_qa.py --base-url http://127.0.0.1:8790/workbench/`
  passed across `desktop` / `tablet` / `mobile` viewports. Evidence: `data/processed/runs/workbench_libtv_add_node_state_browser_qa/workbench_libtv_add_node_browser_qa.json`, screenshots under `data/processed/runs/workbench_libtv_add_node_state_browser_qa/screenshots/{desktop,tablet,mobile}/`. Covered 7 node states and 2 resource states per viewport (`27` cases total) with expected selectors visible, console/page errors `0`, forbidden matches `[]`, provider_request_urls `[]`, and no viewport overflow. The mobile pass also fixed the bottom tool dock width, canvas node layer width, and history-resource card clipping/scroll behavior.
- LibTV TV toolbox browser QA:
  `.\.venv\Scripts\python.exe tools\workbench_libtv_toolbox_browser_qa.py --base-url http://127.0.0.1:8790/workbench/`
  passed across `desktop` / `tablet` / `mobile` viewports. Evidence: `data/processed/runs/workbench_libtv_toolbox_browser_qa/workbench_libtv_toolbox_browser_qa.json`, screenshots under `data/processed/runs/workbench_libtv_toolbox_browser_qa/screenshots/{desktop,tablet,mobile}/`. Covered `TV工具箱` with 6 creation tools and 4 canvas tools; clicked 6 creation-tool intents per viewport with active rows and receipts containing `本地工具意图已登记`、`未创建真实任务`、`未启动 provider`; required labels missing `[]`, console/page errors `0`, provider_request_urls `[]`, and no horizontal viewport overflow.
- LibTV canvas header browser QA:
  `.\.venv\Scripts\python.exe tools\workbench_libtv_canvas_header_browser_qa.py --base-url http://127.0.0.1:8790/workbench/`
  passed across `desktop` / `tablet` / `mobile` viewports. Evidence: `data/processed/runs/workbench_libtv_canvas_header_browser_qa/workbench_libtv_canvas_header_browser_qa.json`, screenshots under `data/processed/runs/workbench_libtv_canvas_header_browser_qa/screenshots/{desktop,tablet,mobile}/`. Covered project title input, canvas menu, `画布 2` selection, `新建画布` local intent receipt, console/page errors `0`, forbidden matches `[]`, provider_request_urls `[]`, and no horizontal viewport overflow.
- LibTV execution scaffold browser QA:
  `.\.venv\Scripts\python.exe tools\workbench_libtv_execution_scaffold_browser_qa.py --base-url http://127.0.0.1:8790/workbench/`
  passed across `desktop` / `tablet` / `mobile` viewports. Evidence: `data/processed/runs/workbench_libtv_execution_scaffold_browser_qa/workbench_libtv_execution_scaffold_browser_qa.json`, screenshots under `data/processed/runs/workbench_libtv_execution_scaffold_browser_qa/screenshots/{desktop,tablet,mobile}/`. Covered `节点连接`、`参数抽屉`、`待执行动作`, 3 execution actions, 3 edge rows, 6 parameter rows, and 3 local intent clicks per viewport. Each click produced an active button and receipt with `本地意图已登记`、`未创建真实任务`、`未启动 provider`; required labels missing `[]`, console/page errors `0`, provider_request_urls `[]`, and no horizontal viewport overflow.
- Latest LibTV multi-viewport closeout verification after local execution-intent flow: focused Workbench/LibTV frontend `29 passed`; full pytest `864 passed, 1 warning`; `maintenance_audit` `failed=0, passed=6, warning=0`; CLI help/version passed; `git diff --check` passed with Windows line-ending warnings only.
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
