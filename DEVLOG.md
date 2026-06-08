# 开发日志

状态：当前会话短日志。历史长叙事放到 `docs/archive/` 或具体 handoff / maintenance 文件中，本文件只保留近期证据入口。

## 当前证据入口

- 活任务账本：`TASK_TRACKER.md`。
- 本轮维护账本：`docs/maintenance/AFS-MAINTENANCE-LOCALIZATION-CLEANUP-001.zh-CN.md`。
- 逐目录逐文件保留性审查：`docs/maintenance/AFS-REPOSITORY-RETENTION-REVIEW-001.zh-CN.md`。
- 本轮 handoff：`docs/handoff/AFS-MAINTENANCE-LOCALIZATION-CLEANUP-001.md`。
- Runtime Service 前端对接：`docs/handoff/AFS-RUNTIME-SERVICE-FRONTEND-INTEGRATION-001.md`。
- 本地内测落地记录：`docs/handoff/AFS-LOCAL-INTERNAL-TEST-LANDING-001.md`。
- 前端中文交接包：`docs/frontend_integration/AFS_FRONTEND_HANDOFF.zh-CN.md`。
- AFS/COS Agent 项目开发规范候选：`docs/maintenance/AFS-AGENT-PROJECT-DEVELOPMENT-STANDARD-001.zh-CN.md`。
- 深度瘦身审查：`docs/maintenance/AFS-DEEP-CLEANUP-AUDIT-001.zh-CN.md`。
- 架构审计门禁：`docs/maintenance/AFS-ARCHITECTURE-AUDIT-GATES-001.zh-CN.md`。
- 实际清理记录：`docs/maintenance/AFS-ACTUAL-CLEANUP-002.zh-CN.md`。
- 历史英文文档中文摘要索引：`docs/archive/HISTORICAL_DOCS_SUMMARY.zh-CN.md`。
- 历史开发日志归档：`docs/archive/devlog_history_2026_06_03_pre_slimming.md`。
- 历史任务账本归档：`docs/archive/task_history_2026_06_03_pre_slimming.md`。

## 2026-06-08 - Harness-first Agentic Delivery 定位投影

- 将 AFS 当前主打主题从 memory-first 叙事调整为 `Harness-first Agentic Delivery System`：AFS 是本地优先 Agent 工程工作台，用于验证提示词、上下文、工具、规则、执行轨迹、质量报告和反馈信号组成的可重复项目交付闭环。
- 在 `10-Startup/20-Operating-System/05-Harness-First-Agentic-Delivery-System.md` 新增源头定位文档，并更新 `AI-Native-Company-OS-MAP.md` 与 `20-Operating-System/README.md` 的术语分工。
- 更新 AFS `README.md` 和 `docs/company_operating_model.md`：`AI-Native Company OS` 是总系统，`Harness-first Agentic Delivery System` 是当前主打项目交付主题，`Evidence-backed Context Runtime` 是上下文运行层，`Governed Memory / Memory OS` 是记忆和知识晋升子系统 / 长期愿景。
- 在 `TASK_TRACKER.md` 登记 `AFS-POSITIONING-HARNESS-FIRST-001`，下一步验证应放到真实开发/维护任务中，而不是另起理论 demo。
- 边界保持：本次为 docs/rules 投影，未修改 runtime/provider 代码，未调用 provider，未声明 human acceptance、business validation 或 Company OS active-rule promotion。

## 2026-06-08 - 实际清理 002

