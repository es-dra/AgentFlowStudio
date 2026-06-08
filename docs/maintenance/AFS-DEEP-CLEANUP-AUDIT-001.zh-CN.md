# AFS 深度瘦身审查 001

状态：已执行低风险删除，保留高风险候选。

日期：2026-06-08

## 目标

本轮不是继续扩大功能，而是从全栈工程维护角度重新审查目录、调用关系、入口、文档和历史证据，判断哪些内容应删除、收口或暂缓。

## 审查结论

AFS 当前主要问题不是单点代码不可用，而是历史验证路径、过渡前端、CLI 支持入口、provider smoke、Production Memory contract 同时留在主线，导致维护成本偏高。

应优先处理以下结构债：

1. 核心层反向依赖 Studio 实现层。
2. 旧 Web Workbench 继续承载过多 artifact 展示逻辑。
3. hidden CLI surface 仍保留过多历史 operator/provider 命令。
4. `docs/handoff/` 保留了大量节点级历史证据，已超过当前产品交付需要。
5. 全仓人类文档中文化尚未彻底完成，当前审计对历史英文文档仍有豁免。

## 已删除

| 文件 | 原因 | 替代证据 |
|---|---|---|
| `docs/handoff/AFS-MEM-002.md` | 只自引用，已完成且不再是当前产品入口 | `docs/archive/task_history_2026_05.md`、`docs/archive/devlog_history_2026_05.md` |
| `docs/handoff/AFS-QA-001.md` | 只自引用，已完成且不再是当前产品入口 | `docs/archive/task_history_2026_05.md`、`docs/archive/devlog_history_2026_05.md` |

删除依据：

```text
rg -n "AFS-MEM-002|AFS-QA-001" docs README.md TASK_TRACKER.md DEVLOG.md tests apps agentflow agentflow_studio
```

结果只命中自身和 2026-05 归档摘要，说明独立 handoff 文件已经是重复历史。

## 不应立即删除

### 编号 demo 012 / 015

相关文件：

```text
agentflow_studio/memory_advantage_demo_012*.py
agentflow_studio/memory_advantage_demo_015*.py
tests/test_memory_advantage_demo_012.py
tests/test_memory_advantage_demo_015.py
apps/cli/memory_demo_commands.py
```

判断：暂缓删除。

原因：

- 仍被 hidden CLI、测试、历史 provider evidence 文档引用。
- 仍代表早期 MiniMax I2I + Kling I2V 可复现实验路径。
- 只有在 generic protocol runner 覆盖同等 live provider 行为后，才应删除。

删除条件：

1. protocol-driven runner 支持同等 I2I/I2V evidence package。
2. provider gate 输出 safe manifest 和 review artifact。
3. 对应测试从 demo-specific tests 迁移到 protocol tests。
4. hidden demo commands 从 CLI 注册器移除。

### `apps/web/`

判断：冻结，不继续扩展；暂不删除。

原因：

- 外部前端团队会重建正式工作台。
- 当前静态 Web 仍是 artifact registry、review screen、project manifest 的参考实现和测试夹具。

删除条件：

1. 新前端已接入 Runtime Service v0.2。
2. artifact registry / selected JSON fixture / review screen 行为被 API 和前端 contract tests 覆盖。
3. `tests/test_web_static_*` 中的关键行为迁移完成。

### `apps/web_bridge/`

判断：迁移后删除。

原因：

- 它与 `apps.cli` 存在循环依赖。
- 新前端边界应是 Runtime Service，不是 CLI bridge。

删除条件：

1. Runtime Service 覆盖当前 bridge 的必要查看能力。
2. CLI 默认帮助不再暴露 `web-bridge`。
3. `tests/test_web_production_bridge.py` 迁移或退休。

## 必须拆分的结构债

### `agentflow` 反向依赖 `agentflow_studio`

