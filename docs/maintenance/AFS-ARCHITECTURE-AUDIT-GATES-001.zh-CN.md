# AFS 架构审计门禁 001

状态：已实现本地测试门禁。

日期：2026-06-08

## 目标

把深度瘦身审查中的关键结论固化为自动化测试，防止后续开发继续扩大架构债。

本轮不重构业务代码，不删除 provider 或 Web 过渡路径，只先建立护栏。

## 新增门禁

新增测试文件：

```text
tests/test_architecture_audit_gates.py
```

覆盖 6 类风险：

1. Runtime Service 不能依赖 CLI 或旧 Web bridge。
2. `apps` 层不能再从 `agentflow_studio.utils` 获取通用 JSON helper。
3. `agentflow` 核心层不能反向依赖 `agentflow_studio`。
4. 包级循环依赖的现有债务被冻结，只允许减少，不允许新增。
5. hidden CLI command surface 的现有债务被冻结，只允许减少，不允许新增。
6. 不允许新增编号式 `memory_advantage_demo_XXX` 源码模块。

## 当前冻结的已知债务

### 核心层反向依赖

当前允许的旧债已经清空。

`agentflow.memory.*` 对 `agentflow_studio.utils.write_json` 的旧依赖已迁移到 `agentflow.harness.json_io`；`agentflow.memory.production_asset_profile_provider` 对 `agentflow_studio.model_gateway` 的旧依赖已改为注入式 provider executor。后续重点转为拆分 `model_gateway` 内部 plan、transport、poll/recovery 和 safe report。

### 包级循环依赖

当前仅允许 2 组旧债：

```text
agentflow_studio.harness <-> agentflow_studio.workflow_engine
agentflow_studio.model_gateway <-> agentflow_studio.production
```

新增循环依赖会使测试失败。

### Hidden CLI

hidden CLI 仍保留 Production Memory 旧长命令、provider smoke 和编号 demo 入口。后续可以删除，但不能无记录新增。

## 后续减少路径

1. `WorkflowRunner` 不再从 `agentflow_studio.harness` 聚合入口导入，改为窄函数或 adapter。
2. `model_gateway` 与 `production.posterflow` 通过 provider interface 解耦。
3. provider smoke 内部继续拆为 plan、transport、poll/recovery、safe report。
4. 编号 demo 的 live evidence 迁移到 protocol-driven runner 后，删除 hidden demo commands 和 bespoke modules。

## 已减少的债务

- `apps/cli/command_registry.py` 不再顶层 import `apps.web_bridge.server`；`web-bridge` 命令改为执行时 lazy import。这样保留旧命令可用性，同时减少 CLI 默认加载时对旧 bridge 的静态依赖。
- `apps.reporting.run_reports` 已接管 inspect/review/package/delivery report helper；`apps.web_bridge` 不再 import `apps.cli.report_commands`，`apps.cli <-> apps.web_bridge` 包级循环依赖已清除。
- `agentflow.harness.json_io` 已接管通用 `write_json` helper；`agentflow.memory` 下 44 个模块已从 `agentflow_studio.utils` 迁移到平台 harness helper。
- `apps/api` 与 `apps/cli` 下 5 个 JSON 写入调用已从 `agentflow_studio.utils` 迁移到 `agentflow.harness.json_io`，并增加门禁防止 API/CLI 再使用 Studio utils 承担通用 IO。
- `agentflow.memory.production_asset_profile_provider` 已改为注入式 `ProviderValidationExecutor`；真实 MiniMax/Kling 调用移动到 `agentflow_studio.model_gateway.asset_profile_provider_adapter`。CLI live provider path 在显式 `--run-provider-validation` 时才注入 Studio adapter；Runtime Service 当前仍只输出 provider validation plan，不启动 live provider。

## 验证

已运行：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_architecture_audit_gates.py -q
```

结果：

```text
6 passed
```

## 非声明边界

- 这是结构门禁，不是业务功能完成声明。
- 这是工程维护验证，不是 human acceptance。
- 没有调用 provider。
- 没有写入 `10-Startup`。
- 没有声明 durable memory 或 business validation。
