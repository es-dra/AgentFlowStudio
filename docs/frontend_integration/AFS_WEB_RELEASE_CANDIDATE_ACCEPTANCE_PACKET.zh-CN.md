# AFS Web Workbench 发布候选验收包

日期：2026-06-10
分支：`codex/afs-landing-prep-web-plan-001`
当前 head：以 `git log -1 --oneline` 为准；本验收包跟随分支更新，不固定单个提交。
验收对象：Runtime Service 托管的 `/workbench/` 中文创作工作台 release candidate

## 定位

本验收包用于判断当前 Web Workbench 是否已经达到“接入真实 provider 前，可以先由人完整试用并确认体验方向”的状态。

它不是 provider smoke、不是 business validation、不是 durable memory promotion，也不是最终商业化界面验收。

## 前置条件

- Runtime Service 已在本机运行，当前浏览器地址为 `http://127.0.0.1:8790/workbench/`。
- provider 默认关闭；不要在本轮验收中配置或提交 provider secret。
- 只使用 safe summary、safe manifest、safe artifact ref，不导入本地私有媒体字节。
- 验收重点是产品路径和交互体验，不是模型质量。

## 必须验收的主路径

1. 打开 `/workbench/`，确认首屏是中文工作台，而不是工程调试面板。
2. 连接 Runtime Service，能看到项目入口和工作区导航。
3. 从项目列表打开一个项目，优先使用列表里的“验收演练项目”或当前 QA 项目 `proj_stage7_rc_1781016167554`。
4. 检查项目列表：主标题应是项目目标、项目类型或中文归一标题，不应把 raw `project_id`、乱码标题或内部 Stage 7 命名作为主标题。
5. 进入素材库，确认素材/参考只展示摘要，不展示本地绝对路径或媒体字节。
6. 生成或加载画布草稿，确认画布节点、节点状态、右侧检查器和底部操作区能联动。
7. 切换到分镜台，确认镜头序列、当前镜头、安全预览、引用/阻塞事实和审片入口可理解。
8. 切换到审片室，执行一次保留 / 修改 / 拒绝类审片决定。
9. 执行首轮素材检查，记录反馈，再执行下一轮验证。
10. 切换到项目记忆，确认它展示的是“候选复用状态”和“下一轮约束”，没有声称已进入 durable memory。
11. 切换到任务中心，确认任务、阻塞原因和 Provider 预检是独立工作区，不再压在创作主界面上。
12. 打开设置/诊断，确认内部 id、action、job、artifact ref 只在诊断层出现。
13. 在 1366x768、1440x900 和移动宽度下快速查看页面，确认没有严重错位、按钮不可见或文本溢出。

## 通过标准

- 用户能用“项目 -> 素材 -> 画布 -> 分镜 -> 审片 -> 记忆 -> 任务”的心智完成一轮操作。
- 主界面默认语言是中文，不需要理解 `project_id`、`job_id`、`artifact_id` 或 action 枚举才能继续。
- 首屏项目列表不把历史演练 id、乱码标题、英文 demo 文案或内部 Stage 7 命名暴露为用户主标题。
- 诊断信息存在，但不压过创作工作流。
- Provider Gate 明确显示阻塞和预检状态，没有暗示已经调用真实模型。
- 所有关键动作都有可见的成功、失败、阻塞或禁用反馈。
- 主路径体验接近常规画布/影视创作工具的低学习成本，而不是要求用户理解 AFS 内部工程对象。

## 不通过时的记录格式

每个问题按下面格式记录，便于下一轮直接修复：

```text
位置：
操作：
预期：
实际：
严重度：blocker / major / minor
截图：
是否涉及安全边界：是 / 否
```

## 当前工程证据

