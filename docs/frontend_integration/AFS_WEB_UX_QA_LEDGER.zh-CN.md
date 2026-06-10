# AFS Web UX QA 账本

状态：阶段 0-7 已落地到发布候选 QA
日期：2026-06-09

## 当前主路径

| 路径 | 当前阶段 | 证据要求 |
|---|---|---|
| 打开 `/workbench/` | 阶段 1 | 首屏显示中文项目入口和工作区导航 |
| 创建项目 | 阶段 2 | 通过 UI 填写项目目标和类型，不手写 JSON |
| 进入创作画布 | 阶段 2 | 项目创建后可加载工作台并看到创作画布 |
| 添加素材摘要 | 阶段 3/4 | 只提交 safe summary，不提交本地路径或媒体字节 |
| 生成画布草稿 | 阶段 3 | 画布节点流、节点工具条和检查器同步更新 |
| 管理素材库 | 阶段 4 | 按需求、参考、脚本分组展示 safe summary |
| 查看分镜台 | 阶段 4 | 镜头序列、当前镜头、安全预览、引用/阻塞事实和审片入口可用 |
| 审片决定 | 阶段 5 | 审片室显示候选队列、当前候选、对比点、决定入口和最近审片 |
| 项目记忆复用 | 阶段 5 | 项目记忆显示可复用偏好、profile version、记忆证据和下一轮入口 |
| Provider 预检 | 阶段 6 | 只展示 gate/blocker，不启动真实 provider |

## 每阶段检查

- 浏览器 console error 为 0。
- 1440x900 与 1366x768 不出现主要布局重叠。
- 所有一级工作区都有中文名称、空态和下一步说明。
- Runtime action/status/stage 在用户界面显示为中文，不把内部 id 当作操作语言。
- 创作画布展示节点流、节点连接、引用/阻塞计数和右侧检查器。
- 素材库按素材类型分组，且不出现本地路径或媒体字节。
- 分镜台能从镜头序列进入审片室，并保持 safe artifact ref 边界。
- 审片室和项目记忆是两个独立工作区，不共用同一块候选/记忆混合面板。
- 审片决定进入 Runtime evidence，不声明 human acceptance 或 durable memory。
- 默认界面不暴露私有路径、secret、signed URL、provider raw response 或媒体字节。
- 诊断窗口可以找到内部 id 和安全边界说明。
- focused Web/API tests 通过。
- `git diff --check` 通过。
- Runtime-hosted Workbench 静态资源返回 `Cache-Control: no-store`。

## 阶段 5 浏览器证据

- 参考项目：`proj_demo_reference_flow_1781004364`。
- 路径：打开 `/workbench/` -> 展开诊断 -> 连接 Runtime Service -> 从项目列表打开参考项目 -> 审片室 -> 项目记忆。
- 审片室：5 个候选、3 条审片记录，保留 / 修改 / 拒绝入口可用；审片决定可写入 Runtime evidence。
- 项目记忆：独立工作区显示 profile version、可复用偏好、记忆证据和下一轮复用入口；不再混入 Activity Timeline。
- 安全检查：本轮检查的内部 action/job id 泄漏为 0，本地路径泄漏为 0，provider secret / gate env 泄漏为 0。
- 截图证据：`data/processed/runs/workbench_live_demo/qa/stage5-review-memory-smoke.png`。

## 阶段 6 浏览器证据

- 参考项目：`proj_demo_reference_flow_1781004364`。
- 路径：打开 `/workbench/` -> 连接 Runtime Service -> 打开参考项目 -> 任务中心。
- 任务中心：独立窗口显示 6 个任务卡、Provider 预检、自动刷新、运行证据入口和高级诊断；不再混入项目就绪度、下一步操作和制作流程面板。
- Provider Gate：默认只展示预检状态和阻塞说明，不启动真实 provider。
- 安全检查：本轮检查的内部 action/job id 泄漏为 0，本地路径泄漏为 0，provider secret / gate env 泄漏为 0。
- 截图证据：`data/processed/runs/workbench_live_demo/qa/stage6-jobs-provider-smoke.png`。

## 阶段 7 发布候选浏览器证据

- QA 项目：`proj_stage7_rc_1781016167554`。
- 路径：打开 `/workbench/` -> 连接 Runtime Service -> 从项目列表打开 QA 项目 -> 素材库登记安全素材摘要 -> 生成画布草稿 -> 创作画布 -> 分镜台 -> 审片室记录审片决定 -> 执行首轮素材检查 -> 记录反馈 -> 执行下一轮验证 -> 项目记忆 -> 任务中心 -> Provider 预检 -> 设置/诊断。
- 浏览器环境限制：Browser 虚拟剪贴板未安装，文本输入自动化不可用；本轮通过 Runtime API 创建唯一 QA 项目，再从 UI 项目列表打开，后续主路径均通过 UI 按钮和工作区切换完成。
- 主路径结果：素材 `1` 个，画布节点 `4` 个，分镜镜头 `3` 个，项目风格偏好 `1` 条，任务 `6` 个，Provider blocker `4` 个。
- 可用性检查：浏览器应用 console error 为 `0`；主视图可见英文为 `false`；主视图内部 id/action/job 泄漏为 `false`；文字溢出总数为 `0`。
- 安全检查：默认主视图未暴露本地路径、secret、signed URL、provider raw response 或媒体字节；Provider 仍为 gate/blocker 预检，没有真实 provider 调用。
- 响应式截图：
  - `data/processed/runs/workbench_live_demo/qa/stage7-rc-1440x900-diagnostics.png`
  - `data/processed/runs/workbench_live_demo/qa/stage7-rc-1366x768.png`
  - `data/processed/runs/workbench_live_demo/qa/stage7-rc-390x844.png`
