# AFS ModelCallContext 生产闭环试航项目书包 v0.1

日期：2026-07-08，Asia/Shanghai

项目编号：`AFS-PROGRAM-MCC-PROD-LOOP-20260708`

## 目标契约

本轮试航要把 AFS 下一阶段推进从“文档控制”拉回真实产品闭环：

```text
Studio 用户操作
-> Runtime 安全上下文装配
-> ModelCallContext
-> 提示词优化 / 请求投影
-> safe manifest 与 artifact refs
-> Studio 证据状态
-> 测试、评审、集成队列
```

目标不是最小演示，而是一套可逐步扩大的 AFS 智能生产架构。第一段切片必须是真实代码，必须跨 Runtime / Studio 边界，必须留下机器可验证证据。

## 启动基线

第一段切片启动前的基线如下：

- 起点栈：`codex/program-runtime-status-badge-20260708`。
- 试航分支：`codex/program-mcc-production-loop-20260708`。
- 本地工作区：启动时干净。
- PR #106：draft，可合并，维护 CI 通过。
- PR #107：draft，堆叠在 #106 上，可合并，维护 CI 通过。
- PR #108：`zhaowei` 审计 PR，存在冲突，不作为本轮集成目标。
- 服务器 Runtime：仅 `127.0.0.1:8790` 监听。
- Runtime 健康：ready，auth required，local only。
- provider gates：`llm=false`，`image=false`，`video=false`，`vision=false`，`asr=false`，`external_download=false`。

## 执行泳道

泳道 1：Runtime 契约加固

- 为 prompt optimization 增加公开的 `model_call_context_summary`。
- 完整 `model_call_context.json` 仍只作为 artifact 保存。
- 对公开 summary 使用白名单字段，不暴露完整内部上下文。

泳道 2：Studio 证据状态

- 在 Studio 侧归一化 `model_call_context_summary`。
- 在节点上保留最近一次 context id 和安全 summary。
- 如果 Runtime 返回 context bundle，prompt optimization 后同步保留到节点状态。

泳道 3：验证

- Runtime 契约测试：summary 与 artifact id、context id 对齐。
- Studio Node 脚本测试：优化完成后保留 context id、summary 和 context bundle。
- Studio JS 语法检查。
- PR 前执行更宽的 API / Studio 聚焦测试。

泳道 4：架构试航复盘

- 记录从分支创建到第一轮绿色证据的耗时。
- 记录跨层触达文件数量。
- 记录当前架构暴露的问题。
- 判断 Program Mode 启动包是否足以承接下一轮更大的 AFS 任务。

## 验收门禁

第一段切片只有满足以下条件才能进入集成队列：

- Runtime 同时返回 `model_call_context_id` 和 `model_call_context_summary`。
- summary 包含 artifact ref 与安全计数，不携带完整内部上下文。
- Studio 保留 summary，但不吞入完整 trace、provider raw 或内部治理字段。
- 聚焦测试通过。
- 不打开任何 provider gate。
- 不声称 provider QA、generated-media QA、human acceptance、public readiness、business acceptance 或 legal acceptance。

## 非声明边界

本项目书包不声明：

- provider 真实执行；
- 生成媒体质量；
- 服务器公网就绪；
- 服务器已加载当前分支代码；
- Owner 或人工验收；
- 商业、法律或公开发布验收。

## 集成队列

1. 完成第一段跨层切片。
2. 运行聚焦测试和 Studio JS 检查。
3. 如响应契约变化，刷新并验证 OpenAPI snapshot。
4. 运行更宽的 Studio / API 聚焦测试。
5. 在状态文件记录效率和架构问题。
6. 验证通过后提交、推送并打开堆叠 draft PR。
7. 集成前对公开 summary 边界做 evaluator review。
