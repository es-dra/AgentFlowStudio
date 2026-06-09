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
- 读取 `/health`、`/capabilities`、`/projects` 和 `GET /projects/{project_id}/workbench-state`。
- 渲染项目工作台、Production Board、Reference Library、创作画布卡片、检查区、Review Room、Style Memory、Job Center、provider preflight 和 filmstrip。
- 创建、打开、导入、导出 project manifest。
- 使用 Project Hub 模板预填 project type、goal 和 safe manifest import JSON。
- 登记 safe asset/reference summary 和 safe scene/content card。
- 使用 source preset 预填 brief、reference、script outline 摘要。
- 从 safe source summaries 一键生成 Hook / Proof / CTA 首版创作画布草稿。
- 以产品面板展示 brief、reference、script 等 safe source summary，不展示本地素材位置或媒体字节。
- 在右侧 Inspector 保存选中 scene/card 的 prompt、reference summary、style direction 和 retry intent。
- 通过 Review Room 比较计划、首轮检查和下一轮候选，再记录 keep / revise / reject 决策。
- 通过 Style Memory 查看已形成的风格偏好、profile version 数量和下一轮复用提示。
- 通过 Job Center 查看 runtime job 进度、阻塞指导和可打开的 safe artifact ref。
- 通过 Activity Timeline 查看当前 project 的运行活动、阻塞动作和可打开的 safe primary artifact ref。
- 通过 Production Board 查看 source、draft、first check、review、style memory、next round 和 provider gate 的一屏流程状态。
- Job Center 会对当前 project 做自动刷新，不启动 provider。
- 触发首轮 deterministic asset test、记录 raw feedback、触发 two-round validation。
- 触发 provider preflight，但不启动 live provider。
- 读取 safe artifact，并渲染 artifact-specific report view，同时保留折叠的 JSON Detail。
- 默认隐藏 Advanced Diagnostics，把 evidence refs、non-claims 和 safe-ref policy 放到高级区。

## Stage Navigation

The rail items switch the Workbench between Projects, Create, Assets, Review,
Style Memory, Jobs, and Settings. Each view renders a narrower control group so
users do not have to learn every internal workflow surface at once.

## Project Readiness

The Workbench reads `project_readiness` from `GET /projects/{project_id}/workbench-state`.
It renders a compact Project Readiness panel with the current action, safe workflow
gates, and non-claim badges. This panel is a user-facing workflow guide only: it
does not execute CLI internals, does not bypass provider gates, and does not
promote feedback into durable memory.

## Activity Timeline

The Workbench reads `activity_timeline` from `GET /projects/{project_id}/workbench-state`.
It renders project runtime activity as a product-facing history: status counts,
latest actions, blockers, and safe primary artifact refs. It is trace navigation,
not approval logic.

## Production Board

The Workbench reads `production_board` from `GET /projects/{project_id}/workbench-state`.
It renders the whole content and memory flow as product-facing lanes: source,
draft, first check, review, style memory, next round, and provider gate. The
board is a workflow surface, not a provider execution path.

## 边界

- 浏览器状态只保存在内存中。
- 浏览器不调用 provider。
- 浏览器不执行 Python、CLI 或 workflow 内部函数。
- 浏览器不扫描目录。
- 浏览器不保存 secret、signed URL、本地私有素材或生成媒体字节。
- UI 不声明 human acceptance、business validation、production readiness 或 durable memory。