- 结构化证据：`data/processed/runs/workbench_live_demo/qa/stage7-rc-browser-qa.json`。

## 阶段 0-7 发布候选验证

- CLI help/version 通过，version 输出 `0.1.0`。
- Focused Workbench frontend：`11 passed`。
- 全量 pytest：`844 passed, 1 warning`。
- `maintenance_audit`：`failed=0, passed=6, warning=0`。
- Runtime-hosted HTTP smoke：`/workbench/` 返回 `200`，`Cache-Control: no-store`，页面包含应用根节点和中文标题。
- `git diff --check` 通过，仅有 Windows 换行提示。

## 2026-06-10 浏览器主路径复核

- `tools/workbench_vertical_flow_browser_smoke.py` 已适配当前中文多工作区外壳：先展开诊断设置临时 Runtime URL，再显式切换到创作画布，不再依赖旧英文按钮文案。
- 最新浏览器 smoke 项目：`proj_browser_vertical_1781030891`。
- 结果：`project_status = ready_for_next_round`，`readiness_status = ready_for_provider_preflight`，`current_action = run_provider_preflight`。
- Provider 边界：`provider_calls_started = false`，`writes_long_term_memory = false`，`writes_company_kb = false`。
- 最新截图：`data/processed/runs/workbench_browser_smoke/browser_evidence/workbench-ready-for-next-round.png`。

## 2026-06-10 首屏中文体验复核

