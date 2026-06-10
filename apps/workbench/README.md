# AFS Workbench

`apps/workbench` 是面向 Runtime Service 的产品工作台基础层。它和
`apps/web` 分开维护：`apps/web` 继续作为过渡期 read-only artifact viewer，
`apps/workbench` 用于后续正式的内容制作 / 记忆链路工作台。

浏览器只消费 Runtime Service 暴露的合同：`project_id`、`job_id`、safe
artifact ref、safe summary 和 `workbench-state`。前端不读取 CLI 内部实现，
不直接接触 provider 执行细节，不保存本地私有路径、signed URL 或媒体字节。

## 本地打开

先在另一个终端启动 Runtime Service：

```powershell
.\.venv\Scripts\python.exe -m apps.cli.main runtime-service --host 127.0.0.1 --port 8790
```

推荐通过 Runtime Service 打开：

```text
http://127.0.0.1:8790/workbench/
```

也可以直接打开静态文件用于隔离调试：

```text
apps/workbench/index.html
```

默认 Runtime Service 地址：

```text
http://127.0.0.1:8790
```

## 浏览器 QA

LibTV 添加节点/资源入口的点击态可以用本地 Playwright 脚本复核：

```powershell
.\.venv\Scripts\python.exe tools\workbench_libtv_add_node_browser_qa.py --base-url http://127.0.0.1:8790/workbench/
```

脚本默认会在 `desktop`、`tablet` 和 `mobile` 三个视口覆盖 `text`、`image`、`video`、`audio`、`script`、`director`、`video_merge`、`upload` 和 `history`；如需单独复核某个视口，可以追加 `--viewport mobile`。截图与结构化 manifest 会写入本地 ignored QA 输出目录。该 QA 只验证本地 UI、console、安全可见文本和 provider request 边界，不等于人工验收或真实 provider smoke。

TV 工具箱主体功能骨架可以用独立脚本复核：

```powershell
.\.venv\Scripts\python.exe tools\workbench_libtv_toolbox_browser_qa.py --base-url http://127.0.0.1:8790/workbench/
```

该脚本默认三视口检查 `TV工具箱`、6 个创作工具、4 个画布辅助、工具意图点击回执、可见文本安全边界和 provider request 边界。

Create 画布顶栏的项目名输入和画布选择器可以用独立脚本复核：

```powershell
.\.venv\Scripts\python.exe tools\workbench_libtv_canvas_header_browser_qa.py --base-url http://127.0.0.1:8790/workbench/
```

该脚本默认三视口检查项目名输入、画布菜单、`画布 2` 选择、`新建画布` 本地意图回执、可访问名称、安全可见文本和 provider request 边界。

Create 实际画布的执行链路骨架可以用独立脚本复核：

```powershell
.\.venv\Scripts\python.exe tools\workbench_libtv_execution_scaffold_browser_qa.py --base-url http://127.0.0.1:8790/workbench/
```

该脚本默认三视口检查 `节点连接`、`参数抽屉`、`待执行动作`、本地执行意图点击回执、可见文本安全边界和 provider request 边界。

## 当前职责

- 连接 Runtime Service。
- 由 Runtime Service 通过 `/workbench/` 提供静态入口，便于前后端联调和浏览器 QA。
- Runtime-hosted Workbench 静态资源使用 no-store，避免浏览器调试时复用旧模块。
- 读取 `/health`、`/capabilities`、`/projects` 和 `GET /projects/{project_id}/workbench-state`。
- 渲染中文项目工作台：项目、创作画布、素材库、分镜台、审片室、项目记忆、任务中心和诊断。
- 创建、打开、导入、导出 project manifest。
- 使用项目设置向导预填 project type、goal 和 safe manifest import JSON。
- 登记 safe asset/reference summary 和 safe scene/content card。
- 使用 source preset 预填内容需求、视觉参考和脚本提纲摘要。
- 从 safe source summaries 一键生成 Hook / Proof / CTA 首版创作画布草稿。
- 以产品面板展示 brief、reference、script 等 safe source summary，不展示本地素材位置或媒体字节。
- 按内容需求、视觉参考、脚本提纲和其他素材分组管理 safe source summary。
- 在右侧 Inspector 保存选中 scene/card 的 prompt、reference summary、style direction 和 retry intent。
- 通过分镜台查看镜头序列、当前镜头安全预览、引用/阻塞事实和审片入口。
- 通过审片室比较计划、首轮检查和下一轮候选，在候选卡上直接选择保留、修改或拒绝。
- 通过项目记忆查看已形成的风格偏好、profile version 数量、记忆证据和下一轮复用入口。
- 通过任务中心查看 runtime job 进度、阻塞指导和可打开的 safe artifact ref。
- 通过诊断查看当前 project 的运行活动、阻塞动作和可打开的 safe primary artifact ref。
- 通过任务中心统一查看 job queue、latest activity、provider preflight、provider controls 和 blocker counts。
- 通过创作画布统一查看主命令、素材参考、创作画布、检查器、分镜条、审片队列、风格记忆和 runtime 摘要。
- 通过创作画布查看本地执行链路骨架：节点连接、参数抽屉、待执行动作队列和本地执行意图回执。
- 通过制作流程查看 source、draft、first check、review、style memory、next round 和 provider gate 的一屏流程状态。
- 通过下一步操作查看当前主命令、阶段命令、所需输入和 provider gate 阻塞原因。
- 任务中心会对当前 project 做自动刷新，不启动 provider。
- 前端对 Runtime action/status/stage 做中文显示适配，内部 id 不直接变成用户操作语言。
- 触发首轮 deterministic asset test、记录 raw feedback、触发 two-round validation。
- 触发 provider preflight，但不启动 live provider。
- 读取 safe artifact，并渲染 artifact-specific report view，同时保留折叠的 JSON 详情。
- 默认隐藏 Advanced Diagnostics，把 evidence refs、non-claims 和 safe-ref policy 放到高级区。