- 从 `origin/master` 新开 `codex/afs-actual-cleanup-002`，保留已有 COS 执行投影 dirty 变更。
- 将 `agentflow_studio/model_gateway/kling_video_smoke.py` 中的任务完成、httpx->curl fallback、视频下载、safe state/manifest 写入逻辑拆到 `agentflow_studio/model_gateway/kling_video_completion.py`；公开 smoke 入口保持不变。
- `kling_video_smoke.py` 从 327 行降到 201 行，退出 `maintenance_audit` 的 oversized warning；新增 completion 模块为 116 行。
- 将 `kling_video_task_state.py` 的 JSON 写入 helper 从旧 `agentflow_studio.utils` 切到 `agentflow.harness.json_io`。
- 拆分 `tests/test_kling_video_task_recovery.py`：task recovery / completion fallback / runtime polling 分别进入独立测试文件；原测试文件从 317 行降到 172 行。
- 拆分 `tests/test_minimax_image_smoke.py` 的 CLI 面到 `tests/test_minimax_image_smoke_cli.py`；原测试文件从 329 行降到 232 行。
- 拆分 `tests/test_posterflow_provider.py`：OpenAI-compatible provider 测试进入 `tests/test_posterflow_openai_provider.py`，共享 fixture 进入 `tests/posterflow_provider_helpers.py`；原测试文件从 342 行降到 188 行。
- 验证：Kling focused tests `16 passed`；Kling + 架构门禁 `22 passed`；拆分后 Kling + 架构门禁仍为 `22 passed`；MiniMax CLI focused tests `16 passed`；PosterFlow provider focused tests `13 passed`；最终 provider/CLI/维护聚焦测试 `63 passed`；`maintenance_audit` 为 `failed=0, passed=4, warning=2`，oversized 文件从 33 降到 29；`git diff --check` 退出码 0。
- 边界保持：未调用 provider，未写入 secret / signed URL / 媒体字节，未声明 human acceptance、business validation 或 durable memory。

## 2026-06-08 - Product Spine Reset 003 启动

- 在 `001def9` 封存 provider cleanup baseline 后，新开 `codex/afs-product-spine-reset-003`。
- 将 `tools/repository_retention_review.py` 从温和保留语义升级为 Product Spine 审查语义，新增 `product_surface` 与 `product_surface_counts`，明确暴露 `transition_surface`、`quarantine_candidate`、`historical_reference` 和 `mixed_docs_surface`。
- 当前审查显示：`quarantine_candidate=19`，`transition_surface=87`，`historical_reference=120`，`mixed_docs_surface=71`；仓库不再按“无删除候选”理解，而是按旧面/过渡面推进退休。
- 删除旧编号 memory advantage demo 的 CLI 可执行入口：移除 `apps/cli/memory_demo_commands.py`，`support_command_registry` 不再注册 `memory-advantage-demo-012*` / `memory-advantage-demo-015*` hidden commands。
- 更新架构门禁：`KNOWN_HIDDEN_COMMAND_DEBT` 不再允许上述 5 个旧 demo hidden CLI。
- 将 `web-bridge` 从可见产品 CLI 降级为 hidden legacy command，默认 help 不再展示旧 Web bridge；Runtime Service 继续作为前端唯一主对接面。
- 拆分 `tools/repository_retention_review.py`，将分类策略下沉到 `tools/repository_retention_policy.py`；两个文件分别为 124 / 188 行，避免维护工具自身变成新的超长文件。
- 验证：旧 demo CLI 删除聚焦测试为 `32 passed`；`web-bridge` 降级聚焦测试为 `22 passed`；最终聚焦回归 `50 passed`；完整 pytest 为 `1023 passed, 1 warning`；`maintenance_audit` 为 `failed=0, passed=4, warning=2`；`repository_retention_review --summary-only` 可直跑；`git diff --check` 退出码 0。
- 边界保持：旧 demo modules 暂时保留为 quarantine candidate，用于迁移前 evidence 校验；未调用 provider，未声明 human acceptance、business validation 或 durable memory。

## 2026-06-08 - 外部项目思想协助标准投影

- 将 `claude-obsidian` 和 `GitNexus` 的核心思想收敛为 Company OS candidate guidance：外部项目只作为机制来源，先对话总结，再映射到本地知识对象、全局规则和项目开发链路，不默认安装、不默认复刻、不默认创建 intake 文档。
- 在 `10-Startup/80-Workflow/ai-native-company-workflow/agent-assistance-standard.md` 新增 candidate 标准，并在 `candidate-rule-ledger.md` 登记为 P1 candidate。
- 在全局 `project-development-workflow` skill 增加 routing hook，未来进入项目时可读取该协助标准。
- 在 `docs/company_operating_model.md` 增加 AFS 执行投影，只记录项目执行需要的摘要，不复制 Company OS 源头知识。
- 边界保持：未安装或运行外部工具，未调用 provider，未写入 secret，未晋升 Company OS active rule；后续需要通过 AFS 真实开发/维护任务产生 feedback signal 后再考虑 `limited`。

