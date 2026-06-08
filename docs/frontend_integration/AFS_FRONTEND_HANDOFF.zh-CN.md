# AFS 前端团队对接包

状态：Runtime Service v0.1 中文交接材料。

这份材料用于交给外部前端 / 画布工作台团队。它说明前端该接什么、不该接什么，以及第一阶段如何把 AFS 做成可操作的本地内容生产工作台。

## 一句话定位

AgentFlow Studio 不是传统 CMS，也不是单纯的生成器。当前可交付给前端的后端基线是：

```text
本地 Runtime Service
-> 项目 Manifest
-> Round 1 资产测试
-> 测试人员原始反馈
-> 候选更新 / 显式版本晋升
-> Round 2 上下文复用验证
-> Provider Gate 计划与安全状态
```

前端要做的是“操作员工作台”，不是在浏览器里重新实现 Python 后端、目录扫描器、Provider 调用器或记忆晋升器。

## 你应该交给前端团队什么

交付包建议包含这些文件和目录：

```text
docs/frontend_integration/AFS_FRONTEND_HANDOFF.zh-CN.md
docs/frontend_integration/AFS_FRONTEND_INTEGRATION_BRIEF.md
docs/frontend_integration/AFS_API_ADAPTER_PLAN.md
docs/frontend_integration/AFS_ARTIFACT_CONTRACT_MAP.md
docs/frontend_integration/AFS_UI_WORKBENCH_REQUIREMENTS.md
docs/handoff/AFS-RUNTIME-SERVICE-FRONTEND-INTEGRATION-001.md
examples/frontend_runtime_service/
apps/api/README.md
```

前端团队只需要把它们当成第一版接口说明、UI 信息架构和请求样例。后端源代码可作为参考，但不要求前端团队理解 CLI 内部实现。

## 本地服务启动

在 AFS 仓库根目录启动：

```powershell
.\.venv\Scripts\python.exe -m apps.cli.main runtime-service --host 127.0.0.1 --port 8790
```

默认服务地址：

```text
http://127.0.0.1:8790
```

OpenAPI：

```text
http://127.0.0.1:8790/docs
http://127.0.0.1:8790/openapi.json
```

## 当前后端可对接能力

| 接口 | 状态 | 前端用途 |
|---|---|---|
| `GET /health` | 已实现 | 服务是否就绪 |
| `GET /capabilities` | 已实现 | 展示当前可用动作、禁用动作和边界 |
| `POST /projects` | 已实现 | 创建本地项目 Manifest |
| `GET /projects/{project_id}/manifest` | 已实现 | 读取项目工作台入口对象 |
| `GET /artifacts/{artifact_id}` | 已实现 | 读取安全 artifact 内容 |
| `GET /runs/{job_id}` | 已实现 | 查询 run/job 状态 |
| `POST /runs/asset-test` | 已实现 | 发起 Round 1 deterministic asset loop |
| `POST /runs/two-round-validate` | 已实现 | 发起 Round 2 context runtime validation |
| `POST /feedback` | 已实现 | 记录测试人员原始反馈证据 |
| `POST /provider/validation-plan` | 已实现 | 生成 Provider Gate 的计划 / blocked evidence |
| 真实 provider 执行接口 | 未开放 | 等 deterministic 本地闭环稳定后再做 |

## 前端必须遵守的核心规则

前端只保存和传递：

```text
project_id
job_id
artifact_id
status
safe summary
safe manifest
```

前端不要直接依赖：

```text
本地私有素材路径
provider config 路径
signed URL
API key / cookie / token
provider 原始响应体
媒体字节
浏览器本地缓存作为事实来源
```

如果后端返回了 `artifact_id`，前端应该通过 `GET /artifacts/{artifact_id}` 读取，而不是猜测文件路径。

## 第一阶段 UI 节点

建议画布 / 工作台先做这些节点：

```text
Project
Source Assets
Asset Test Run
Feedback
Profile Candidate
Profile Version
Context Projection
Round 2 Validation
Provider Gate
```

节点之间的连线表达 artifact / job 关系，不表达“已经人工通过”或“已经商业验证”。

## 第一阶段页面

建议前端第一版至少包含：

| 页面 | 必须回答的问题 |
|---|---|
| Project Overview | 这个项目是什么、目标是什么、状态是什么 |
| Run Timeline | 当前有哪些 run，每个 run 的状态和输出是什么 |
| Asset Review | 当前测哪个人物 / 场景 / profile version，哪些 refs included / blocked |
| Feedback Panel | 测试人员反馈是 kept / partial / failed / unknown 中哪一种 |
| Context Runtime Report | Round 2 引入了哪些上下文，是否改善，为什么 |
| Provider Gate | 当前 provider 是 blocked / ready / succeeded，阻塞原因是什么 |

## 禁止前端声明的结果

前端可以显示：

```text
Runtime service produced a report.
This profile version is included in context.
This ref is blocked with a reason.
Provider gate is ready / blocked / succeeded according to safe manifest.
```

前端不能显示为事实：

```text
内容已经人工验收通过。
商业效果已经验证。
候选记忆已经成为公司长期记忆。
Provider 输出已经生产可用。
```

这些结论必须由人工验收、商业验证或 COS 规则晋升流程单独确认。

## 请求样例

请求样例在：

```text
examples/frontend_runtime_service/
```

建议前端团队先用这些样例调通：

```text
create_project.request.example.json
asset_test_run.request.example.json
feedback_record.request.example.json
two_round_validate.request.example.json
provider_validation_plan.request.example.json
```

## 第一阶段验收

前端第一版可以认为对接完成，当它能做到：

1. 启动本地 Runtime Service 后，显示服务 ready。
2. 创建或打开一个 project manifest。
3. 发起 Round 1 asset test run，并显示报告 artifact。
4. 记录一条 raw tester feedback。
5. 发起 Round 2 validation，并展示 included refs / blocked refs / improvement assessment。
6. 展示 Provider Gate 的 blocked 或 ready 状态。
7. 所有 artifact 读取都通过后端 `artifact_id`，不直接读取私有路径。
8. UI 中明确区分 runtime verification、human acceptance、business validation 和 durable memory。

## 目前不要做

这些不是第一阶段目标：

- 不做 SaaS。
- 不做账号系统。
- 不做数据库。
- 不做云同步。
- 不做浏览器侧目录扫描。
- 不把 provider secret 交给前端。
- 不让前端直接调用 Kling、gpt-image、OpenAI、Minimax 等 provider。
- 不让前端决定 memory promotion。

## 推荐沟通方式

你可以对前端团队这样讲：

> 你们只需要把 AFS 当成一个本地 API 服务来接。前端负责画布、节点、状态展示和操作体验；后端负责 deterministic run、artifact、feedback、profile version、context projection 和 provider gate。第一阶段不接 SaaS，不碰 secret，不直接扫本地素材，不做自动记忆晋升。
