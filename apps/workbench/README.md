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

## 创作画布与分镜台

Workbench 读取 `studio_workspace` 和 `creation_workspace`。创作画布承载主命令、素材参考、节点流、节点检查器、分镜条、审片队列、项目记忆和 runtime 摘要；分镜台使用独立工作区呈现镜头序列、当前镜头、安全预览、引用/阻塞事实和审片入口。

画布第一轮使用轻量节点流，不引入拖拽框架。节点展示状态、摘要、引用数、阻塞项和产物入口；右侧检查器展示安全引用、阻塞、动作和可编辑的提示词/风格摘要。

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
