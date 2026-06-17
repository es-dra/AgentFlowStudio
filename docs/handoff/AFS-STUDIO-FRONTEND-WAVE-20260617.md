# AFS Studio 前端工作台第一轮改造记录（2026-06-17）

## 范围

本轮只改 `/studio/` 桌面端前端体验，不触发 provider，不改服务器配置，不做移动端适配。

## 已完成

- 增加 Studio favicon，并让 `/favicon.ico` 重定向到 `/studio/favicon.svg`。
- 增加项目工作台弹层，集中展示当前项目、Runtime readiness、Provider gates 和 workflow starters。
- 增加 workflow starter 模板：故事到关键帧、人物资产卡、场景资产卡、首帧到视频、视频资产修订。
- 增加 Action Registry，作为 Add Node 菜单的分组来源，区分基础节点、生产节点、资产节点、资源动作和 gated action。
- 左侧 drawer 增加 Canvas / Assets / Jobs / History 四个 tab。
- 增加 Project Navigator、Job Center、Inspector 三个独立面板模块。
- 节点表面增加状态条，显示 Draft / Ready / Complete 等轻量状态。
- 调整 starter 默认落点，避免默认三节点流程被左侧 drawer 或右侧 Inspector 遮挡。

## 验证

- `node --check` 覆盖本轮改动的 Studio JS 模块。
- `pytest tests\test_web_studio_frontend_wave.py tests\test_web_studio_static.py tests\test_api_runtime_service.py -q`：41 passed。
- `tools\maintenance_audit.py`：failed=0，保留既有 warning。
- `git diff --check`：无 whitespace error，仅保留 CRLF/LF 提示。
- Browser 验证 URL：`http://127.0.0.1:8790/studio/`。
- Browser 交互：打开工作台、查看 5 个 starter、创建 3 节点流程、切换 Canvas / Jobs / History、确认 Inspector 和状态条可见。
- Browser console：error/warn 为 0。
- 布局几何：drawer 右边界 196，节点最左 230；Inspector 左边界 1302，节点最右 1230；左右均无重叠。
- 截图：`C:\Users\chenzy\.codex\backups\AgentFlowStudio\frontend-wave-20260617\studio-wave-verification-final.png`。

## 非声明

- 本轮不是 provider smoke。
- 本轮不是真人验收。
- 本轮不是商业验证。
- 本轮没有写入 Company OS durable memory。

## 后续

- 下一轮可以继续做更深的视觉 polish：Canvas 节点卡片层级、右侧 Inspector 信息密度、工作台弹层动效、资产面板和结果区的视觉统一。
- `apps/studio/src/main.js`、`apps/studio/src/node-actions.js`、`apps/studio/src/panels/drawer.js` 仍是维护审计中的超大文件，后续应继续拆分。

## 第二轮追加优化（2026-06-17）

- 清理项目工作台、workflow starter、Add Node registry 的桌面端文案与分类，使入口更接近“生产工作台”而不是零散按钮集合。
- 将工作台样式拆分为 `studio-workbench.css` 与 `studio-wave.css`，避免单个新增样式文件继续膨胀。
- 固定项目工作台弹层结构：顶部状态、启动模板、最近项目、底部动作区分别有明确 flex 边界；最近项目限制为 5 个并允许局部滚动，避免挤压“继续当前项目 / 新建项目”操作区。
- 增加乱码哨兵测试，覆盖 Studio 新增模块，防止中文文案再次以 mojibake 形式进入源码。

### 第二轮验证