- Stage 7 QA 项目：`proj_stage7_rc_1781016167554`。
- 可视化演示索引：`docs/frontend_integration/AFS_WEB_RC_DEMO_INDEX.zh-CN.html`。
- 浏览器 QA：console error `0`，主视图可见英文 `false`，主视图内部 id 泄漏 `false`，文字溢出 `0`。
- 人工验收前演练：刷新 `/workbench/` 后自动连接 Runtime Service，8 个工作区均可切换；console error `0`，列出的英文残留/内部 id/本地路径残留 `0`，文字溢出 `0`。
- 2026-06-10 浏览器主路径复核：`tools/workbench_vertical_flow_browser_smoke.py` 已适配中文多工作区外壳，最新项目 `proj_browser_vertical_1781030891` 达到 `ready_for_next_round`，Provider 调用仍未启动。
- 2026-06-10 PM 复核补充：Create 视图不再暴露 `completed_with_blocks` 或英文 project-materials blocker；这些可见泄漏已纳入 smoke 硬断言，且 RuntimeStore 已覆盖损坏 `artifact_index.json` 的本地恢复路径。
- 2026-06-10 视口工作台复核：页面不再作为整页长报表滚动；当前应用壳锁定在视口内，导航区和工作区分别内部滚动，Projects/Create/Jobs/Settings 在 917x791 浏览器下页面高度均等于视口高度。
- 2026-06-10 工作区主任务优先复核：Projects 首屏先显示项目中心与项目操作，Assets 首屏先显示素材库，Settings 首屏先显示高级诊断与活动时间线，不再把通用生产状态面板置于诊断页顶部。
- 2026-06-10 首屏中文体验复核已纳入自动 smoke 硬断言：`old_project_ids_visible=false`，`question_mark_runs=0`，`stage_rc_visible=false`，`toast_errors=[]`；旧英文 projection 文案扫描命中 `0`。
- 2026-06-10 Canvas V2 工程复核：Create 视图已切到暗色媒体画布，旧窗口头隐藏，节点预览/素材缩略/检查器预览/分镜条均可见；可见 `Provider` 文案命中 `0`，文字溢出 `0`。
- 2026-06-10 Canvas V2 聚焦窗口复核：Create 内部可切换画布、素材、审片、检查器和运行窗口；未打开安全产物前不再显示空 artifact panel。
- 2026-06-10 Canvas V2 降噪复核：Create 画布保留规划、制作、审片和复用模式，但移除阶段条、模式卡片、节点摘要、引用数和零值状态标签；运行摘要改为进入“运行”窗口后查看。
- 2026-06-10 LibTV 画布页复刻复核：Create 视图已重做为全屏点阵画布，隐藏全局顶栏/左侧导航，只保留项目入口、生成能力门、生产节点和底部工具坞；底部工具坞可以打开添加节点、资产、历史、快捷键、节点检查器，右上角生成能力门可以打开 blocker 面板。
- 2026-06-10 画布交互证据：底部缩放按钮将画布从 `100%` 放大到 `110%`；空白区域拖拽后节点层 transform 更新为 `translate3d(90px, 50px, 0px) scale(1.1)`，证明当前具备轻量无限画布交互，而不是静态背景。
- 2026-06-10 LibTV 登录首页/创作门户复刻：Projects 页已从工程项目总览改为全屏暗色创作门户，首屏为三张能力横幅、最近项目、开始创作和精选画布；旧项目总览面板不再可见，首页不再堆叠项目就绪度、命令中心和制作流程状态面板。
- 2026-06-10 Projects 门户浏览器证据：可见英文 `provider/durable memory` 命中 `0`，raw project id/type 可见为 `false`，横幅 `3` 张、最近项目卡 `5` 张、精选画布 `6` 张，旧 `.project-hub-panel` 不可见。
- 2026-06-10 LibTV `/project` 全部项目页复刻：Projects 页新增“全部项目”模式，保留返回、全部项目标题、新建文件夹按钮、开始创作卡、项目卡片和“没有更多了”结构；浏览器证据显示项目卡 `9` 张，raw project id/type 可见为 `false`。
- 2026-06-10 LibTV 案例详情/制作过程复刻：Projects 精选画布可进入沉浸式案例详情，详情页包含返回、作者、标题、更新时间、立即观看、查看制作过程、收藏/分享和底部案例切换；“查看制作过程”打开只读过程弹层。
- 2026-06-10 制作过程浏览器证据：Projects 自动刷新后内部滚动位置仍保持在案例区，点击“查看流程”进入详情；弹层显示只读模式和复制到项目入口，过程节点 `10` 个、连线 `6` 条，点击节点可切换安全摘要；Provider 未启动。
- 2026-06-10 LibTV 左侧菜单复刻：Projects 左上菜单打开全局工作台抽屉，包含账号席位、执行投影状态、首页、模式切换、生成能力门、退出占位和规则边界；不处理真实账号凭据。
- 2026-06-10 LibTV 门户筛选/搜索复刻：Projects 精选画布支持分类筛选和搜索空态；筛选“生成门”后只显示 `产品短片自动化画布`，搜索“不存在”后显示“没有匹配的画布”。
- 2026-06-10 LibTV 开始创作入口复刻：Projects“开始创作”直接进入 Create 起步画布，提供故事脚本生成、角色三视图、首帧图生视频、音频生视频四个生产入口，并保留“实际画布”切换回 Runtime 投影。
- 2026-06-10 LibTV 空画布工具坞复刻：Create 起步画布的添加节点浮层收敛为“起步生成 / 链路组织 / 治理与记忆”三组 `6` 个核心生产节点；资产管理抽屉显示“项目输入 / 生成候选 / 记忆证据”三组素材入口；Provider 未启动。
- 2026-06-10 LibTV 工具箱/帮助中心复刻：底部工具坞补齐工具箱和帮助中心；工具箱含整理画布、切换小地图、网格吸附、跟随选中 `4` 个入口，帮助中心含画布操作、素材安全、生成能力门、审片记忆 `4` 个中文说明。
- 2026-06-10 LibTV 历史资产浮层复刻：底部工具坞“历史资产”打开生产资产网格，包含图片/视频/音频历史、倒序/批量/仅看可复用控制、缩放和关闭入口；复测 `6` 条可复用记录、`consoleErrorCount=0`、`overflowCount=0`、安全命中 `0`，Provider 未启动。
- 2026-06-10 LibTV 脚本结果节点复刻：真实 LibTV 点击“故事脚本生成”后进入“剧本”内容节点；AFS 对应为 Create 起步画布中的脚本内容卡、下游承接节点、连线、编辑提示、底部生成控制卡、`GVLM 3.1` 和 `Provider 未启动`。
- 2026-06-10 LibTV 角色三视图节点复刻：真实 LibTV 点击“角色三视图”后进入“角色图 / 角色三视图”双节点，并显示 `全景`、`多角度`、`打光`、`九宫格`、`高清`、`宫格切分` 能力条；AFS 对应为 Create 起步画布中的角色图安全占位、三视图安全占位、替换提示、能力条、`生成器未启动` 和 `Provider Gate 未授权`。
- 2026-06-10 LibTV 首帧图生视频节点复刻：真实 LibTV 点击“首帧图生视频”后进入“首帧 / 视频”双节点，控制区包含 `文生视频`、`全能参考`、`图生视频`、`首尾帧`、`图片参考`、`标记`、`运镜`、`角色库`、`Seedance 2.0 VIP` 和 `16:9 · 720P · 5s`；AFS 对应为 Create 起步画布中的首帧安全占位、视频安全占位、替换提示、模式 tabs、辅助工具、模型参数和 `视频生成未启动`。
- 2026-06-10 LibTV 添加节点菜单复刻：真实 LibTV 底部“添加节点”浮层包含 `文本`、`图片`、`视频`、`视频合成 Beta`、`导演台 NEW`、`音频`、`脚本`，并在 `添加资源` 下提供 `上传` 和 `从生成历史选择`；AFS 对应为 Create 起步画布中的 7 个节点入口、2 个资源入口和 3 个徽标，DOM 复核 `data-add-node-kind` / `data-add-resource-kind` 均正确，未点击上传/历史/生成。
- 2026-06-10 LibTV 添加菜单节点态复刻：AFS 点击 `文本`、`图片`、`视频`、`视频合成`、`导演台`、`音频` 或 `脚本` 后进入本地安全节点态，显示节点摘要、控制卡、模式按钮和对应“未启动”边界；资源入口只切换资产或历史面板，不执行上传或历史读取。
- 2026-06-10 LibTV 导演台/视频合成节点态复刻：AFS 点击 `导演台` 后进入本地 `3D导演台` 控制面，覆盖导演/机位/场景视角、对象搜索、`机位1`、`角色A`、摄像机属性、`FOV 50°`、位置/注视坐标、截图、AI 识图导入和全屏入口；点击 `视频合成` 后进入安全时间线控制面，覆盖 3 段安全引用片段、片段排序、转场、节奏、统一画幅和 `视频合成未启动`。已补 Playwright 点击截图与结构化指标。
- 2026-06-10 LibTV 添加资源入口态复刻：AFS 点击 `上传` 后进入上传素材安全投影，显示图片/视频/音频/文本类型、拖放或选择安全摘要和“不读取本地文件字节”边界；点击 `从生成历史选择` 后进入历史素材选择投影，显示图片/视频/音频历史、时间降序、批量操作和空历史状态。已补 Playwright 点击截图与结构化指标。
- 2026-06-10 LibTV 图片添加节点态复刻：AFS 点击添加菜单里的 `图片` 后进入图片节点安全控制面，覆盖 `上传`、`图生图`、`图片高清`、`风格`、`标记`、`Lib Image`、`自适应 · 标准画质 · 2K`、`摄像机 · 全景`、`1张 · 18` 和 `图片生成未启动`。已补 Playwright 点击截图与结构化指标。
- 2026-06-10 LibTV 脚本添加节点态复刻：AFS 点击添加菜单里的 `脚本` 后进入脚本生成器安全控制面，覆盖 `脚本生成器`、`剧本生成分镜脚本`、`视频参考生成分镜脚本`、`角色生成分镜脚本`、`文本节点 2`、`自己编写内容`、`文生视频`、`图片反推提示词`、`文字生音乐`、`GVLM 3.1` 和 `脚本生成未启动`。已补 Playwright 点击截图与结构化指标。
- 2026-06-10 LibTV 文本添加节点态复刻：AFS 点击添加菜单里的 `文本` 后进入文本节点安全控制面，覆盖 `文本节点 2`、`尝试：`、`自己编写内容`、`文生视频`、`图片反推提示词`、`文字生音乐`、故事/场景/角色设定提示、`GVLM 3.1`、`1` 和 `文本生成未启动`。已补 Playwright 点击截图与结构化指标。
- 2026-06-10 LibTV 视频添加节点态复刻：AFS 点击添加菜单里的 `视频` 后进入视频节点安全控制面，覆盖 `视频节点`、`文生视频`、`全能参考`、`图生视频`、`首尾帧`、`图片参考`、`标记`、`运镜`、`角色库`、`Seedance 2.0 VIP`、`16:9 · 720P · 5s`、`1个`、`135`、`联网搜索`、`自动校验素材` 和 `视频生成未启动`。已补 Playwright 点击截图与结构化指标。
- 2026-06-10 LibTV 音频添加节点态复刻：AFS 点击添加菜单里的 `音频` 后进入音频节点安全控制面，覆盖 `音频节点`、`00:00 / 00:03`、`图片`、`视频`、`文生视频`、`全能参考`、`图生视频`、`首尾帧`、`图片参考`、`标记`、`运镜`、`角色库`、`Seedance 2.0 VIP`、`16:9 · 720P · 5s`、`1个`、`135`、`联网搜索`、`自动校验素材` 和 `音频生成未启动`。已补 Playwright 点击截图与结构化指标。
- 当前节点态 QA 边界：focused Workbench frontend、HTTP 资源检查与本地 Playwright 点击 QA 已通过；统一节点态 manifest 默认覆盖 `desktop` / `tablet` / `mobile` 三个视口，共 `27` 个点击态用例，显示 7 个节点态与 2 个资源态 expected selectors 全部可见，console/page errors `0`、forbidden matches `[]`、provider_request_urls `[]`、viewport overflow `0`。移动端已修复底部工具坞宽度、画布节点层窄屏单列、历史素材卡片摘要截断和历史列表内部滚动。这仍不等于 human acceptance、business validation 或 provider smoke。
- 主路径计数：素材 `1` 个，画布节点 `4` 个，分镜镜头 `3` 个，项目风格偏好 `1` 条，任务 `6` 个，Provider blocker `4` 个。
- 截图：
  - `data/processed/runs/workbench_live_demo/qa/stage7-rc-1440x900-diagnostics.png`
  - `data/processed/runs/workbench_live_demo/qa/stage7-rc-1366x768.png`
  - `data/processed/runs/workbench_live_demo/qa/stage7-rc-390x844.png`
  - `data/processed/runs/workbench_live_demo/qa/acceptance-rehearsal-auto-connect-clean-1440x900.png`
  - `data/processed/runs/workbench_browser_smoke/browser_evidence/workbench-ready-for-next-round.png`
  - `data/processed/runs/workbench_canvas_v2_qa/canvas-v2-create-1440x900-visual-final.png`
  - `data/processed/runs/workbench_canvas_v2_focus_qa/focus-canvas-1440x900-no-empty-artifact.png`
  - `data/processed/runs/workbench_canvas_v2_focus_qa/focus-review-1440x900-no-empty-artifact.png`
  - `data/processed/runs/workbench_canvas_v2_focus_qa/focus-ops-1440x900-no-empty-artifact.png`
  - `data/processed/runs/workbench_canvas_declutter_audit/create-declutter-canvas.png`
  - `data/processed/runs/workbench_libtv_canvas_rebuild/08-refined-canvas.png`
  - `data/processed/runs/workbench_libtv_canvas_rebuild/10-panel-gate-fixed.png`
  - `data/processed/runs/web_reference_libtv_logged_in/17-home.png`
  - `data/processed/runs/workbench_libtv_home_rebuild/05-project-portal-final.png`
  - `data/processed/runs/web_reference_libtv_logged_in/18-project-page.png`
  - `data/processed/runs/workbench_libtv_project_rebuild/01-project-directory.png`
  - `data/processed/runs/web_reference_libtv_logged_in/21-after-card-click.png`
  - `data/processed/runs/web_reference_libtv_logged_in/23-process-modal-loaded.png`
  - `data/processed/runs/web_reference_libtv_logged_in/24-process-node-click.png`
  - `data/processed/runs/workbench_libtv_showcase_rebuild/06-showcase-detail.png`
  - `data/processed/runs/workbench_libtv_showcase_rebuild/08-process-dialog-refined.png`
  - `data/processed/runs/workbench_libtv_showcase_rebuild/09-process-node-switch.png`
  - `data/processed/runs/web_reference_libtv_logged_in/27-after-timeout-state.png`
  - `data/processed/runs/workbench_libtv_menu_rebuild/03-menu-drawer-compact.png`
  - `data/processed/runs/workbench_libtv_showcase_rebuild/11-showcase-filter-empty.png`
  - `data/processed/runs/web_reference_libtv_logged_in/30-create-entry-recheck.png`
  - `data/processed/runs/workbench_libtv_create_entry_rebuild/04-starter-canvas-compact.png`
  - `data/processed/runs/workbench_libtv_panel_rebuild/01-add-node-palette.png`
  - `data/processed/runs/workbench_libtv_panel_rebuild/02-assets-drawer.png`
  - `data/processed/runs/workbench_libtv_toolbox_rebuild/01-toolbox-panel.png`
  - `data/processed/runs/workbench_libtv_toolbox_rebuild/02-help-panel.png`
  - `data/processed/runs/workbench_libtv_history_rebuild/02-history-panel-after-css-fix.png`
  - `data/processed/runs/web_reference_libtv_live_20260610/02-script-node-content.png`
  - `data/processed/runs/workbench_libtv_script_rebuild/04-script-flow-after-tip-layer-fix.png`
  - `data/processed/runs/web_reference_libtv_live_20260610/05-character-node-state.png`
  - `data/processed/runs/workbench_libtv_character_rebuild/01-character-flow-local-qa.png`
  - `data/processed/runs/web_reference_libtv_live_20260610/08-image-video-node-state.png`
  - `data/processed/runs/workbench_libtv_image_video_rebuild/03-image-video-scroll-fixed.png`
  - `data/processed/runs/web_reference_libtv_live_20260610/10-audio-video-node-state.png`
  - `data/processed/runs/workbench_libtv_audio_video_rebuild/01-audio-video-flow-local-qa.png`
  - `data/processed/runs/workbench_libtv_audio_video_rebuild/02-audio-video-control-card-local-qa.png`
  - `data/processed/runs/web_reference_libtv_live_20260610/11-add-node-after-coordinate-click.png`
  - `data/processed/runs/workbench_libtv_add_node_rebuild/01-add-node-menu-libtv-aligned.png`
  - `data/processed/runs/workbench_libtv_add_node_state_browser_qa/screenshots/desktop/node_text.png`
  - `data/processed/runs/workbench_libtv_add_node_state_browser_qa/screenshots/desktop/node_image.png`
  - `data/processed/runs/workbench_libtv_add_node_state_browser_qa/screenshots/desktop/node_video.png`
  - `data/processed/runs/workbench_libtv_add_node_state_browser_qa/screenshots/desktop/node_audio.png`
  - `data/processed/runs/workbench_libtv_add_node_state_browser_qa/screenshots/desktop/node_script.png`
  - `data/processed/runs/workbench_libtv_add_node_state_browser_qa/screenshots/desktop/node_director.png`
  - `data/processed/runs/workbench_libtv_add_node_state_browser_qa/screenshots/desktop/node_video_merge.png`
  - `data/processed/runs/workbench_libtv_add_node_state_browser_qa/screenshots/mobile/resource_upload.png`
  - `data/processed/runs/workbench_libtv_add_node_state_browser_qa/screenshots/mobile/resource_history.png`