- 问题：刷新 `http://127.0.0.1:8790/workbench/` 后，项目列表和部分 Runtime projection 仍可能显示旧英文 demo 文案、raw project id、乱码标题或内部 Stage 7 命名。
- 修补：默认项目选择改为优先选择 `ready_for_next_round` 且证据更完整的项目；项目列表主标题改为项目目标/类型/计数，不再用 raw project id；明显乱码标题归一为“历史演练项目”，Stage 7 内部项目归一为“验收演练项目”。
- 修补：素材库、项目就绪度、操作指令、制作进度、任务中心、任务与 Provider、审片室、内容卡片等用户可见 projection 文案中文化；保留 action/status/non-claims 等合同枚举边界。
- 浏览器复核：项目列表 `old_project_ids_visible = false`，`question_mark_runs = 0`，`stage_rc_visible = false`，`toast_errors = []`；旧英文 projection 文案扫描命中 `0`。
- 自动化固化：`tools/workbench_vertical_flow_browser_smoke.py` 已将上述首屏检查升级为硬断言；最新 smoke 项目 `proj_browser_vertical_1781030891` 到达 `ready_for_next_round`，且 `provider_calls_started = false`。
- 2026-06-10 PM 复核补充：Create 视图中的内部状态 `completed_with_blocks` 和英文 blocker `Add project materials before running a real generation pass.` 已改为中文用户文案，并纳入可见文本泄漏断言；默认 smoke 根目录中损坏的 `artifact_index.json` 已由 RuntimeStore 自动修复路径覆盖。
- 2026-06-10 视口工作台复核：`/workbench/` 已从整页长滚动改为视口锁定应用壳；917x791 浏览器下 Projects/Create/Jobs/Settings 的 `documentElement.scrollHeight = 791`，长内容进入 `.workspace` 内部滚动，旧英文/内部枚举泄漏为 `0`。
- 2026-06-10 工作区主任务优先复核：Projects 首屏从项目中心开始，Assets 首屏从素材库开始，Settings 首屏从高级诊断和活动时间线开始；该顺序已在 `tests/test_web_workbench_foundation.py` 固化，避免回退成“一个窗口塞满所有状态面板”。
- 2026-06-10 Canvas V2 工程复核：Create 视图改为暗色媒体优先画布，包含节点预览、素材缩略、检查器预览、分镜条和生成能力术语清洗；Playwright 复核 `headerHidden=true`、`mediaFrames=4`、`sideThumbs=5`、`inspectorHero=true`、`filmstripPreviews=3`、`providerMatches=0`、`textOverflow=0`。
- Canvas V2 截图：`data/processed/runs/workbench_canvas_v2_qa/canvas-v2-create-1440x900-visual-final.png`；结构化证据：`data/processed/runs/workbench_canvas_v2_qa/canvas-v2-create-1440x900-visual-final.json`。
- 2026-06-10 Canvas V2 聚焦窗口复核：Create 内部支持 `画布 / 素材 / 审片 / 检查器 / 运行` 切换；Playwright 复核每个窗口 `providerMatches=0`、`textOverflow=0`、`bodyHeight=viewportHeight=900`，未加载产物时不显示空 artifact panel。
- 聚焦窗口证据：`data/processed/runs/workbench_canvas_v2_focus_qa/focus-switch-1440x900-no-empty-artifact.json`；截图：`focus-canvas-1440x900-no-empty-artifact.png`、`focus-review-1440x900-no-empty-artifact.png`、`focus-ops-1440x900-no-empty-artifact.png`。
- 2026-06-10 Canvas V2 降噪复核：Create 画布保留 `规划 / 制作 / 审片 / 复用` 模式入口，但将模式卡、阶段条、节点状态标签、引用数、零值动作/阻塞和运行摘要下沉或按需隐藏；主画布只突出可选择的镜头/候选对象。
- 降噪证据：`data/processed/runs/workbench_canvas_declutter_audit/create-declutter-current.json`；截图：`data/processed/runs/workbench_canvas_declutter_audit/create-declutter-canvas.png`；浏览器复核 `visibleBadgeLikeCount=5`、`stageTokenCount=0`、`modeChipCount=0`、`opsSummaryVisible=false`、`visibleSummaryCount=1`。边界仍为 Runtime Service safe projection，不启动真实 provider。
- 2026-06-10 LibTV 画布页复刻复核：Create 视图改为接近 LibTV 生产画布的全屏暗色点阵工作区，旧全局顶栏和左侧工作区导航在 Create 内隐藏，主画布只保留项目入口、生成能力门、生产节点和底部工具坞；添加节点、资产、历史、快捷键、节点检查器和生成能力门均为按需浮层。
- 画布交互证据：缩放从 `100%` 到 `110%`，节点层 transform 从 `translate3d(0px, 0px, 0px) scale(1.1)` 变为 `translate3d(90px, 50px, 0px) scale(1.1)`，证明当前不只是静态背景；Provider 仍未启动。
- LibTV 画布页复刻截图：`data/processed/runs/workbench_libtv_canvas_rebuild/08-refined-canvas.png`、`data/processed/runs/workbench_libtv_canvas_rebuild/09-pan-zoom.png`、`data/processed/runs/workbench_libtv_canvas_rebuild/10-panel-add.png`、`data/processed/runs/workbench_libtv_canvas_rebuild/10-panel-assets.png`、`data/processed/runs/workbench_libtv_canvas_rebuild/10-panel-history.png`、`data/processed/runs/workbench_libtv_canvas_rebuild/10-panel-shortcuts.png`、`data/processed/runs/workbench_libtv_canvas_rebuild/10-panel-inspector.png`、`data/processed/runs/workbench_libtv_canvas_rebuild/10-panel-gate-fixed.png`。
- 本轮 focused 验证：`tests/test_web_workbench_studio.py tests/test_web_workbench_foundation.py` 为 `10 passed`；`maintenance_audit` 为 `failed=0, passed=6, warning=0`。
- 2026-06-10 LibTV 登录首页/创作门户复刻：LibTV 首页首屏参考包含活动横幅、最近项目、开始创作入口、精选画布案例流、筛选与搜索；AFS 对应 Projects 页已改为全屏暗色创作门户，隐藏旧工程顶栏和侧栏，不再在首页堆叠项目就绪度、命令中心和制作流程状态面板。
- Projects 门户浏览器复核：`heroCards=3`，`projectCards=5`，`showcaseCards=6`，`oldPanelVisible=false`，`topbarVisible=false`，`railVisible=false`，可见 `provider/durable memory` 英文命中 `0`，raw project id/type 可见为 `false`。
- Projects 门户证据：LibTV 参考截图 `data/processed/runs/web_reference_libtv_logged_in/17-home.png`；AFS 截图 `data/processed/runs/workbench_libtv_home_rebuild/05-project-portal-final.png`；结构化检查 `data/processed/runs/workbench_libtv_home_rebuild/05-project-portal-visible-scan.json`。
- 2026-06-10 LibTV `/project` 全部项目页复刻：LibTV 参考页包含返回、全部项目标题、新建文件夹、开始创作卡、项目卡片和“没有更多了”；AFS 对应为 Projects 内的项目列表模式，通过门户“全部项目”入口切换。
- 项目列表模式浏览器复核：`directoryVisible=true`，返回/新建文件夹/开始创作/没有更多了均可见，`projectCards=9`，可见 `provider/durable memory` 英文命中 `0`，raw project id/type 可见为 `false`。
- 项目列表证据：LibTV 参考截图 `data/processed/runs/web_reference_libtv_logged_in/18-project-page.png`；AFS 截图 `data/processed/runs/workbench_libtv_project_rebuild/01-project-directory.png`；结构化检查 `data/processed/runs/workbench_libtv_project_rebuild/01-project-directory-metrics.json`。
- 2026-06-10 LibTV 案例详情/制作过程复刻：LibTV 案例页参考为沉浸式视频封面、顶部返回/作者/标题/更新时间、底部立即观看/查看制作过程/收藏/分享和横向推荐；“查看制作过程”在同页打开只读画布弹层，包含只读提示、复制项目、节点连线、缩放百分比和节点详情。
- AFS 对应实现：Projects 精选画布卡片进入沉浸式案例详情；详情页可打开只读制作过程弹层，复制入口只切到当前项目创作画布，不执行 provider、不复制真实素材、不写长期记忆。
- 案例/过程浏览器复核：自动刷新后 Projects 内部滚动位置保留，案例按钮可点击；详情页 `detailVisible=true`；制作过程弹层 `processVisible=true`，过程节点 `10` 个、连线 `6` 条，点击节点后选中详情从“视频节点 12”切换为“视频节点 20”。
- 案例/过程证据：LibTV 参考截图 `data/processed/runs/web_reference_libtv_logged_in/21-after-card-click.png`、`data/processed/runs/web_reference_libtv_logged_in/23-process-modal-loaded.png`、`data/processed/runs/web_reference_libtv_logged_in/24-process-node-click.png`；AFS 截图 `data/processed/runs/workbench_libtv_showcase_rebuild/06-showcase-detail.png`、`data/processed/runs/workbench_libtv_showcase_rebuild/08-process-dialog-refined.png`、`data/processed/runs/workbench_libtv_showcase_rebuild/09-process-node-switch.png`；结构化指标 `data/processed/runs/workbench_libtv_showcase_rebuild/10-showcase-process-metrics.json`。
- 2026-06-10 LibTV 左侧菜单复刻：LibTV 菜单参考包含账号、会员入口、首页、模式切换、退出登录、协议/备案信息和右侧暗色遮罩；AFS 对应为 Projects 全局工作台抽屉，包含账号席位、执行投影状态、首页、模式切换、生成能力门、退出占位和规则边界。
- 菜单抽屉浏览器复核：`drawerVisible=true`，导航行 `4` 个，会员/席位行高度 `38px`，默认可见文本未命中 `OPENAI_API_KEY`、`signed URL`、`provider_config`；抽屉不处理真实账号凭据，不启动 provider。
- 菜单抽屉证据：LibTV 参考截图 `data/processed/runs/web_reference_libtv_logged_in/27-after-timeout-state.png`；AFS 截图 `data/processed/runs/workbench_libtv_menu_rebuild/03-menu-drawer-compact.png`；结构化指标 `data/processed/runs/workbench_libtv_menu_rebuild/03-menu-drawer-compact-metrics.json`。
- 2026-06-10 LibTV 门户筛选/搜索复刻：Projects 精选画布从静态占位改为可交互筛选和搜索；浏览器复核筛选“生成门”后只剩 `产品短片自动化画布`，搜索“不存在”后 `cards=0` 且显示“没有匹配的画布”。
- 筛选/搜索证据：AFS 截图 `data/processed/runs/workbench_libtv_showcase_rebuild/11-showcase-filter-empty.png`；结构化指标 `data/processed/runs/workbench_libtv_showcase_rebuild/11-showcase-filter-metrics.json`。
- 2026-06-10 LibTV 开始创作入口复刻：LibTV 点击“开始创作”进入 `/canvas` 空项目，画布中央显示故事脚本生成、角色三视图、首帧图生视频、音频生视频四个紧凑起步节点，底部保留资产管理、添加节点、工具、历史、快捷键、缩放等工具坞。
- AFS 对应实现：Projects“开始创作”直接进入 Create 起步画布，四个入口分别为故事脚本生成、角色三视图、首帧图生视频、音频生视频；右上保留“实际画布”切回 Runtime Service 投影。本轮只做本地配置入口，不启动 provider。
- 创建入口证据：LibTV 参考截图 `data/processed/runs/web_reference_libtv_logged_in/30-create-entry-recheck.png`；AFS 截图 `data/processed/runs/workbench_libtv_create_entry_rebuild/04-starter-canvas-compact.png`；AFS 结构化指标 `data/processed/runs/workbench_libtv_create_entry_rebuild/03-starter-canvas-coordinate-metrics.json`。
- 2026-06-10 LibTV 空画布工具坞复刻：添加节点浮层不再重复展示所有系统状态，收敛为“起步生成 / 链路组织 / 治理与记忆”三组 `6` 个核心生产节点；资产管理抽屉显示“项目输入 / 生成候选 / 记忆证据”三组素材入口，空态不读取本地路径或媒体字节。
- 工具坞浏览器复核：`createVisible=true`，起步节点 `4` 个，添加节点浮层可见，节点调色板分组 `3` 个、节点按钮 `6` 个；资产抽屉可见，素材分组 `3` 个；`providerStartedClaimVisible=false`。
- 工具坞证据：AFS 截图 `data/processed/runs/workbench_libtv_panel_rebuild/01-add-node-palette.png`、`data/processed/runs/workbench_libtv_panel_rebuild/02-assets-drawer.png`；结构化指标 `data/processed/runs/workbench_libtv_panel_rebuild/03-panel-metrics.json`。
- 2026-06-10 LibTV 工具箱/帮助中心复刻：底部工具坞补齐工具箱和帮助中心入口；工具箱第一轮只显示整理画布、切换小地图、网格吸附、跟随选中 `4` 个画布辅助动作，帮助中心显示画布操作、素材安全、生成能力门、审片记忆 `4` 个中文说明。
- 2026-06-10 LibTV TV 工具箱主体骨架补齐：工具箱已提升为 `TV工具箱`，包含 `多角度`、`运镜标记`、`首尾帧`、`图片高清`、`文字生音乐`、`角色库` `6` 个创作工具，并保留 `4` 个画布辅助；这些入口只登记工具意图，真实生成继续由能力门控制。
- TV 工具箱浏览器复核：`tools/workbench_libtv_toolbox_browser_qa.py` 默认覆盖 `desktop` / `tablet` / `mobile` 三视口，manifest `qa_status=passed`、required labels missing `[]`、console/page errors `0`、provider_request_urls `[]`、horizontal viewport overflow `false`；移动端截图显示工具箱内部滚动，不挤出底部工具坞。
- 2026-06-10 TV 工具箱工具意图状态流补齐：`多角度`、`运镜标记`、`首尾帧`、`图片高清`、`文字生音乐`、`角色库` 不再只是静态入口，点击后写入 `studioToolIntent`，按钮 active，并显示 `本地工具意图已登记`、`未创建真实任务`、`未启动 provider` 的工具回执。
- 工具意图浏览器复核：同一 QA 脚本逐视口点击 6 个创作工具，manifest 记录 `intent_clicks`、`active_tool_visible=true`、回执文本命中边界文案、provider_request_urls `[]`；工具箱样式已拆到 `styles-studio-toolbox.css`，维护审计无 oversized warning。
- 2026-06-10 LibTV 画布顶栏状态流补齐：Create 顶栏从静态项目标题/`画布 1` 按钮提升为本地 Canvas Workspace 控制器，包含 `项目名称` 可访问输入、`画布 1` / `画布 2` / `审片画布` 菜单和 `新建画布` 本地意图。
- 画布顶栏浏览器复核：`tools/workbench_libtv_canvas_header_browser_qa.py` 默认覆盖 `desktop` / `tablet` / `mobile` 三视口，标题输入值保持为 `本地画布验收`，`title_aria_label=项目名称`，菜单可见，点击 `画布 2` 和 `新建画布` 后回执命中 `本地画布意图已登记`、`未创建真实画布`、`未启动 provider`；provider_request_urls `[]`、console/page errors `0`、forbidden matches `[]`、horizontal viewport overflow `false`。
- 画布顶栏证据：manifest `data/processed/runs/workbench_libtv_canvas_header_browser_qa/workbench_libtv_canvas_header_browser_qa.json`；菜单截图 `screenshots/{desktop,tablet,mobile}/canvas-menu.png`；回执截图 `canvas-header-{canvas_2,new_canvas}.png`。
- 工具箱/帮助浏览器复核：`toolboxVisible=true`，`toolboxCount=4`，`helpVisible=true`，`helpCount=4`，帮助面板英文残留 `helpEnglishLeak=false`。
- 工具箱/帮助证据：AFS 截图 `data/processed/runs/workbench_libtv_toolbox_rebuild/01-toolbox-panel.png`、`data/processed/runs/workbench_libtv_toolbox_rebuild/02-help-panel.png`；结构化指标 `data/processed/runs/workbench_libtv_toolbox_rebuild/03-toolbox-help-metrics.json`。
- TV 工具箱证据：manifest `data/processed/runs/workbench_libtv_toolbox_browser_qa/workbench_libtv_toolbox_browser_qa.json`；截图 `data/processed/runs/workbench_libtv_toolbox_browser_qa/screenshots/{desktop,tablet,mobile}/toolbox.png` 与 `toolbox-intent-{angles,motion,keyframes,upscale,music,character}.png`。
- 2026-06-10 LibTV 执行链路骨架补齐：Create 实际画布新增 `节点连接`、`参数抽屉` 和 `待执行动作` 三个主体对象，覆盖 3 条本地连接关系、6 个参数占位和 3 个执行意图入口；这些入口只登记本地执行意图，不启动真实生成。
- 执行链路骨架浏览器复核：`tools/workbench_libtv_execution_scaffold_browser_qa.py` 默认覆盖 `desktop` / `tablet` / `mobile` 三视口，manifest `qa_status=passed`、required labels missing `[]`、action count `3`、edge count `3`、parameter count `6`、console/page errors `0`、provider_request_urls `[]`、horizontal viewport overflow `false`；移动端截图完整可读。
- 执行链路骨架证据：manifest `data/processed/runs/workbench_libtv_execution_scaffold_browser_qa/workbench_libtv_execution_scaffold_browser_qa.json`；截图 `data/processed/runs/workbench_libtv_execution_scaffold_browser_qa/screenshots/{desktop,tablet,mobile}/execution-scaffold.png`。
- 2026-06-10 LibTV 执行意图状态流补齐：`生成预检`、`登记执行意图`、`等待能力授权` 不再只是静态按钮，点击后会写入前端内存态 `studioExecutionIntent`，按钮 active，并显示 `本地意图已登记`、`未创建真实任务`、`未启动 provider` 的执行回执。
- 执行意图浏览器复核：同一 QA 脚本逐视口点击 3 个意图，manifest 记录 `intent_clicks`、`active_button_visible=true`、回执文本命中边界文案、provider_request_urls `[]`；移动端 execution layer 调整为单列脚手架，避免顶部栏遮挡节点连接区域。
- 执行意图证据：manifest `data/processed/runs/workbench_libtv_execution_scaffold_browser_qa/workbench_libtv_execution_scaffold_browser_qa.json`；回执截图 `data/processed/runs/workbench_libtv_execution_scaffold_browser_qa/screenshots/{desktop,tablet,mobile}/execution-intent-{preflight,register,wait_gate}.png`。
- 2026-06-10 LibTV 历史资产浮层复核：底部工具坞“历史资产”打开图片/视频/音频历史面板，显示 `6` 条可复用记录、倒序/批量/仅看可复用控制、缩放和关闭入口；卡片从工程历史列表改为生产资产网格。
- 历史资产浏览器复核：首次 QA 发现卡片摘要单行省略导致 `overflowCount=6`；已将历史卡片摘要改为自然换行，复测 `panelVisible=true`、`cardCount=6`、`gridVisible=true`、`consoleErrorCount=0`、`overflowCount=0`、`forbiddenMatches=[]`、`providerStartedClaimVisible=false`、`internalIdLeakVisible=false`。
- 历史资产证据：截图 `data/processed/runs/workbench_libtv_history_rebuild/02-history-panel-after-css-fix.png`；结构化指标 `data/processed/runs/workbench_libtv_history_rebuild/02-history-panel-after-css-fix-metrics.json`。
- 2026-06-10 LibTV 脚本结果节点复核：真实 LibTV `/canvas` 中点击“故事脚本生成”后进入“剧本”内容节点，旁边出现下游承接节点、编辑提示气泡、底部生成控制卡和 `GVLM 3.1` 模型入口；这说明起步节点需要覆盖“结果节点态”，不能只做配置表单。
- 脚本结果节点浏览器复核：AFS Create 起步画布点击“故事脚本生成”后显示脚本内容节点、连线、`双击剧本内容，可直接编辑或替换`、`根据我上传的剧本生成一个完整的故事脚本`、`GVLM 3.1` 和 `Provider 未启动`；复测 `console_error_count=0`、`empty_canvas_hint_visible=false`、`forbidden_matches=[]`。
- 脚本结果节点证据：真实站点截图 `data/processed/runs/web_reference_libtv_live_20260610/02-script-node-content.png`；AFS 截图 `data/processed/runs/workbench_libtv_script_rebuild/04-script-flow-after-tip-layer-fix.png`；结构化指标 `data/processed/runs/workbench_libtv_script_rebuild/04-script-flow-after-tip-layer-fix-metrics.json`。
- 2026-06-10 LibTV 角色三视图节点复核：真实 LibTV `/canvas` 中点击“角色三视图”后进入“角色图 / 角色三视图”双节点，顶部能力条包含 `全景`、`多角度`、`打光`、`九宫格`、`高清`、`宫格切分`，并显示“点击按钮，可替换上传你的角色图”；真实站点同时出现生成器 chunk 加载失败，记录为参考边界，不声明 provider 验证。
- 角色三视图节点浏览器复核：AFS Create 起步画布点击“角色三视图”后显示角色图安全占位、三视图安全占位、顶部能力条、替换提示、`生成器未启动` 和 `Provider Gate 未授权`；复测 `consoleErrorCount=0`、`emptyCanvasHintVisible=false`、`inspectorVisible=false`、`forbiddenMatches=[]`。
- 角色三视图节点证据：真实站点截图 `data/processed/runs/web_reference_libtv_live_20260610/05-character-node-state.png`；AFS 截图 `data/processed/runs/workbench_libtv_character_rebuild/01-character-flow-local-qa.png`；结构化指标 `data/processed/runs/workbench_libtv_character_rebuild/01-character-flow-local-qa-metrics.json`。
- 2026-06-10 LibTV 首帧图生视频节点复核：真实 LibTV `/canvas` 中点击“首帧图生视频”后进入“首帧 / 视频”双节点，控制区包含 `文生视频`、`全能参考`、`图生视频`、`首尾帧`、`图片参考`、`标记`、`运镜`、`角色库`、`Seedance 2.0 VIP` 和 `16:9 · 720P · 5s`，并显示“点击按钮，可替换上传你的首帧图”。
- 首帧图生视频节点浏览器复核：AFS Create 起步画布点击“首帧图生视频”后显示首帧安全占位、视频安全占位、模式 tabs、辅助工具、模型参数和 `视频生成未启动`；复测 `consoleErrorCount=0`、`emptyCanvasHintVisible=false`、`inspectorVisible=false`、`forbiddenMatches=[]`。
- 紧凑布局滚动复核：起步结果流内滚轮不再误触画布缩放，滚动首帧图生视频流后缩放仍为 `100%`，Seedance 参数区和视频未启动边界可访问。
- 首帧图生视频节点证据：真实站点截图 `data/processed/runs/web_reference_libtv_live_20260610/08-image-video-node-state.png`；AFS 截图 `data/processed/runs/workbench_libtv_image_video_rebuild/01-image-video-flow-local-qa.png` 与 `data/processed/runs/workbench_libtv_image_video_rebuild/03-image-video-scroll-fixed.png`；结构化指标 `data/processed/runs/workbench_libtv_image_video_rebuild/01-image-video-flow-local-qa-metrics.json`。
- 2026-06-10 LibTV 音频生视频节点复核：真实 LibTV `/canvas` 中点击“音频生视频”后进入“音频 / 视频”双节点，音频节点显示 `00:00 / 00:03`，控制区包含 `文生视频`、`全能参考`、`图生视频`、`首尾帧`、`图片参考`、`标记`、`运镜`、`角色库`、`Seedance 2.0 VIP`、`16:9 · 720P · 5s`、`1个`、`135`、`联网搜索`、`自动校验素材`，并显示“点击按钮，可替换上传你的音频文件”。
- 音频生视频节点浏览器复核：AFS Create 起步画布点击“音频生视频”后显示音频波形安全占位、视频安全占位、模式 tabs、辅助工具、模型参数、联网/校验开关和 `音频驱动未启动`；复测 `emptyCanvasHintVisible=false`、`inspectorVisible=false`、`forbiddenMatches=[]`、`providerStopped=true`。
- 音频生视频节点证据：真实站点截图 `data/processed/runs/web_reference_libtv_live_20260610/10-audio-video-node-state.png`；AFS 截图 `data/processed/runs/workbench_libtv_audio_video_rebuild/01-audio-video-flow-local-qa.png` 与 `data/processed/runs/workbench_libtv_audio_video_rebuild/02-audio-video-control-card-local-qa.png`；结构化指标 `data/processed/runs/workbench_libtv_audio_video_rebuild/01-audio-video-flow-local-qa-summary.json` 与 `data/processed/runs/workbench_libtv_audio_video_rebuild/02-audio-video-control-card-local-qa-summary.json`。
- 2026-06-10 LibTV 添加节点菜单复核：真实 LibTV `/canvas` 底部“添加节点”浮层包含 `文本`、`图片`、`视频`、`视频合成 Beta`、`导演台 NEW`、`音频`、`脚本`，下方另有 `添加资源` 区，提供 `上传` 和 `从生成历史选择`。
- 添加节点菜单浏览器复核：AFS Create 起步画布底部“添加节点”浮层显示 `7` 个节点按钮、`2` 个资源按钮、`3` 个徽标；所有真实标签均命中，`data-add-node-kind` / `data-add-resource-kind` 正确落到 DOM；复测 `missingLabels=[]`、`forbiddenMatches=[]`、`providerStopped=true`。
- 添加节点菜单证据：真实站点截图 `data/processed/runs/web_reference_libtv_live_20260610/11-add-node-after-coordinate-click.png`；AFS 截图 `data/processed/runs/workbench_libtv_add_node_rebuild/01-add-node-menu-libtv-aligned.png`；结构化指标 `data/processed/runs/workbench_libtv_add_node_rebuild/01-add-node-menu-libtv-aligned-summary.json`。
- 2026-06-10 LibTV 添加菜单节点态复核：AFS 已补齐点击添加菜单项后的本地节点态，覆盖 `文本`、`图片`、`视频`、`视频合成`、`导演台`、`音频`、`脚本`；每个节点只创建安全占位节点和控制卡，显示未启动边界，不读取素材字节、不上传、不调用 provider。
- 添加菜单节点态验证：focused Workbench frontend `10 passed`；HTTP 资源检查显示 `/workbench/src/render-studio-add-node-flow.js`、`/workbench/styles-studio-add-node-flow.css` 和 `/workbench/` 均返回 `200` 且包含目标标记；同时固化了“进入新增节点态后再次点击添加节点必须能重新打开菜单”的回归断言。
- 添加菜单节点态浏览器补证：已新增 `tools/workbench_libtv_add_node_browser_qa.py`，使用本地 Playwright 真实点击添加菜单，覆盖 7 个节点态与 2 个资源态；manifest `data/processed/runs/workbench_libtv_add_node_state_browser_qa/workbench_libtv_add_node_browser_qa.json` 显示 expected selectors 全部可见、console/page errors `0`、forbidden matches `[]`、provider_request_urls `[]`、qa_status `passed`。
- 2026-06-10 LibTV 导演台/视频合成节点态复核：真实 LibTV 取证 `data/processed/runs/web_reference_libtv_logged_in/13-director-node.json` 和 `data/processed/runs/web_reference_libtv_logged_in/14-director-workspace.json` 显示 `导演台` 节点会进入 `3D导演台` 工作区，包含 `导演视角`、`机位视角`、`场景`、对象搜索、`机位1`、`角色A`、摄像机属性、`FOV 50°`、位置/注视坐标、截图、AI 识图导入和全屏入口。
- 导演台/视频合成本地验证：AFS 已将 `导演台` 渲染为本地 3D 导演台控制面，将 `视频合成` 渲染为安全时间线控制面；新增 TDD 文件 `tests/test_web_workbench_libtv_add_node_flows.py` 覆盖 `renderDirectorFlow`、`renderVideoMergeFlow`、关键中文标签和 CSS 类，红灯先失败，绿灯 `2 passed`；与既有 Studio 回归合跑 `3 passed`。
- 导演台/视频合成浏览器补证：`node_director.png` 与 `node_video_merge.png` 已由统一 Playwright QA 产出；两个节点态 selector 可见，Provider 未启动，未命中 secret / signed URL / provider_config。
- 2026-06-10 LibTV 添加资源入口态复刻：AFS 点击添加菜单中的 `上传` 或 `从生成历史选择` 后进入 `resource` 浮层；上传面板显示素材类型、拖放/选择摘要和“不读取本地文件字节”边界，历史面板显示图片/视频/音频历史、时间降序、批量操作和空历史状态。
- 添加资源入口验证：新增 `tests/test_web_workbench_libtv_resource_entries.py`，红灯先失败在缺失资源入口模块和 CSS；实现后 focused Workbench frontend `14 passed`，full pytest `849 passed, 1 warning`，maintenance audit `failed=0, passed=6, warning=0`，HTTP 资源检查命中 `renderResourceEntryPanel`、`libtv-upload-dropzone`、`libtv-history-resource-picker` 和安全文案。
- 添加资源入口浏览器补证：`resource_upload.png` 与 `resource_history.png` 已由统一 Playwright QA 产出；上传/历史入口 selector 可见，console/page errors `0`，Provider 未启动，不读取本地文件字节。
- 2026-06-10 LibTV 图片添加节点态复刻：真实 LibTV `图片节点` 参考包含 `上传`、`尝试：`、`图生图`、`图片高清`、`风格`、`标记`、`Lib Image`、`自适应 · 标准画质 · 2K`、`摄像机`、`全景`、`1张` 和 `18`；AFS 已将添加菜单里的 `图片` 节点从通用占位提升为对应安全控制面。
- 图片添加节点验证：新增红灯断言后先失败在缺失 `renderImageNodeFlow`；实现后 `tests/test_web_workbench_libtv_add_node_flows.py` `3 passed`，focused Workbench frontend `16 passed`，HTTP 资源检查命中目标标记；统一 Playwright QA 已产出 `node_image.png`，selector 可见且 Provider 未启动。
- 2026-06-10 LibTV 脚本添加节点态复刻：真实 LibTV `12-script-node.json/png` 参考包含 `脚本生成器`、`剧本生成分镜脚本`、`视频参考生成分镜脚本`、`角色生成分镜脚本`、`文本节点 2`、`自己编写内容`、`文生视频`、`图片反推提示词`、`文字生音乐` 和 `GVLM 3.1`；AFS 已将添加菜单里的 `脚本` 节点提升为对应安全控制面。
- 脚本添加节点验证：新增红灯断言后先失败在缺失 `renderScriptGeneratorFlow`；实现后 `tests/test_web_workbench_libtv_add_node_flows.py` `4 passed`，focused Workbench frontend `17 passed`，HTTP 资源检查命中目标标记；统一 Playwright QA 已产出 `node_script.png`，selector 可见且 Provider 未启动。
- 2026-06-10 LibTV 文本添加节点态复刻：真实 LibTV `03-text-node.json/png` 参考包含 `文本节点 2`、`尝试：`、`自己编写内容`、`文生视频`、`图片反推提示词`、`文字生音乐`、故事/场景/角色设定提示、`GVLM 3.1` 和数量 `1`；AFS 已将添加菜单里的 `文本` 节点提升为对应安全控制面。
- 文本添加节点验证：新增红灯断言后先失败在缺失 `renderTextNodeFlow`；实现后 `tests/test_web_workbench_libtv_add_node_flows.py` `5 passed`，`tests/test_web_workbench_foundation.py` 与 `tests/test_web_workbench_studio.py` 合计 `10 passed`，HTTP 资源检查命中目标标记；统一 Playwright QA 已产出 `node_text.png`，selector 可见且 Provider 未启动。
- 2026-06-10 LibTV 视频添加节点态复刻：真实 LibTV `08-image-video-node-state-summary.json` 视频控制参考包含 `文生视频`、`全能参考`、`图生视频`、`首尾帧`、`图片参考`、`标记`、`运镜`、`角色库`、`Seedance 2.0 VIP`、`16:9 · 720P · 5s`、`1个`、`135`、`联网搜索` 和 `自动校验素材`；AFS 已将添加菜单里的 `视频` 节点提升为对应安全控制面。
- 视频添加节点验证：新增红灯断言后先失败在缺失 `render-studio-video-node-flow.js`；实现后 `tests/test_web_workbench_libtv_add_node_flows.py`、`tests/test_web_workbench_foundation.py` 与 `tests/test_web_workbench_studio.py` 合计 `16 passed`，HTTP 资源检查命中目标标记；统一 Playwright QA 已产出 `node_video.png`，selector 可见且 Provider 未启动。
- 边界：本轮仍为工程验收前复核，不等于 human acceptance、business validation 或 durable memory promotion；Provider 未启动。

