# 开发日志

状态：当前会话短日志。历史长叙事不作为当前任务入口。

## 当前证据入口

- 当前任务账本：`TASK_TRACKER.md`
- Product Spine Reset 账本：`docs/maintenance/AFS-PRODUCT-SPINE-RESET-003.zh-CN.md`
- 本地内测落地记录：`docs/handoff/AFS-LOCAL-INTERNAL-TEST-LANDING-001.md`
- Runtime Service 前端对接：`docs/handoff/AFS-RUNTIME-SERVICE-FRONTEND-INTEGRATION-001.md`
- 前端中文交接包：`docs/frontend_integration/AFS_FRONTEND_HANDOFF.zh-CN.md`

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
