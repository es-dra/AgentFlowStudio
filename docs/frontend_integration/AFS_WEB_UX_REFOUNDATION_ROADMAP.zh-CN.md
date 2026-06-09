# AFS Web Workbench UX Refoundation Roadmap

状态：长期前端开发主线规划；阶段 0-7 已形成发布候选

日期：2026-06-09

当前分支：`codex/afs-landing-prep-web-plan-001`

任务定位：把现有 Workbench 从工程状态面板升级为可操作的中文工业化创作工作台。

## 一句话定位

AFS Web Workbench 不是 Runtime Service 的调试页，也不是把所有工程对象摊在一个大窗口里的状态看板。它应该是一个面向内容制作与记忆链路的 Agent-native 创作工作台：用户以项目为入口，在画布、分镜、审片、项目记忆、任务中心之间自然切换；系统在后台保持 Runtime Service、Project Manifest、Provider Gate、artifact viewer 和 maintenance audit 的工程边界。

## 当前判断

当前 `/workbench/` 已经具备多块后端安全投影和前端模块，包括 Project Hub、Studio Workspace、Creation Workspace、Production Board、Review/Memory、Operations、Job Center、Command Hub、Activity Timeline 等。问题不在于模块数量不够，而在于产品体验仍然偏工程拼装：

- 首屏仍然让用户感知过多 Runtime、job、artifact、provider 等内部概念。
- 画布、分镜、审片、记忆、任务中心之间缺少清晰的窗口切换和任务动线。
- 用户从“创建项目”到“完成一轮内容制作与记忆复用”的路径没有形成接近参考画布工具的低学习成本体验。
- 诊断信息和安全边界是必要的，但不应该压过创作主界面。
- 现有模块拆分是可维护性的基础，下一阶段重点是重新编排信息架构、交互模型和验收闭环。

## 目标

1. 形成完整中文 Web 工作台，而不是单屏信息堆叠。
2. 支持从项目创建、素材/参考录入、画布规划、分镜/内容制作、审片反馈、项目记忆沉淀、下一轮复用、Provider Gate 预检到任务追踪的确定性闭环。
3. 让用户主要看到“项目、画布、素材、分镜、审片、记忆、任务”，而不是默认看到 `project_id`、`job_id`、`artifact_id`。
4. 后端继续通过 Runtime Service 暴露 safe projection；前端不绕过 API 直接接 CLI、路径、provider 配置或私有素材。
5. 每个阶段都通过浏览器操作、focused pytest、静态检查和项目记录进行自监督。

## 非目标

- 不在浏览器里重写 Python 编排、provider adapter 或记忆晋升逻辑。
- 不接入真实 provider，除非后续单独授权对应 capability gate。
- 不引入账号体系、多人协作、云端同步、商业看板或 SaaS 权限模型。
- 不把 COS active rule、商业判断、secret、signed URL、provider 原始响应、私有素材路径或媒体字节写入仓库。
- 不为了追求视觉效果牺牲 Runtime Service、Project Manifest、Provider Gate、read-only artifact viewer 和 maintenance audit 主线。

## 总体交付节奏

本路线图按 8 个阶段推进。每个阶段都应该形成可运行、可截图、可测试、可回滚的小版本，而不是长时间堆积未验证改动。

