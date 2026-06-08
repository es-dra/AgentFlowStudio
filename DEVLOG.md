# 开发日志

状态：当前会话短日志。历史长叙事不作为当前任务入口。

## 当前证据入口

- 当前任务账本：`TASK_TRACKER.md`
- 低成本维护收口：`docs/maintenance/AFS-MAINTENANCE-CLOSEOUT-001.zh-CN.md`
- Product Spine Reset 账本：`docs/maintenance/AFS-PRODUCT-SPINE-RESET-003.zh-CN.md`
- 本地内测落地记录：`docs/handoff/AFS-LOCAL-INTERNAL-TEST-LANDING-001.md`
- Runtime Service 前端对接：`docs/handoff/AFS-RUNTIME-SERVICE-FRONTEND-INTEGRATION-001.md`
- 前端中文交接包：`docs/frontend_integration/AFS_FRONTEND_HANDOFF.zh-CN.md`

## 2026-06-09 - 低成本维护强删收口

- 直接退休旧编号式 `memory_advantage_demo_*` 模块、旧 Alpha smoke CLI、旧 `memory-video-pipeline` CLI/core/examples/tests。
- 删除不再服务当前主线的大批旧文档、长历史归档、旧 workbench/task brief/company-kb-feedback 子目录文档。
- 过渡 Web 继续保留为 read-only/local-only artifact viewer，但删除旧内置 sample bundle、demo evidence、browser feedback draft 和旧 memory video package 视图。
- `contract_registry.example.json` 与 `contract_audit_report.example.json` 已移除退休 artifact type，并把仍有效 contract 指向当前中文架构/资产 profile 文档。
- 当前 product spine 收敛为：Runtime Service / Production Memory asset loop / Project Manifest / Provider Gate / read-only artifact viewer / maintenance audit。

边界：

- 未启动 provider。
- 未写入 secret、signed URL、本地私有素材、生成媒体字节或 runtime artifact。
- 未声明 human acceptance、business validation 或 durable memory。
- 未写入或晋升 `10-Startup` / COS active rule。

局部验证：

- 契约 / CLI focused：`41 passed`。
- Web static focused：`26 passed`。
- 全部 Web static：`83 passed`。
- 维护 / 架构 / retention focused：`38 passed`。
- Web JS 语法检查通过：`memory-workbench-controller.js`、`memory-workbench-render.js`、`memory-workbench-studio-render.js`、`artifact-contracts.js`、`artifact-workspace.js`。
- `maintenance_audit`：`failed=0, passed=5, warning=1`；`secret_like_fragments high_confidence_count=0`；`oversized_files=24`。
- `repository_retention_review --summary-only`：`delete_candidate_count=0`，`manual_review_required_count=0`；当前未提交删除仍显示为 `remove_applied_pending_stage=108`，提交后应消失。
- 全量 pytest：`901 passed, 1 warning`。
- `git diff --check` 通过。

## 2026-06-09 - 低成本维护收口 001

- 将 `secret_like_fragments` 审计从粗粒度字段扫描改为区分高置信 secret、schema 字段、环境变量引用、参数引用和测试 fixture。
- 新增 `tools/maintenance_audit_secret_scan.py`，避免维护审计主文件继续膨胀。
- 将 `configs/tool_catalog.yaml` 从 1100+ 行单文件改为索引文件，实际工具条目拆入 `configs/tool_catalog/` 分片。
- 新增 `agentflow_studio/workflow_engine/tool_catalog.py`，让 workflow planner 和测试共享 tool catalog contract 加载路径。
- 拆分过渡 Web 的 artifact workspace、memory inspector、production inspector facts 映射文件；这些文件仍是 read-only / local-only 过渡面，不作为未来正式 Web 架构。
- 更新 retention policy：tool catalog 索引和分片作为当前 supporting contract，不再作为 split candidate。

边界：

- 未启动 provider。
- 未写入 secret、signed URL、本地私有素材或生成媒体字节。
- 未声明 human acceptance、business validation 或 durable memory。
- 未写入或晋升 `10-Startup` / COS active rule。

局部验证：

- 维护 / tool catalog / retention 聚焦测试：`29 passed`。
- Web artifact workspace / inspector 聚焦测试：`26 passed`。
- Web facts JS 语法检查通过。
- `maintenance_audit`：`failed=0, passed=5, warning=1`；`secret_like_fragments count=0`；`oversized_files=24`。
- `repository_retention_review --summary-only`：`delete_candidate_count=0`，`manual_review_required_count=0`。
- 全量 pytest：`997 passed, 1 warning`。
- `git diff --check` 通过。

## 2026-06-08 - Product Spine Reset 003 强删除切片

- 直接删除旧 `apps/web_bridge/`、`web-bridge` CLI、旧 bridge 测试。
- 直接删除旧 Web Production Mode：`apps/web/production-*`、`production.css`、生产模式静态测试。
- 直接删除旧 Local Alpha 长文、旧 Web/Alpha/Poster/Memory task brief、旧 workbench reference/milestone。
- 直接删除 `docs/handoff` 中不再服务当前产品主干的旧 demo、competition、Company KB、generic Production Memory operator node handoff，当前只保留资产闭环、Runtime Service、前端对接和本地内测落地入口。
- 将 still-useful memory evidence reuse contract 从旧 `local_alpha_0_4` 命名改为通用 `production_memory` 命名。
- 将 `apps/web` 重新限定为 read-only / local-only artifact viewer，不再保留旧 bridge 或旧 production-mode 执行面。
- 将 `tools/repository_retention_policy.py` 改为 Product Spine 删除语义：Git 已删除文件统一标记为 `remove_applied_pending_stage`；`apps/web_bridge` 重新出现时仍是删除候选。