## 工作区导航

左侧工作区把 Workbench 切成项目、创作画布、素材库、分镜台、审片室、项目记忆、任务中心和诊断。内部仍然兼容 Runtime Service 返回的 view id，但主界面显示中文产品语言，避免用户学习 `project_id`、`job_id`、`artifact_id` 等工程对象。

## 项目与就绪度

Workbench 从 `GET /projects/{project_id}/workbench-state` 读取 `project_hub` 和 `project_readiness`。项目页展示当前项目、计数、下一步、最近任务和 safe manifest artifact ref；就绪度面板只作为工作流提示，不执行 CLI、不绕过 provider gate、不把 feedback 晋升为 durable memory。

Projects 首页现在按创作门户组织：能力横幅、最近项目、开始创作入口和精选画布优先；项目就绪度、命令中心和制作流程状态不再默认压在首页上，避免把用户带回工程状态面板。

点击 Projects 门户的“全部项目”会切换到项目列表模式，用于集中查看和打开项目；该模式保留返回、开始创作、新建文件夹占位和项目卡片，不暴露 raw project id 作为主视觉信息。

精选画布支持进入案例详情页：详情页使用沉浸式成片预览、作者/标题/更新时间、观看入口、查看制作过程和底部案例切换；制作过程以只读弹层展示轻量节点画布、连线、缩放/小地图占位和节点安全摘要，复制入口只切回当前项目创作画布，不启动 provider。

Projects 左上角菜单打开全局工作台抽屉，用于承载账号席位、首页返回、模式切换、生成能力门和退出占位；当前版本只做导航与边界提示，不处理真实账号凭据。

精选画布筛选和搜索为前端内存态交互，用于快速定位案例；无匹配时显示空态，不请求后端、不启动生成能力。

Projects 的“开始创作”可以直接进入起步画布：画布中央显示故事脚本生成、角色三视图、首帧图生视频和音频生视频四个生产入口，并保留“实际画布”切换回 Runtime Service 投影。起步节点只做本地配置入口，不启动真实生成能力。

选择“故事脚本生成”后，Create 起步画布会进入脚本结果节点态：左侧展示剧本内容卡，右侧显示下游承接节点，中间保留可编辑提示，底部显示生成控制卡、`GVLM 3.1` 模型占位和 `Provider 未启动` 边界。该状态复刻 LibTV 的节点结果视图，但仍只使用本地安全示例内容，不调用真实模型。

选择“角色三视图”后，Create 起步画布会进入角色结果节点态：左侧展示角色图安全占位，右侧展示三视图安全占位，上方保留 `全景`、`多角度`、`打光`、`九宫格`、`高清`、`宫格切分` 能力条，中间显示“点击按钮，可替换上传你的角色图”提示，并明确标记 `生成器未启动` 与 `Provider Gate 未授权`。该状态只复刻 LibTV 的画布结构和操作入口，不复制真实站图片、不上传素材、不调用 provider。

选择“首帧图生视频”后，Create 起步画布会进入首帧视频结果节点态：左侧展示首帧安全占位，右侧展示视频安全占位，下方保留 `文生视频`、`全能参考`、`图生视频`、`首尾帧`、`图片参考` 模式入口，以及 `标记`、`运镜`、`角色库` 辅助工具、`Seedance 2.0 VIP` 和 `16:9 · 720P · 5s` 参数占位，并明确标记 `视频生成未启动`。该状态不上传图片、不读取本地素材、不启动视频 provider。

选择“音频生视频”后，Create 起步画布会进入音频驱动视频结果节点态：左侧展示音频安全占位、波形和 `00:00 / 00:03` 时长，右侧展示视频安全占位，下方保留 `文生视频`、`全能参考`、`图生视频`、`首尾帧`、`图片参考` 模式入口，以及 `标记`、`运镜`、`角色库`、`Seedance 2.0 VIP`、`16:9 · 720P · 5s`、`1个`、`135`、`联网搜索` 和 `自动校验素材` 控制占位，并明确标记 `音频驱动未启动`。该状态不上传音频、不读取本地素材、不启动视频 provider。