- 结构化证据：`data/processed/runs/workbench_live_demo/qa/stage7-rc-browser-qa.json`。
  - Canvas V2 降噪审计：`data/processed/runs/workbench_canvas_declutter_audit/create-declutter-current.json`。
  - LibTV 画布复刻交互证据：`data/processed/runs/workbench_libtv_canvas_rebuild/09-pan-zoom-metrics.json`、`data/processed/runs/workbench_libtv_canvas_rebuild/10-panel-results.json`、`data/processed/runs/workbench_libtv_canvas_rebuild/10-panel-gate-fixed.json`。
  - LibTV 首页/Projects 门户复刻证据：`data/processed/runs/workbench_libtv_home_rebuild/05-project-portal-visible-scan.json`。
  - LibTV 全部项目页复刻证据：`data/processed/runs/workbench_libtv_project_rebuild/01-project-directory-metrics.json`。
  - AFS 案例/制作过程复刻指标：`data/processed/runs/workbench_libtv_showcase_rebuild/10-showcase-process-metrics.json`。
  - LibTV 案例/制作过程复刻 DOM 证据：`data/processed/runs/web_reference_libtv_logged_in/21-detail-visible-dom.json`、`data/processed/runs/web_reference_libtv_logged_in/23-process-modal-dom.json`、`data/processed/runs/web_reference_libtv_logged_in/24-process-node-click-dom.json`。
  - LibTV 菜单抽屉复刻指标：`data/processed/runs/workbench_libtv_menu_rebuild/03-menu-drawer-compact-metrics.json`。
  - LibTV 精选画布筛选/搜索指标：`data/processed/runs/workbench_libtv_showcase_rebuild/11-showcase-filter-metrics.json`。
  - LibTV 开始创作入口复刻指标：`data/processed/runs/workbench_libtv_create_entry_rebuild/03-starter-canvas-coordinate-metrics.json`。
  - LibTV 空画布工具坞复刻指标：`data/processed/runs/workbench_libtv_panel_rebuild/03-panel-metrics.json`。
  - LibTV 工具箱/帮助中心复刻指标：`data/processed/runs/workbench_libtv_toolbox_rebuild/03-toolbox-help-metrics.json`。
  - LibTV 历史资产浮层复刻指标：`data/processed/runs/workbench_libtv_history_rebuild/02-history-panel-after-css-fix-metrics.json`。
  - LibTV 脚本结果节点复刻指标：`data/processed/runs/workbench_libtv_script_rebuild/04-script-flow-after-tip-layer-fix-metrics.json`。
  - LibTV 角色三视图节点复刻指标：`data/processed/runs/workbench_libtv_character_rebuild/01-character-flow-local-qa-metrics.json`。
  - LibTV 首帧图生视频节点复刻指标：`data/processed/runs/workbench_libtv_image_video_rebuild/01-image-video-flow-local-qa-metrics.json`。
  - 首帧图生视频紧凑布局滚动修复指标：`data/processed/runs/workbench_libtv_image_video_rebuild/03-image-video-scroll-fixed-metrics.json`。
  - LibTV 音频生视频节点复刻指标：`data/processed/runs/workbench_libtv_audio_video_rebuild/01-audio-video-flow-local-qa-summary.json`。
  - LibTV 音频生视频控制卡指标：`data/processed/runs/workbench_libtv_audio_video_rebuild/02-audio-video-control-card-local-qa-summary.json`。
  - LibTV 添加节点菜单复刻指标：`data/processed/runs/workbench_libtv_add_node_rebuild/01-add-node-menu-libtv-aligned-summary.json`。
  - LibTV 添加节点/资源状态统一浏览器 QA：`data/processed/runs/workbench_libtv_add_node_state_browser_qa/workbench_libtv_add_node_browser_qa.json`，截图按 `screenshots/{desktop,tablet,mobile}/` 分目录保存。
  - LibTV 导演台真实参考 DOM：`data/processed/runs/web_reference_libtv_logged_in/13-director-node.json`、`data/processed/runs/web_reference_libtv_logged_in/14-director-workspace.json`。
  - LibTV 添加资源入口本地验证：`tests/test_web_workbench_libtv_resource_entries.py`、`apps/workbench/src/render-studio-resource-entry.js`、`apps/workbench/styles-studio-resource-entry.css`。
  - LibTV 图片节点真实参考与本地验证：`data/processed/runs/web_reference_libtv_logged_in/15-image-node.json`、`tests/test_web_workbench_libtv_add_node_flows.py`、`apps/workbench/src/render-studio-add-node-flow.js`。
  - LibTV 脚本节点真实参考与本地验证：`data/processed/runs/web_reference_libtv_logged_in/12-script-node.json`、`tests/test_web_workbench_libtv_add_node_flows.py`、`apps/workbench/src/render-studio-add-node-flow.js`、`apps/workbench/styles-studio-script-generator-flow.css`。
  - LibTV 文本节点真实参考与本地验证：`data/processed/runs/web_reference_libtv_logged_in/03-text-node.json`、`tests/test_web_workbench_libtv_add_node_flows.py`、`apps/workbench/src/render-studio-add-node-flow.js`、`apps/workbench/styles-studio-text-node-flow.css`。
  - LibTV 视频控制参考与本地验证：`data/processed/runs/web_reference_libtv_live_20260610/08-image-video-node-state-summary.json`、`tests/test_web_workbench_libtv_add_node_flows.py`、`apps/workbench/src/render-studio-video-node-flow.js`、`apps/workbench/styles-studio-video-node-flow.css`。
  - LibTV 音频控制参考与本地验证：`data/processed/runs/web_reference_libtv_live_20260610/10-audio-video-node-state-summary.json`、`tests/test_web_workbench_libtv_audio_add_node_flow.py`、`apps/workbench/src/render-studio-audio-node-flow.js`、`apps/workbench/styles-studio-audio-node-flow.css`。

