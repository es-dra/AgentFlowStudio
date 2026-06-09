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
- 边界：本轮仍为工程验收前复核，不等于 human acceptance、business validation 或 durable memory promotion；Provider 未启动。

## 当前残留风险

- 第一轮仍沿用轻量 JS/CSS 模块，暂不引入 React Flow；如果后续需要复杂拖拽连线，应单独做技术 spike。
- 分镜台第一轮会复用现有 `creation_workspace` / `studio_workspace` 安全投影，真实媒体预览仍需后续 provider 或 artifact contract 明确后再接。
- Stage 7 浏览器 QA 已完成，但这仍只是工程 release candidate；诊断视图可保留内部 id，主视图不得默认暴露。
- Browser 自动化当前不能直接键入中文文本；如果后续要把创建向导的文本输入也纳入自动化，需要修复或替换当前 Browser 输入通道。
- UI 验收不等于 human acceptance、business validation 或 durable memory promotion。