- `node --check` 覆盖本轮 Studio JS 模块：通过。
- `pytest tests\test_web_studio_frontend_wave.py tests\test_web_studio_static.py tests\test_api_runtime_service.py -q`：42 passed，保留 1 个既有 Starlette/httpx warning。
- `tools\maintenance_audit.py`：failed=0，保留既有 legacy/doc/oversized/secret-like test sentinel warning。
- `git diff --check`：无 whitespace error，仅保留 `index.html` 与 `store.js` 的 CRLF/LF 提示。
- `http://127.0.0.1:8790/health`：Runtime ready，studio static ready。
- 本环境未暴露可用的 in-app browser MCP；`agent-browser` skill 存在但 CLI 不在 PATH，因此第二轮布局补丁后的自动截图未重新生成。第一轮可视化截图仍位于 `C:\Users\chenzy\.codex\backups\AgentFlowStudio\frontend-wave-20260617\`。

### 第二轮非声明

- 本轮仍不声明 provider smoke、真人验收、移动端适配或商业验证完成。

## 第三轮追加优化：页面术语降噪（2026-06-17）

- 参考 LibTV 公开页面的表达方式：入口使用“开始创作 / 全部项目 / 新建文件夹 / 创建新的视频项目”等创作者语言，复杂能力不直接暴露为工程术语。
- 将 Studio 工作台中的 `Runtime ready`、`Provider gates`、`safe by default` 等用户可见文案改为“创作服务 / 生成能力 / 按需开启”。
- 将左侧抽屉从 `Canvas / Assets / Jobs / History` 改为“画布 / 素材 / 生成 / 历史”。
- 将右侧详情从 `Inspector / Prompt / Context bundle / Safe manifest / Job / artifact / Fixed assets` 改为“详情 / 创作说明 / 引用内容 / 生成摘要 / 生成记录 / 固定素材”。
- 将状态和结果面板中的 `Job`、`artifact`、`Runtime 安全端点`、`Kling video failed` 等表达改为“任务编号 / 输出编号 / 安全预览地址 / 视频生成请求失败”。
- 将模板标签从 `Narrative / Asset card / I2V / Revision / Draft / Gate` 改为“短剧起步 / 角色设定 / 图生视频 / 修改迭代 / 草稿 / 需确认”。

### 第三轮验证

- 页面术语扫描：目标工程词 `Runtime ready`、`Provider gates`、`Safe manifest`、`Context bundle`、`Job:`、`Reference Asset`、`Kling video` 等不再出现在 Studio 可见源码字符串里。
- `node --check` 覆盖本轮改动 JS：通过。
- `pytest tests\test_web_studio_frontend_wave.py tests\test_web_studio_static.py tests\test_api_runtime_service.py -q`：42 passed，保留 1 个既有 Starlette/httpx warning。
- `tools\maintenance_audit.py`：failed=0，保留既有 warning。
- `git diff --check`：无 whitespace error，仅保留 `index.html` 与 `store.js` 的 CRLF/LF 提示。

### 第三轮剩余不足

- 这只是页面文案降噪，不是完整信息架构重做；深层节点参数、导演台、资产确认表单仍偏专业。
- 未做登录态 LibTV 深层页面逐屏复刻；本轮只根据公开可访问页面和此前观察抽取表达原则。
- 未做新的视觉截图，因为当前环境仍未暴露可用 in-app browser MCP，`agent-browser` CLI 也不在 PATH。

## 第四轮追加优化：视觉入口与快捷创建（2026-06-17）

- 将空画布提示升级为“开始创作一个视频项目”的居中入口，增加双击画布、Tab 添加节点、拖动连线三项操作提示。
- 为 5 个工作流模板增加 tone 标记：短剧、人物、场景、图生视频、修改迭代分别拥有不同低饱和背景、边框和图标色。
- 将空画布模板卡从单行按钮升级为带图标、摘要和标签的小型创作卡。
- 在添加节点菜单顶部新增“双击创建”快捷区，常用入口为文本、图片、视频、脚本、导演台，减少用户从分组列表中寻找节点的步骤。
- 新增 `studio-interactions.css` 承载空画布、快捷创建、模板卡背景纹理和 tone 视觉系统，避免继续撑大既有 CSS 文件。
- 没有引入外部图片或第三方版权素材；背景和按钮质感均由 CSS 纹理、图标和低饱和色块实现。

### 第四轮验证

- `node --check apps/studio/src/main.js apps/studio/src/panels/add-node-menu.js apps/studio/src/project-hub.js apps/studio/src/workflow-starters.js`：通过。
- `pytest tests\test_web_studio_frontend_wave.py tests\test_web_studio_static.py tests\test_api_runtime_service.py -q`：42 passed，保留 1 个既有 Starlette/httpx warning。
- 页面术语扫描：目标工程词仍未回到 Studio 可见源码字符串。
- `tools\maintenance_audit.py`：failed=0，保留既有 warning；新增 `studio-interactions.css` 为 243 行。
- `git diff --check`：无 whitespace error，仅保留 `index.html` 与 `store.js` 的 CRLF/LF 提示。

### 第四轮剩余不足

- 本轮仍未做浏览器截图复核；当前环境没有可用 in-app browser MCP，`agent-browser` CLI 也不在 PATH。
- 结果区、素材库、导演台和资产确认表单还没有完成同等层级的视觉升级。
- 快捷创建目前只覆盖常用节点，尚未做 `/` 命令、整组执行和拖入素材创建节点。

## 第五轮追加优化：媒体结果与生成历史卡片（2026-06-17）

- 将节点结果中的图片/视频预览升级为固定比例的媒体画框，增加预览类型与画幅提示，避免生成结果只是松散图片或文本。
- 为媒体结果增加就地操作区：图片显示“下载图片”，视频显示“下载视频”和“生成视频内容卡”，让用户下一步操作更接近内容生产工作台。
- 将生成队列和生成历史卡片升级为带缩略视觉的列表项：有输出预览的图片任务显示缩略图，视频任务显示视频占位图标，普通任务保留文字状态。
- 新增测试标记覆盖 `node-preview-frame`、`media-result-actions`、`job-thumb`，防止后续前端重构误删这层结果可视化。
- 本轮没有打开 provider，没有下载外部素材，没有引入第三方版权图片；全部视觉增强来自现有 preview URL、CSS 和内置图标。

### 第五轮验证

- `node --check apps/studio/src/node-result-view.js; node --check apps/studio/src/panels/job-center.js`：通过。
- `pytest tests\test_web_studio_frontend_wave.py tests\test_web_studio_static.py tests\test_api_runtime_service.py -q`：42 passed，保留 1 个既有 Starlette/httpx warning。
- 页面术语扫描：目标工程词仍未回到 Studio 可见源码字符串。
- `tools\maintenance_audit.py`：failed=0，保留既有 warning；本轮触及文件均未超过 300 行。
- `git diff --check`：无 whitespace error，仅保留 `index.html` 与 `store.js` 的 CRLF/LF 提示。

### 第五轮剩余不足

- 本轮仍未做浏览器截图复核；当前环境没有可用 in-app browser MCP，`agent-browser` CLI 也不在 PATH。
- 视频内容卡按钮目前只是前端事件入口，仍依赖后续资产卡自动识别链路接入。
- 素材库、导演台、资产确认表单、整组执行和拖入素材创建节点仍是下一轮更深 UI/UX 优化重点。
## 第六轮追加优化：创作门户与作品流（2026-06-18）

- 将顶部“工作台”升级为更接近创作者产品的项目入口：首屏突出“开始创作一个视频项目”，把“短剧起步 / 图生视频 / 修改迭代”作为主要视觉选择，而不是暴露工程状态。
- 新增 `studio-portal.css` 承载项目门户、最近作品、作品卡和创作过程弹层样式，避免继续堆叠既有大 CSS 文件。
- 新增“最近作品”区域：从当前画布节点中提取已产生结果或预览的内容，形成作品卡，并提供“打开作品流”入口。
- 将生成历史面板改为“作品流”，使用缩略图、类型、摘要和“查看创作过程”入口，减少 Job/artifact 等工程术语对用户的干扰。
- 新增 `creation-process-panel.js`：从作品卡进入后展示当前输出、上游来源、当前节点和后续动作入口。第一版只做前端安全展示，不触发 provider。
- 顶部项目下拉继续收敛噪声：默认只显示当前项目、最近项目和少量正常项目，测试/调试项目统一折叠到更多菜单。

### 第六轮验证

- `node --check apps/studio/src/project-hub.js`
- `node --check apps/studio/src/panels/job-center.js`
- `node --check apps/studio/src/panels/creation-process-panel.js`
- `node --check apps/studio/src/main.js`
- `pytest tests\test_web_studio_frontend_wave.py tests\test_web_studio_static.py tests\test_api_runtime_service.py -q`：42 passed，保留 1 个既有 Starlette/httpx warning。
- `http://127.0.0.1:8790/health`：Runtime ready，Studio static ready。
- Browser/Playwright 桌面验证：打开 `/studio/`，确认空画布创作入口可见；点击顶部“工作台”后确认 `project-hub-hero`、`project-hub-visual`、`recent-works-section`、`hero-cta` 均可见；点击“从素材继续”后弹层关闭并切换到“素材”侧栏；console error 为 0。
- 截图：`C:\Users\chenzy\.codex\backups\AgentFlowStudio\afs-portal-20260618\studio-project-hub.png`。