- 2026-06-10 LibTV 音频添加节点态复刻：真实 LibTV `10-audio-video-node-state-summary.json` 音频控制参考包含 `音频节点`、`00:00 / 00:03`、`图片`、`视频`、`文生视频`、`全能参考`、`图生视频`、`首尾帧`、`图片参考`、`标记`、`运镜`、`角色库`、`Seedance 2.0 VIP`、`16:9 · 720P · 5s`、`1个`、`135`、`联网搜索`、`自动校验素材` 和“点击按钮，可替换上传你的音频文件”；AFS 已将添加菜单里的 `音频` 节点提升为对应安全控制面。
- 音频添加节点态验证：新增红灯断言后先失败在缺失 `render-studio-audio-node-flow.js`；实现后 focused Workbench frontend `17 passed`，相关 LibTV/Workbench 扩展测试 `20 passed`，HTTP 资源检查命中目标标记；统一 Playwright QA 已产出 `node_audio.png`，selector 可见、不读取本地文件字节且 Provider 未启动。
- 2026-06-10 LibTV 添加节点/资源多视口 QA：统一 Playwright 脚本默认覆盖 `desktop` / `tablet` / `mobile` 三个视口，共 `27` 个点击态用例；最新 manifest `qa_status=passed`、console/page errors `0`、forbidden matches `[]`、provider_request_urls `[]`、viewport overflow `0`。本轮同时修复移动端底部工具坞宽度、画布节点层窄屏单列、历史素材卡片摘要 clamp 和历史列表内部滚动，截图按视口分目录保存。