边界：

- 未调用 provider。
- 未写入 secret、signed URL、私有素材或生成媒体字节。
- 未声明 human acceptance、business validation 或 durable memory。
- 未写入或晋升 `10-Startup` / COS active rule。

## 验证记录

已完成：

- CLI help 可运行。
- CLI version 输出 `0.1.0`。
- 聚焦回归：`56 passed`。
- Web JS 语法检查通过：`app.js`、`app-shell-template.js`、`app-elements.js`、`feedback-wiring.js`、`feedback-event.js`。
- `maintenance_audit`：`failed=0, passed=4, warning=2`。
- `repository_retention_review --summary-only`：`delete_candidate_count=0`，`manual_review_required_count=0`，`remove_applied_pending_stage=132`。
- 全量 pytest：`992 passed, 1 warning`。

## 2026-06-08 - Model Gateway / Production 循环依赖切片

- 将 provider 边界异常和 MiniMax 默认值下沉到 `agentflow_studio/provider_contracts.py`。
- `agentflow_studio.model_gateway.errors` 保留兼容导出，避免破坏旧调用面。
- `production.posterflow` 不再依赖 `model_gateway.errors`。
- `model_gateway.minimax_image_smoke` 不再调用生产侧 PosterFlow provider/schema，改由 `model_gateway.minimax_image_runtime` 独立完成 smoke 请求和 safe output summary。
- 架构门禁移除 `agentflow_studio.model_gateway <-> agentflow_studio.production` 循环豁免。

边界：

- 未调用 live provider。
- 未写入 secret、signed URL、私有素材或生成媒体字节。
- 未声明 human acceptance、business validation 或 durable memory。

验证记录：

- 红灯确认：移除循环豁免后，`test_package_level_cycle_debt_is_frozen` 能捕获 `model_gateway/production` 循环。
- 聚焦 provider/architecture：`20 passed`。
- 扩展 provider/architecture/CLI：`47 passed`。
- CLI help 可运行；CLI version 输出 `0.1.0`。
- `maintenance_audit`：`failed=0, passed=4, warning=2`。
- 全量 pytest：`992 passed, 1 warning`。
- `git diff --check` 通过。
- 静态 import 搜索未发现 `model_gateway` 与 `production` 之间的交叉引用。

## 2026-06-08 - Maintenance Debt Closure 001

- 新增 `agentflow_studio/workflow_run_artifacts.py`，把 workflow trace 与 run manifest 写入从 `harness` 包中抽到中立模块。
- `workflow_engine.runner` 不再依赖 `harness`，`harness.trace` 与 `harness.run_manifest` 改为兼容导出层。
- 架构门禁从“冻结已知包级循环债务”改为“不允许任何包级循环”。
- 新增 `.github/workflows/maintenance.yml`，CI 默认运行 CLI smoke、`maintenance_audit`、全量 pytest 和 `git diff --check`，并显式关闭 live provider gate。
- 新增 `tests/test_ci_maintenance_workflow.py`，防止维护门禁缺失或 CI 默认打开 provider。

边界：

- 未调用 live provider。
- 未删除仍被测试和文档引用的 hidden CLI 兼容命令。
- 未写入或晋升 `10-Startup` / COS active rule。
- 未声明 human acceptance、business validation 或 durable memory。

验证记录：

- 红灯确认：移除 `harness/workflow_engine` 循环豁免后，架构门禁能捕获旧循环。
- 聚焦测试：`12 passed`。
- 静态 import 搜索未发现 `harness` 与 `workflow_engine` 之间的交叉引用。
- Retention review 对新增 `.github/workflows/maintenance.yml` 先报 `manual_review_required_count=3`；已将 `.github` 和 workflow 文件登记为 `operations_spine`，复测 `manual_review_required_count=0`。
- CLI help 可运行；CLI version 输出 `0.1.0`。
- `maintenance_audit`：`failed=0, passed=4, warning=2`。
- `repository_retention_review --summary-only`：`delete_candidate_count=0`，`manual_review_required_count=0`。
- 全量 pytest：`994 passed, 1 warning`。
- `git diff --check` 通过。
## 2026-06-09 - Oversized Maintenance Closure 001

- 删除已退休的成片后处理工作流面：assembly、subtitle export/burn、BGM、cover、finished package、delivery readiness，以及只服务这些链路的 demo、SOP、workflow node、tool catalog entry、CLI 命令和测试。
- 保留当前主线：Runtime Service、Production Memory Asset Loop、Project Manifest、Provider Gate、maintenance audit、read-only artifact viewer、纯切片和内容制作 workflow。
- 将剩余超长核心文件按职责拆分为更小模块：workflow 输入解析、video artifact review、review recommendations、operator run package render、promotion checks、asset validation、acceptance overlay validation、asset consistency validation、asset profile seed validation、production quality review、production memory operator runner。
- 将 `examples/agentflow/contract_audit_report.example.json` 做无语义排版压缩，避免 schema 示例继续触发 oversized warning。
- 新增 project-local Company OS feedback candidate packet：`docs/maintenance/AFS-COMPANY-OS-FEEDBACK-PACKET-OVERSIZED-CLOSURE-001.zh-CN.md`；未写入或晋升 `10-Startup` / COS active rule。

边界：

- 未启动 provider。
- 未写入 secret、signed URL、本地私有素材、provider 原始响应或生成媒体字节。
- 未声明 human acceptance、business validation 或 durable memory。

验证状态：

- `maintenance_audit`: `failed=0, passed=6, warning=0`。
- 完整 CLI、focused pytest、full pytest 和 `git diff --check` 在最终提交前执行。