| 阶段 | 主题 | 主要产出 | 验收门槛 |
|---|---|---|---|
| 0 | 基线与产品语言冻结 | 中文 IA、术语表、UX 门禁、QA 账本 | 文档落地，provider 仍关闭，分支干净 |
| 1 | 应用外壳与窗口模型 | 左侧工作区导航、顶部项目栏、窗口/抽屉/对话框状态 | 用户不再面对单页堆叠 |
| 2 | 项目入口与创建向导 | 项目首页、创建向导、模板入口、示例项目加载 | 从空状态能进入可操作项目 |
| 3 | 创作画布重构 | 可操作画布、节点/卡片、右侧检查器、底部命令栏 | 画布成为主工作区 |
| 4 | 分镜与素材工作流 | 素材库、参考入口、分镜台、镜头卡、filmstrip/timeline | 内容制作路径可视化 |
| 5 | 审片室与项目记忆 | 审片对比、保留/修改/拒绝、候选记忆、版本化风格约束 | 反馈能进入下一轮复用 |
| 6 | 任务中心与 Provider Gate | 任务队列、阻塞原因、Provider 预检、安全状态 | 用户能理解能否进入真实模型 |
| 7 | 全链路 QA 与发布候选 | 浏览器脚本、响应式检查、完整测试、维护审计、发布记录 | 可交付给人工验收 |

## 阶段 0：基线与产品语言冻结

目标：先把“要做成什么”钉住，防止继续向工程调试页堆功能。

动作：

- 新增或更新前端规划、QA 账本、中文术语表。
- 固定一级工作区：`项目`、`创作画布`、`素材库`、`分镜台`、`审片室`、`项目记忆`、`任务中心`、`诊断`。
- 固定技术对象的展示规则：`project_id`、`job_id`、`artifact_id` 默认只出现在诊断或详情抽屉。
- 固定安全边界：前端只接 safe manifest、safe summary、safe artifact ref、OpenAPI。
- 明确每个窗口的空态、加载态、错误态、成功态和禁用态。

验收：

- `docs/frontend_integration/` 有可执行路线图。
- `DEVLOG.md` 记录本轮规划。
- `git status --short --branch` 能清楚反映只发生计划性文档变更。

## 阶段 1：应用外壳与窗口模型

目标：把工作台从“一个大页面”改成真正的多窗口创作应用。

动作：

- 重构首屏为三层结构：顶部项目栏、左侧工作区导航、中间活动窗口。
- 右侧统一为检查器/详情抽屉，不再在主画布里堆所有说明。
- 底部统一为命令栏或阶段性操作区，承载“下一步”而不是散落按钮。
- Runtime 连接状态降级为顶部小状态，不再作为首屏主角。
- 所有主导航、按钮、错误信息、空态文案中文化。

验收：

- 用户打开 `/workbench/` 后第一眼看到项目与创作入口，而不是工程调试入口。
- 一级窗口可以切换，切换不丢状态。
- 浏览器 console error 为 0。
- 基础静态测试和 Web focused tests 通过。

## 阶段 2：项目入口与创建向导

目标：让用户从空状态自然开始，而不是手动理解 API 或填内部字段。

动作：

- 项目首页显示最近项目、项目阶段、下一步、主要产物。
- 创建向导拆为：项目目标、内容类型、参考素材、风格/记忆约束、确认创建。
- 示例/模板作为入口，但不能伪装成已验证业务成果。
- 导入/导出只处理安全 manifest 或示例配置。

后端协同：

- 如果现有 `project_hub` 不足，新增产品化 safe projection，不让前端推断项目阶段。
- 保持 Project Manifest contract 作为唯一项目事实入口。

验收：

- 空项目能通过 UI 创建。
- 用户不需要手写 JSON 即可进入工作台。
- 创建过程不暴露私有路径、provider 配置或 secret。

## 阶段 3：创作画布重构

目标：吸收参考画布工具的低学习成本体验，让画布成为主工作区。

动作：

- 将画布节点改为用户语言：`需求`、`素材`、`脚本`、`分镜`、`镜头`、`审片`、`记忆`、`Provider 预检`。
- 节点卡显示状态、主要摘要、下一步，不默认显示内部 id。
- 右侧检查器显示选中节点的证据、阻塞原因、相关 artifact ref 和可执行动作。
- 底部命令栏显示当前阶段最自然的一到三个动作。
- 保留诊断模式，用于查看 `job_id`、`artifact_id`、raw blocker 和 API 返回摘要。

技术路线：