## 2026-06-10 Web RC 冻结收口

- 当前阶段已停止继续横向扩展 LibTV 功能面；后续只修 blocker、major UX、可见泄漏、移动端遮挡和测试失败。
- 收口审计、dirty worktree 分类、接近 300 行模块检查、provider 纵切建议和 COS candidate feedback 已记录在 `docs/frontend_integration/AFS_WEB_RC_FREEZE_CLOSEOUT_2026-06-10.zh-CN.md`。
- 本轮新增和修改的 Workbench JS/CSS/test/tool 均归属当前 Web Workbench RC；`apps/workbench/styles-studio-canvas-focus.css` 为已退役样式删除项。
- 当前没有文件超过 300 行；`tests/test_web_workbench_foundation.py` 为 300 行，`apps/workbench/src/display-labels.js` 为 291 行，后续再扩展时应优先拆分。
- 下一条 provider 纵切建议从 LLM/script 开始：用户目标 -> 脚本/分镜文本 safe artifact -> 审片反馈 -> 第二轮复用反馈；image provider 第二步，video provider 第三步。
- Company OS feedback: `docs/frontend_integration/AFS_WEB_RC_COMPANY_OS_FEEDBACK_2026-06-10.zh-CN.md`。
- 最终工程 QA：focused Workbench/LibTV `34 passed`；full pytest `868 passed, 1 warning`；maintenance audit `failed=0, passed=6, warning=0`；add-node/resource、toolbox、execution scaffold、canvas header 四组 browser QA 均为 `qa_status=passed` 且 `provider_request_urls=[]`；`git diff --check` 仅有 Windows CRLF normalization warnings。
- 本状态仍是工程 RC，不是人工验收、provider smoke、business validation 或 durable memory promotion。