### 第六轮非声明

- 本轮不是 provider smoke，没有调用 LLM / image / video / vision provider。
- 本轮不是真人验收，也不是商业验证。
- 本轮没有改服务器、Nginx、systemd、provider config 或线上数据。
- “查看创作过程”当前是前端过程视图，动作卡仍是下一轮流程接入点，不声明完整创作闭环已经完成。

## 第七轮追加优化：三波次画布成熟体验（2026-06-18）

### Task Startup Packet

- Identity：Engineering Delivery Lead + Studio Interaction Designer + QA/Release Gatekeeper + Rule Steward。
- Context pack：engineering_delivery、afs_project。
- Write scope：仅 `/studio/` 前端交互、样式、静态测试和本 handoff；不改 provider、服务器、Nginx、systemd、secret 或真实生成链路。
- Gates：不打开 LLM / image / video / vision provider；不消耗积分；不上传媒体字节；不记录 provider raw response。
- Verification route：JS syntax、frontend static pytest、Runtime static service tests、maintenance audit、diff check、browser QA。
- Non-claims：本轮不是 provider smoke，不是 human acceptance，不是 business validation，也不是 durable memory promotion。

### Wave 1：画布交互成熟度

- 新增 `apps/studio/src/canvas-context-menu.js`，为空白画布提供右键菜单：添加节点、整理画布、适配视图、全选/清除选择、打开素材和作品流。
- 保留现有节点右键菜单，不覆盖节点菜单逻辑。
- 节点端口增加更明显的 hover / 吸附视觉；画布区域禁止误选网页文本，输入框仍允许正常选字。
- 节点选中并有结果或生成中时显示 `node-context-toolbar`，提供继续、素材、内容卡、过程四个就地动作。

