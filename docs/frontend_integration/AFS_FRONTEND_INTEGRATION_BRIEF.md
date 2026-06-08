# AFS 前端集成 Brief

状态：交给画布/工作台前端团队的 handoff brief。

## 产品定位

AgentFlow Studio 是 agent-native content production workbench。当前后端不是 SaaS backend，而是本地 Runtime Service，包住 deterministic AFS core：

```text
Project Manifest
-> Round 1 asset test run
-> raw tester feedback
-> candidate / explicit profile promotion
-> profile version
-> Round 2 context runtime validation
-> optional provider validation plan
```

前端应被设计为 operator workbench，用于跑、看、反馈、复用这条 evidence loop。

前端不应该：

- 执行 Python；
- 扫描本地文件夹；
- 保存 provider secret；
- 自己推断 memory promotion。

## 对接目标

前端只对接：

```text
AFS Runtime Service v0.1
```

默认本地 URL：

```text
http://127.0.0.1:8790
```

启动方式：

```powershell
.\.venv\Scripts\python.exe -m apps.cli.main runtime-service --host 127.0.0.1 --port 8790
```

## 当前后端能力

| Surface | 状态 | 前端用途 |
|---|---|---|
| `/health` | implemented | service readiness |
| `/capabilities` | implemented | action/status discovery |
| `/projects` | implemented | 创建本地 project manifest |
| `/projects/{project_id}/manifest` | implemented | project workbench entrypoint |
| `/artifacts/{artifact_id}` | implemented | safe artifact read |
| `/runs/asset-test` | implemented | 运行 Round 1 deterministic asset loop |
| `/runs/two-round-validate` | implemented | 运行 Round 2 context validation |
| `/feedback` | implemented | 记录 raw feedback evidence |
| `/provider/validation-plan` | implemented | 生成 provider readiness/blocker evidence |
| live provider execution endpoint | not exposed | deterministic loop 通过后再打开 |

## 前端心智模型

Canvas nodes 表示 backend action 和 artifact state：

```text
Project
-> Source Assets
-> Asset Test Run
-> Feedback
-> Profile Candidate
-> Profile Version
-> Context Projection
-> Round 2 Validation
-> Provider Gate
```

边只指向 `artifact_id` 和 status，不指向本地文件路径。

## 硬边界

- 不从 manifest refs 直接读取本地文件。
- 不把 browser state 当作 source of truth。
- 不显示 private local paths、provider config paths、signed URLs、API keys、cookies、media bytes、provider response bodies。
- 不把 raw feedback 标记为 memory。
- 不把 profile candidate 标记为 durable memory。
- 不把 runtime success 当作 human acceptance。
- 不把 provider smoke 当作 business validation。

## 前端允许声明什么

允许：

- “Runtime Service produced a Round 1 report.”
- “This profile version is included in Round 2 context.”
- “This ref is blocked with a reason.”
- “Provider validation is blocked/ready/succeeded according to safe manifest.”

禁止：

- “The content is approved.”
- “The business result is validated.”
- “The memory is durable company memory.”
- “The provider output is production-ready.”

## 第一个前端里程碑

构建本地项目工作台，至少支持：

1. 创建或打开 project manifest。
2. 从表单启动 Round 1 asset test run。
3. 渲染返回的 `real_asset_test_report`。
4. 记录 raw tester feedback。
5. 从 Round 1 job 启动 Round 2 validation。
6. 渲染 included refs、blocked refs、improvement assessment。
7. 渲染 provider readiness / blocker state。

第一版保持 local-only、single-user。