- 第一轮继续沿用当前轻量 JS 模块，优先完成产品动线。
- 当节点拖拽、连线、缩放、复杂布局成为真实需求后，再评估 React Flow。
- 不默认采用 tldraw，除非自由绘制、多媒体标注和白板协作成为主需求；同时需处理许可与集成边界。

验收：

- 用户能从画布理解当前项目处于哪一步。
- 选中节点后，检查器内容和可执行动作同步变化。
- 画布在 1366x768 与 1440x900 下不重叠、不溢出。

## 阶段 4：分镜与素材工作流

目标：让内容制作链路具备接近工业工具的操作感。

动作：

- 素材库区分：来源摘要、参考图/文本、风格锚点、被阻塞素材。
- 分镜台以镜头卡和横向 filmstrip 呈现，不把所有信息塞进表格。
- 镜头卡支持选中、查看证据、标记需要修改、进入审片。
- 如果当前只是 safe artifact，没有媒体字节，界面必须明确显示为安全预览或占位，不伪装成真实成片。

后端协同：

- 必要时为 `creation_workspace` 增加 storyboard-safe projection。
- 前端只根据 safe ref 拉 artifact，不推断本地文件。

验收：

- 从素材到分镜的路径可被浏览器脚本点击完成。
- 用户能知道哪些素材可用、哪些被阻塞、为什么阻塞。

## 阶段 5：审片室与项目记忆

目标：把“反馈 -> 候选记忆 -> 下一轮复用”做成产品主能力。

动作：

- 审片室支持候选对比、保留、修改、拒绝、备注。
- 项目记忆区必须区分：原始反馈、候选记忆、profile version、durable memory。
- 下一轮复用必须显示“将带入哪些约束、哪些不会带入、哪些仍需人工确认”。
- 所有记忆相关 UI 避免暗示已经写入 COS durable memory，除非后端 contract 明确声明。

验收：

- 用户能在 UI 中完成一次 review decision。
- 下一轮准备状态能解释它复用了什么、没复用什么。
- 记忆状态不会越权宣称 human acceptance、business validation 或 durable memory。

## 阶段 6：任务中心与 Provider Gate

目标：让用户能判断“当前为什么不能进入真实模型，什么时候可以进入”。

动作：

- 任务中心展示队列、运行中、已完成、阻塞、失败和可重试任务。
- Provider Gate 只显示 capability、gate 状态、阻塞项、预检结果和 redacted metadata。
- 真实 provider 调用保持关闭；UI 只能做预检和授权提示。
- 诊断窗口保留完整 API/状态排查入口，但不打扰主工作流。

验收：

- Provider Gate 能明确显示 `blocked`、`ready_not_run`、`ready` 等状态。
- 用户不会误以为预检等于真实模型验证。
- 前端代码中没有 secret、signed URL、provider raw response 或媒体字节落盘。

## 阶段 7：全链路 QA 与发布候选

目标：把 Web 工作台推进到可人工验收的 release candidate。

浏览器验收路径：

1. 打开 `/workbench/`。
2. 创建项目。
3. 添加安全素材/参考摘要。
4. 生成或加载画布草稿。
5. 进入分镜台查看镜头卡。
6. 进入审片室做一次 keep/revise/reject。
7. 查看项目记忆候选和下一轮复用状态。
8. 打开任务中心查看 job 与 blocker。
9. 打开 Provider Gate 预检，确认没有真实 provider 调用。
10. 打开诊断窗口查看内部 id 与 artifact ref。

自动与手动检查：

- Playwright 或浏览器自动化覆盖主路径，保存截图到忽略目录。
- 控制台错误为 0。
- 主要视口：1440x900、1366x768、390x844；桌面为主，移动端不要求完整操作能力，但不能严重错位。
- 文字不能溢出按钮、卡片、侧栏或抽屉。
- 所有空态、错误态、加载态、禁用态有中文文案。

验证命令：