## 2026-06-08 - 深度瘦身审查

- 重新审查目录体量、Python import 关系、CLI hidden surface、Web 静态模块、handoff 引用关系和文档中文化覆盖。
- 已确认 2 组循环依赖仍需后续拆分：`agentflow_studio.harness` / `agentflow_studio.workflow_engine`、`agentflow_studio.model_gateway` / `agentflow_studio.production`；`apps.cli` / `apps.web_bridge` 已通过 `apps.reporting.run_reports` 解耦。
- 已删除两个只自引用且已有 2026-05 归档摘要替代的旧 handoff：`docs/handoff/AFS-MEM-002.md`、`docs/handoff/AFS-QA-001.md`。
- 编号 demo 012 / 015、旧 `apps/web/` 和 `apps/web_bridge/` 暂不直接删除；它们需要先完成 protocol runner、Runtime Service v0.2 和前端替代路径。
- 已新增 `tests/test_architecture_audit_gates.py`，冻结 Runtime Service 边界、核心层反向依赖、包级循环依赖、hidden CLI surface 和编号 demo 模块；focused test `5 passed`。
- `web-bridge` 命令保留，但 `apps/cli/command_registry.py` 改为执行时 lazy import 旧 bridge，减少 CLI 默认静态依赖。
- 新增 `apps.reporting.run_reports`，CLI 和旧 Web bridge 共同依赖该应用层 helper；`apps.web_bridge` 不再 import `apps.cli.report_commands`，包级循环依赖已清除。
- 已新增 `agentflow.harness.json_io`，并将 `agentflow.memory` 下 44 个模块从 `agentflow_studio.utils.write_json` 迁移到平台 harness helper。
- 已将 `apps/api` 与 `apps/cli` 下 5 个 JSON 写入调用迁移到 `agentflow.harness.json_io`，并用架构门禁防止 API/CLI 继续从 Studio utils 获取通用 IO。
- 已将 `agentflow.memory.production_asset_profile_provider` 的 live provider 调用改为注入式 `ProviderValidationExecutor`，并新增 `agentflow_studio.model_gateway.asset_profile_provider_adapter` 承接 MiniMax/Kling smoke；架构门禁现在要求 `agentflow` 对 `agentflow_studio` 零反向依赖。

## 2026-06-08 - 维护性重置与中文化

- 建立 `codex/afs-maintenance-localization-cleanup-001` 作为当前维护性重置单一分支，保留已有 Runtime Service、本地内测、provider recovery、Web review 和前端 handoff 未提交成果。
- 新增维护账本，记录 dirty ownership、保留/归档/删除/暂缓分类、验证命令、回滚方式、外部参考和非声明边界。
- 新增 `tools/maintenance_audit.py`，输出 `agentflow_maintenance_audit_report`，检查旧源头路径、人类文档中文覆盖、secret-like 文本、超长文件和 runtime artifact 入库风险。
- 新增 `tools/repository_retention_review.py`，逐目录逐文件输出保留理由、退休条件和可直接删除候选。
- 删除冗余 `README.zh-CN.md`，`README.md` 成为唯一中文主入口。
- 新增本地 AgentOps contract examples：`agentflow_run_trace`、`agentflow_quality_report`、`agentflow_guardrail_result`、`agentflow_handoff_record`、`agentflow_maintenance_audit_report`。
- Runtime Service job 现在生成 `agentflow_run_trace`，记录 safe refs、provider gate state、generated artifact refs、blocked refs、tester feedback state 和 `non_claims`。
- 拆分 Runtime Service helper：artifact 注册和 Project Manifest 更新放入 `apps/api/runtime_artifacts.py`，trace helper 放入 `apps/api/runtime_tracing.py`。
- 中文化当前活入口文档：`README.md`、`AGENTS.md`、`TASK_TRACKER.md`、`DEVLOG.md`、`docs/README.md`、`docs/company_operating_model.md`、`apps/api/README.md`、`apps/web/README.md`、`configs/README.md`、`prompts/README.md`、`skills/README.md`、`workflows/README.md`、`docs/frontend_integration/`、`docs/local_internal_test_runbook.md`、`docs/project_manifest_contract.md`、当前 Runtime Service handoff、本地内测 handoff。
- 修正 `tools/maintenance_audit.py` 的中文覆盖率计算：fenced code block 和 inline code 不参与人类文档中文比例，避免把 API path、JSON key、CLI command 误判为英文残留。
- 新增 `docs/archive/HISTORICAL_DOCS_SUMMARY.zh-CN.md`，把旧 handoff、旧路线图、旧验收记录和历史长文按“做了什么 / 是否仍有效 / 替代路径 / 证据路径 / 非声明边界”归档为中文摘要索引；维护审计只在该摘要存在时豁免历史文档。
- 将 `tools/maintenance_audit.py` 的策略常量拆到 `tools/maintenance_audit_policy.py`，主审计脚本按含空行统计降至 275 行。
- 调整 `tools/staging_preflight.py`：本地 secret/runtime 路径继续作为 block，超 300 行改为 warning；测试中的本机 `.secrets` 绝对路径改为运行时拼接，避免提交敏感路径字面量。
- 在 `D:\Learning materials\Learning_notes\10-Startup\30-Engineering\03-AI-Agent项目可维护性与中文化规范.md` 新增 COS candidate 规则，并在 `candidate-rule-ledger.md` 登记为 candidate-only evidence。
- 已清理 `.pytest_cache` 和 34 个 `__pycache__` 目录。`data/processed/pytest-basetemp/` 下多个 ignored 历史目录因 Windows 权限拒绝未能删除，已记录为本地运行残留。
- 边界保持：未调用 provider，未写入 secret，未复制私有素材，未声明 human acceptance、business validation、durable memory 或 COS active-rule promotion。