Create 起步画布的顶部栏按 LibTV 画布页组织：项目名输入只写入浏览器内存态，画布菜单显示 `画布 1`、`画布 2`、`审片画布` 和 `新建画布`，选择或新建只登记本地画布意图，不创建真实画布、不写项目文件、不启动 provider。底部工具坞按 LibTV 空画布方式组织：添加节点浮层显示文本、图片、视频、视频合成、导演台、音频、脚本，并在添加资源区提供上传和从生成历史选择入口；点击节点入口会进入本地安全节点态，展示节点摘要、控制卡、模式按钮和对应“未启动”边界。文本节点会进入 `文本节点 2` 控制面，保留自己编写内容、文生视频、图片反推提示词、文字生音乐、故事设定提示和 `GVLM 3.1` 占位；图片节点会进入本地图片控制面，保留上传摘要入口、图生图、图片高清、风格、标记、Lib Image、画质尺寸、摄像机/全景、张数和种子占位；视频节点会进入本地视频控制面，保留文生视频、全能参考、图生视频、首尾帧、图片参考、标记、运镜、角色库、Seedance 2.0 VIP、画幅/清晰度/时长、数量、种子和安全开关占位；音频节点会进入本地音频控制面，保留波形/时长、图片/视频目标、视频生成模式、运镜/角色库、Seedance 参数、联网搜索和自动校验素材占位；脚本节点会进入脚本生成器控制面，保留剧本生成分镜脚本、视频参考生成分镜脚本、角色生成分镜脚本、参考文本节点、文本/视频/提示词/音乐尝试和 `GVLM 3.1` 占位。导演台会进入本地 `3D导演台` 控制面，保留机位、场景对象、FOV、坐标、截图和 AI 识图导入入口；视频合成会进入安全时间线控制面，保留片段排序、转场、节奏和统一画幅入口。上传和生成历史入口会打开资源浮层：上传只登记安全摘要，不读取本地文件字节；历史选择只显示可复用记录投影，不拉取真实 provider 历史。资产管理是左侧抽屉，按项目输入、生成候选和记忆证据组织入口；历史资产按图片、视频和音频归档可复用记录；`TV工具箱` 提供多角度、运镜标记、首尾帧、图片高清、文字生音乐、角色库和画布辅助的主体功能骨架，点击创作工具只登记本地工具意图并显示回执；实际画布右侧提供节点连接、参数抽屉、待执行动作队列和本地执行意图回执，点击动作只更新浏览器内存态，不创建真实任务。帮助中心只保留必要操作边界。这里不展示 provider 配置、内部 job id 或本地文件路径，也不执行上传或真实生成。

## 创作画布与分镜台

Workbench 读取 `studio_workspace` 和 `creation_workspace`。创作画布承载主命令、素材参考、节点流、节点检查器、分镜条、审片队列、项目记忆和 runtime 摘要；分镜台使用独立工作区呈现镜头序列、当前镜头、安全预览、引用/阻塞事实和审片入口。

画布第一轮使用轻量节点流和内存态平移/缩放交互，不引入重型拖拽框架。节点只保留预览、标题和必要操作点，摘要、引用、阻塞项和产物入口下沉到按需浮层，避免主画布被标签和工程状态淹没。

## 素材库

Workbench 读取 `asset_library`，按 brief、reference、script 和其他素材分组展示 safe summary。浏览器不读取本地私有路径，也不保存媒体字节。

## 审片室与项目记忆

Workbench 读取 `review_room`、`style_memory` 和 `memory_workspace`。审片室专注候选队列、当前候选、对比点、审片决定和最近审片历史；项目记忆专注可复用偏好、profile version、记忆证据和下一轮复用入口。反馈仍然是 runtime evidence，不是 durable memory。

## 任务中心与诊断

Workbench 读取 `operations_workspace`、`activity_timeline` 和 `advanced_evidence`。任务中心展示 job queue、latest activity、provider preflight、provider controls 和 blocker counts；诊断区用于连接运行服务、查看内部引用和安全边界。它不会启动 live provider，也不会绕过 capability gate。

当前任务中心只通过 `render-operations-workspace.js` 渲染；旧 `render-jobs.js` 已删除，避免恢复英文 Job Center 面板和重复维护路径。审片与项目记忆也分别由 `render-review-workspace.js`、`render-style-memory-workspace.js` 承担，不再保留旧的混合记忆面板。

## 制作流程与下一步操作

Workbench 读取 `production_board` 和 `command_hub`。制作流程展示 source、draft、first check、review、style memory、next round 和 provider gate 的阶段状态；下一步操作把后端 action 映射成用户可理解的命令，禁用命令必须显示阻塞原因。

## 边界

- 浏览器状态只保存在内存中。
- 浏览器不调用 provider。
- 浏览器不执行 Python、CLI 或 workflow 内部函数。
- 浏览器不扫描目录。
- 浏览器不保存 secret、signed URL、本地私有素材或生成媒体字节。
- UI 不声明 human acceptance、business validation、production readiness 或 durable memory。