## 2026-06-10 LLM/Script Provider Prep QA

- 本切口是 Runtime Service backend-only provider 准备，不新增 Web Workbench UI 功能面，不继续横向复刻 LibTV。
- 新增 `POST /provider/script-draft-plan`，默认 gate closed，创建安全计划、本地确定性脚本/分镜草案、safe manifest 和 run trace。
- Focused API QA：`.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_llm_script_vertical.py -q` -> `3 passed, 1 warning`。
- 验证覆盖：`AFS_ALLOW_REMOTE_LLM` 未设置时 job 为 `blocked`，`provider_calls_started=false`，`remote_provider_calls_started=false`，`raw_provider_response_stored=false`，`generated_media_bytes_stored=false`，`writes_long_term_memory=false`，`writes_company_kb=false`，OpenAPI 暴露新 endpoint 且不出现 `api_key` / `signed_url` 字段；第二轮请求会把上一版脚本 artifact 和审片 note 写入 candidate constraints。
- 最终验证：focused Runtime/API `8 passed, 1 warning`；full pytest `871 passed, 1 warning`；maintenance audit `failed=0, passed=6, warning=0`；CLI help/version 通过；`git diff --check` 仅有 Windows CRLF normalization warnings。
- 浏览器 QA：本切口未新增 UI，因此未新跑浏览器截图；上一轮 Web RC browser QA 只证明 UI 冻结主路径，不证明 provider smoke。
- 边界：这是 provider 纵切工程准备，不是 live provider smoke、human acceptance、business validation 或 durable memory promotion。
## 当前残留风险