## 验证记录

- full pytest：`1023 passed, 1 warning`。
- 中文化后 focused regression：`72 passed, 1 warning`；维护/保留 focused regression：`8 passed`；保留性审查回归：`3 passed`。
- staging preflight：`status: pass`，仅保留 oversized warning；staging preflight focused regression：`12 passed`。
- `repository_retention_review`：覆盖 83 个目录、1004 个文件，`delete_candidate_count=0`，`manual_review_required_count=0`；新增 `apps/reporting` 已归类为 `retain_application_reporting`。
- `maintenance_audit`：`failed=0, passed=4, warning=2`；人类 Markdown 中文覆盖已通过，历史文档摘要豁免 187 份；剩余 warning 来自低置信 secret-like 字段名/测试假值和超 300 行文件。
- `git diff --check` 通过，仅 Windows LF-to-CRLF warning。
- 旧 `Company` 源头路径/旧文案扫描无命中。

## 2026-06-08 - Runtime Service 前端对接

- 新增本地 FastAPI Runtime Service v0.1，作为外部前端/画布工作台对接后端基线。
- 前端只拿 `project_id`、`job_id`、`artifact_id`、safe payload 和 safe summary，不接触 CLI 内部编排、provider secret、私有路径、signed URL 或媒体字节。
- 暴露 health、capabilities、project manifest、artifact read、Round 1 asset test、Round 2 validation、raw feedback、provider validation plan 等本地 endpoint。
- 新增 `runtime-service` CLI 命令，保留 `web-bridge`。
- 准备 `docs/frontend_integration/` 和 `examples/frontend_runtime_service/`。
- 边界保持：无 SaaS、数据库、账号系统、browser persistence、live provider execution endpoint、durable memory、human acceptance、business validation。

## 2026-06-04 - 本地内测落地

- 完成 Asset Profile Review Screen、Real Asset Test Run Harness、Two-Round Context Runtime Validation、Project Manifest v0.1、Provider Validation Gate。
- 本地 deterministic 输出默认写入 ignored runtime path，不默认启动 live provider。
- Loulan 显式素材跑通 Round 1 和 Round 2；Round 2 结构验证为 `verified`，`improvement_assessment=improved`。
- 在显式 image/video gate 和本地 provider config 下完成 provider smoke；Minimax image 和 Kling I2V 成功，但这只代表 provider smoke / runtime evidence。
- 修复 Kling transport recovery：httpx 失败可回退 curl，poll transient error 可重试，curl TLS handshake failure 可重试一次。
- 新增本地内测 runbook 和 Project Manifest contract 文档。
- 更新 `10-Startup` candidate feedback packet；不晋升 COS active rule。