当前 `agentflow.memory` 对 `agentflow_studio.utils.write_json` 的反向依赖已迁移到 `agentflow.harness.json_io`。`production_asset_profile_provider.py` 对 `agentflow_studio.model_gateway` 的直接引用也已拆为注入式 provider executor。

处理顺序：

1. 保持 `write_json` 等通用工具在 `agentflow.harness` 或共享基础模块中，禁止重新从 `agentflow_studio` 反向引用。
2. `agentflow.memory` 只能依赖 `agentflow` 内部或标准库。
3. provider 调用保持在 adapter 层，核心 contract 只接收 provider capability/result artifact。
4. 后续继续拆 `agentflow_studio.model_gateway` 内部 plan、transport、poll/recovery 和 safe report。

### `apps.cli` 与 `apps.web_bridge` 循环依赖

当前状态：循环依赖已清除，旧 bridge 暂保留为 legacy 入口。

已完成：

1. `apps.cli.command_registry` 不再顶层 import `apps.web_bridge.server`。
2. `apps.reporting.run_reports` 接管 inspect/review/package/delivery report helper。
3. `apps.web_bridge` 不再 import `apps.cli.report_commands`。

后续：

1. 旧 bridge 命令移入 support/legacy registry 或从默认产品命令中退休。
2. Runtime Service 成为前端唯一正式入口。

### `harness` 与 `workflow_engine` 循环依赖

处理顺序：

1. `WorkflowRunner` 不从 `agentflow_studio.harness` 聚合入口 import。
2. 改为显式 import `trace`、`run_manifest` 的窄函数，或建立 `workflow_engine.artifact_writers` adapter。
3. harness 可读取 run/context type，但不能反向驱动 workflow runtime。

### `model_gateway` 与 `production.posterflow` 循环依赖

处理顺序：

1. provider 通用错误、gate、request hash 下沉到 gateway common。
2. PosterFlow 只消费 provider interface，不被 gateway plan 反向 import。
3. MiniMax/Kling smoke 拆为 plan、transport、poll/recovery、safe report。

## 下一轮推荐切片

### AFS-ARCHITECTURE-AUDIT-GATES-001

目标：把本轮发现变成自动化门禁，不先大改业务。

新增测试建议：

- 禁止 `agentflow.*` import `agentflow_studio.*`。
- 禁止 `apps.api.*` import `apps.cli.*` 或 `apps.web_bridge.*`。
- 禁止新增 `memory_advantage_demo_XXX` 模块。
- 检查 hidden CLI command 数量只能下降，不能无说明上升。
- 检查人类活文档中文覆盖率，不再把新文档自动归入历史豁免。

落地记录：

```text
docs/maintenance/AFS-ARCHITECTURE-AUDIT-GATES-001.zh-CN.md
tests/test_architecture_audit_gates.py
```

本轮已先减少一处债务：`apps/cli/command_registry.py` 的旧 Web bridge 顶层 import 已改为 lazy import。

### AFS-RUNTIME-SERVICE-V0-2-SPLIT-001

目标：拆分 Runtime Service，给前端团队稳定 API 面。

拆分建议：

```text
apps/api/routes/projects.py
apps/api/routes/runs.py
apps/api/routes/feedback.py
apps/api/routes/provider.py
apps/api/openapi_export.py
```

### AFS-LEGACY-WEB-BRIDGE-RETIREMENT-001

目标：把 `apps/web_bridge` 从正式路径降级为 legacy support，最终删除。

## 验证计划

本轮低风险删除后至少运行：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_agentflow_roadmap_docs.py tests/test_contract_examples.py -q
.\.venv\Scripts\python.exe tools\maintenance_audit.py
git diff --check
```

如继续删除 CLI、provider 或 Web 文件，必须追加相关 focused tests 或全量 pytest。

## 非声明边界

- 本轮删除不代表历史证据无效，只代表独立文件已被归档摘要替代。
- 本轮审查不是 human acceptance。
- 本轮审查不是 business validation。
- 本轮审查不向 `10-Startup` 自动晋升规则。