- 第一轮仍沿用轻量 JS/CSS 模块，暂不引入 React Flow；如果后续需要复杂拖拽连线，应单独做技术 spike。
- 分镜台第一轮会复用现有 `creation_workspace` / `studio_workspace` 安全投影，真实媒体预览仍需后续 provider 或 artifact contract 明确后再接。
- Stage 7 浏览器 QA 已完成，但这仍只是工程 release candidate；诊断视图可保留内部 id，主视图不得默认暴露。
- Browser 自动化当前不能直接键入中文文本；如果后续要把创建向导的文本输入也纳入自动化，需要修复或替换当前 Browser 输入通道。
- UI 验收不等于 human acceptance、business validation 或 durable memory promotion。

## 2026-06-10 Web RC Freeze QA Gate

- 冻结口径：停止新增 LibTV 功能面，只修 blocker、major UX、可见泄漏、移动端遮挡和测试失败。
- 收口审计：`docs/frontend_integration/AFS_WEB_RC_FREEZE_CLOSEOUT_2026-06-10.zh-CN.md`。
- Company OS candidate feedback：`docs/frontend_integration/AFS_WEB_RC_COMPANY_OS_FEEDBACK_2026-06-10.zh-CN.md`。
- 最终 QA 范围：focused Workbench tests、full pytest、maintenance audit、`git diff --check`、以及 add-node/resource、toolbox、execution scaffold、canvas header 四组浏览器 QA。
- 最终 QA 结果：focused Workbench/LibTV `34 passed`；full pytest `868 passed, 1 warning`；maintenance audit `failed=0, passed=6, warning=0`；四组 browser QA 均为 `qa_status=passed` 且 `provider_request_urls=[]`；CLI help/version 通过，version 为 `0.1.0`；`git diff --check` 仅有 Windows CRLF normalization warnings。
- 验收边界：最终 QA 只产生 runtime verification，不产生 human acceptance、provider smoke、business validation 或 durable memory promotion。