## 2026-06-10 LLM/Script Provider 纵切准备

- 已新增 `POST /provider/script-draft-plan`，用于在真实 provider smoke 前创建 gate-closed 的 LLM/script 安全计划。
- 默认 `AFS_ALLOW_REMOTE_LLM` 关闭时，该 endpoint 写入 `llm_script_request_plan`、本地确定性 `script_storyboard_safe_artifact`、`script_provider_safe_manifest` 和 run trace，job 状态为 `blocked`，不启动远程 LLM。
- Review feedback 只作为 `candidate_constraints_only` 复用；第二轮会把上一版脚本 artifact 和审片 note 写入 candidate constraints，不写入 durable memory 或 Company KB。
- Focused API 验证：`.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_llm_script_vertical.py -q` -> `3 passed, 1 warning`。
- 最终验证：focused Runtime/API `8 passed, 1 warning`；full pytest `871 passed, 1 warning`；maintenance audit `failed=0, passed=6, warning=0`；CLI help/version 通过，version `0.1.0`；`git diff --check` 仅有 Windows CRLF normalization warnings。
- 收口包：`docs/frontend_integration/AFS_PROVIDER_LLM_SCRIPT_VERTICAL_PREP_2026-06-10.zh-CN.md`。
- Company OS feedback: `docs/frontend_integration/AFS_PROVIDER_LLM_SCRIPT_COMPANY_OS_FEEDBACK_2026-06-10.zh-CN.md`。
- 本状态是 provider 纵切工程准备，不是 live provider smoke、human acceptance、business validation 或 durable memory promotion。

## 当前边界

- 没有真实 provider 调用。
- 没有写入 secret、signed URL、本地私有素材、provider 原始响应或生成媒体字节。
- Runtime verification 不等于 human acceptance。
- Provider smoke 不等于 business validation。
- 反馈和候选记忆不自动晋升为 durable memory。
- 本演练仍不等于人工验收结论。

## 验收后的下一步

如果人工验收通过：

1. 固定当前 Web release candidate，补最后的提交前代码审查。
2. 按 capability gate 单独准备 provider smoke，不复用本轮 QA 结论。
3. provider smoke 只验证真实模型接入链路，不宣称商业效果。
4. smoke 通过后，再进入提交、合并、推送和分支清理。

如果人工验收不通过：

1. 先按问题严重度修复 blocker 和 major。
2. 重新跑浏览器主路径、focused tests、maintenance audit 和 diff check。
3. 更新本验收包或 QA 账本中的残留风险。