```powershell
.\.venv\Scripts\python.exe -m apps.cli.main --help
.\.venv\Scripts\python.exe -m apps.cli.main version
.\.venv\Scripts\python.exe tools\maintenance_audit.py
.\.venv\Scripts\python.exe -m pytest tests\test_api_runtime_service_v02.py tests\test_api_runtime_workbench_state.py tests\test_web_workbench_foundation.py -q
.\.venv\Scripts\python.exe -m pytest
git diff --check
```

如引入新的前端构建链，再追加对应 JS/TS lint、typecheck、build 和 browser smoke。

## 自监督机制

每个阶段按同一套检查执行：

- 进入阶段前确认 `git status --short --branch`，不覆盖无关改动。
- 阶段内只做一个产品目标，避免继续堆叠无关面板。
- 每次新增 UI 模块，检查文件长度；超过 300 行优先拆分，超过 500 行必须有拆分或保留理由。
- 每个用户动作都必须有成功、失败、阻塞、禁用状态。
- 每个主窗口都必须能解释：当前是什么、下一步是什么、为什么不能做、产物在哪里。
- 每个后端新增字段都必须是 safe projection，不让前端接触 CLI 内部、私有路径或 provider 原始信息。
- 每阶段至少跑 focused tests；重大阶段跑全量 pytest、maintenance audit 和 diff check。
- 每阶段更新 `DEVLOG.md` 或对应 handoff/QA 文档，记录边界、验证和残留风险。

## 提交与合并节奏

建议按垂直切片提交：

1. `docs(frontend): plan workbench ux refoundation`
2. `feat(workbench): add Chinese app shell navigation`
3. `feat(workbench): add project creation wizard`
4. `feat(workbench): refactor creation canvas workflow`
5. `feat(workbench): add storyboard and review room flow`
6. `feat(workbench): surface project memory reuse`
7. `feat(workbench): add task center provider gate diagnostics`
8. `test(workbench): add browser release candidate checks`

合并回 `master` 前必须完成：

- 浏览器主路径证据。
- focused Web/API tests。
- 全量 pytest。
- maintenance audit。
- `git diff --check`。
- 人工验收结论与 provider gate 边界记录。

## 当前下一步

阶段 0-7 已落地到当前分支：中文 IA / 术语 / QA 账本、多工作区外壳、项目入口、创作画布、素材库、分镜台、审片室、项目记忆、任务中心、Provider Gate、浏览器主路径、响应式截图和发布候选证据已经形成可人工验收的 Runtime Service 工作台切片。

发布候选主路径已经跑通：

1. `/workbench/` 连接 Runtime Service。
2. 从项目列表打开 QA 项目。
3. 素材库登记安全素材摘要。
4. 生成画布草稿并进入创作画布。
5. 进入分镜台查看镜头序列。
6. 进入审片室记录审片决定。
7. 执行首轮素材检查、记录反馈、执行下一轮验证。
8. 查看项目记忆复用状态。
9. 进入任务中心和 Provider 预检。
10. 打开设置/诊断确认内部定位信息只在诊断层出现。

下一阶段不再继续堆 Workbench 静态界面，而是按落地前顺序推进：

1. 由人工验收当前 Web release candidate，确认信息架构、窗口切换、中文操作语言和主路径体验是否可接受。
2. 修复验收中出现的交互问题，优先处理输入、导航、空态、阻塞解释、响应式错位和中文化遗漏。
3. 在仍不打开 provider 的前提下，补一轮后端协同检查：Runtime Service safe projection 是否足够支持真实内容制作 / 记忆链路。
4. 只有在人为确认 Web 主路径可用后，再进入 capability-gated provider smoke；provider smoke 必须单独记录授权、能力边界、输入输出摘要和残留风险。
5. provider smoke 通过后，才进入前后端初步落地收尾：提交、合并、推送、清理临时分支，并给出 human acceptance / provider validation / durable memory 的明确边界。

这一轮不接真实 provider，不扩大后端职责，不恢复旧 demo 或旧 Web surface。