### Wave 2：生成与媒体结果体验

- 新增 `apps/studio/src/panels/generation-panel.js`，用户可在弹层内调整提示词、画幅、张数、镜头说明后再显式开始生成。
- 生成中节点新增 `generation-progress-layer`：支持真实 percent 字段，也支持无 percent 时的非确定进度条。
- 媒体结果新增候选网格结构 `candidate-grid` / `candidate-card`，只读取 safe preview URL，不接触媒体字节。
- 结果区增加继续生成、固定素材、下载和视频内容卡入口。

### Wave 3：作品流与资产化入口

- 创作过程面板的三张动作卡改成真正按钮，通过统一事件回到 `main.js` 编排。
- 作品流卡片增加继续、素材、内容卡入口，和节点工具条保持一致。
- `main.js` 统一监听 `afs:studio-open-generation-panel`、`afs:studio-open-creation-process`、`afs:studio-fix-visual-asset`，避免各面板各自散落调用。

### 新增文件与维护边界

- `apps/studio/src/canvas-context-menu.js`：117 行。
- `apps/studio/src/panels/generation-panel.js`：132 行。
- `apps/studio/styles/studio-canvas-maturity.css`：284 行。
- `apps/studio/styles/studio-media-experience.css`：61 行。
- 新文件均低于 300 行维护阈值；没有引入外部图片、字体、脚本或第三方 UI 依赖。

### 已执行验证

- `node --check apps/studio/src/canvas-context-menu.js`
- `node --check apps/studio/src/panels/generation-panel.js`
- `node --check apps/studio/src/main.js`
- `node --check apps/studio/src/canvas-input.js`
- `node --check apps/studio/src/canvas-view.js`
- `node --check apps/studio/src/node-result-view.js`
- `node --check apps/studio/src/panels/job-center.js`
- `node --check apps/studio/src/panels/creation-process-panel.js`
- `python -m pytest tests/test_web_studio_frontend_wave.py -q`：7 passed。
- `python -m pytest tests/test_web_studio_frontend_wave.py tests/test_web_studio_static.py tests/test_api_runtime_service.py -q`：43 passed，保留 1 个既有 Starlette/httpx warning。

### 待最终补充

- 本节后续还需追加：maintenance audit、`git diff --check` 和浏览器 QA 截图/控制台结果。

### 最终验证补充

- `python -m pytest tests/test_web_studio_frontend_wave.py tests/test_web_studio_static.py tests/test_api_runtime_service.py -q`：43 passed，保留 1 个既有 Starlette/httpx warning。
- `python tools/maintenance_audit.py`：failed=0，保留既有 legacy/doc/secret-like/oversized warning。
- `git diff --check`：通过，仅提示 `apps/studio/index.html` 与 `apps/studio/src/store.js` 的既有 CRLF/LF 转换 warning。
- Runtime health：`http://127.0.0.1:8790/health` 返回 ready，`studio_static.status=ready`。
- Playwright 浏览器 QA：
  - URL：`http://127.0.0.1:8790/studio/?project=frontend-maturity-1781720737`
  - 断言通过：`.node.has-media-result`、`.candidate-grid`、`.node-context-toolbar`、`.generation-panel`、`.canvas-context-menu`。
  - Console：error=0，warning=0。
  - 截图目录：`C:\Users\chenzy\.codex\backups\AgentFlowStudio\frontend-maturity-20260618`。
- 生成设置浮层复核：
  - URL：`http://127.0.0.1:8790/studio/?project=frontend-maturity-float-1781720936`
  - 断言：`panel_overlaps_node=false`。
  - Console：error=0，warning=0。
  - 截图：`C:\Users\chenzy\.codex\backups\AgentFlowStudio\frontend-maturity-20260618\studio-maturity-floating-panel.png`。
