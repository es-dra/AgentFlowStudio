# 开发日志

状态：当前会话短日志。历史长叙事不作为当前任务入口。

## 当前证据入口

- 当前任务账本：`TASK_TRACKER.md`
- 落地前内容制作 / 记忆链路与 Web 规划：`docs/handoff/AFS-LANDING-PREP-CONTENT-MEMORY-WEB-001.md`
- 低成本维护收口：`docs/maintenance/AFS-MAINTENANCE-CLOSEOUT-001.zh-CN.md`
- Product Spine Reset 账本：`docs/maintenance/AFS-PRODUCT-SPINE-RESET-003.zh-CN.md`
- 本地内测落地记录：`docs/handoff/AFS-LOCAL-INTERNAL-TEST-LANDING-001.md`
- Runtime Service 前端对接：`docs/handoff/AFS-RUNTIME-SERVICE-FRONTEND-INTEGRATION-001.md`
- 前端中文交接包：`docs/frontend_integration/AFS_FRONTEND_HANDOFF.zh-CN.md`

## 2026-06-09 - Web Vertical Flow 001

- Started `AFS-WEB-VERTICAL-FLOW-001`: deterministic Workbench path from empty project toward `ready_for_next_round`.
- Added API-level vertical flow coverage for create project -> source summaries -> Draft Canvas -> inspector -> first deterministic check -> review decision -> two-round validation -> provider preflight readiness.
- Added compact `flow` summaries to Runtime mutation responses so the frontend can show target status, current action, next command, Studio status, provider status, and non-claims without re-inferring the workflow.
- Improved Workbench startup and navigation: empty workspace now exposes project create/open controls; Studio cross-stage commands navigate to the matching view; Project Hub no longer renders an empty-action Pending button.
- Added browser-level Workbench smoke: Runtime Service starts on a temporary port, Chromium clicks create -> source summary -> draft -> first check -> Review decision -> next round, and reaches `ready_for_next_round`.
- Tightened the main review action toward candidate-bound `record-review-decision`; generic `record-feedback` remains an auxiliary runtime control.
- Fixed Production Board layout after screenshot QA exposed right-column clipping; command/board surfaces now span the workbench width and board lanes wrap.
- Boundaries preserved: no live provider call, no secret, no signed URL, no private media bytes, no provider raw response, no durable-memory or human-acceptance claim.

## 2026-06-09 - Web Foundation 001

- Added Runtime Service workbench-state projection for frontend-facing project/canvas/events/provider status.
- Kept provider execution backend-gated and surfaced only safe UI summary for provider preflight state.
- Added `apps/workbench` as the new Runtime Service-backed product frontend foundation, separate from transitional `apps/web`.
- Implemented runtime client, workbench-state normalizer, DOM renderer, canvas workspace shell, inspector, jobs lane, provider gate panel, and collapsed advanced diagnostics.
- Added local Runtime Service CORS for localhost and direct file-origin workbench use.
- Classified `apps/workbench` in retention policy as current production spine.
- Added focused frontend boundary tests to prevent browser persistence, old bridge/CLI coupling, private local data references, and oversized new frontend files.
- Added implementation handoff: `docs/handoff/AFS-WEB-FOUNDATION-001.md`.

Boundaries:

- No live provider call was started.
- No secret, signed URL, private media, provider raw response, or generated media bytes were written.
- This is not human acceptance, business validation, or durable memory.
- `apps/workbench` is still a foundation; project-create/run/feedback actions are the next slice.

## 2026-06-09 - Web Workflow Controls 001

- Advanced `apps/workbench` from a read-only state shell to Runtime Service workflow controls.
- Added project create/open/import/export actions, deterministic Round 1 asset-test trigger, raw feedback recording, Round 2 validation trigger, provider preflight trigger, and safe artifact loading.
- Split frontend rendering into smaller modules: `dom.js`, `render-actions.js`, and `render-artifact.js`.
- Updated the frontend state adapter to consume backend `cards/card_id/primary_artifact_id` workbench-state payloads.
- Added workflow-control assertions to `tests/test_web_workbench_foundation.py`.
- Added handoff: `docs/handoff/AFS-WEB-WORKFLOW-CONTROLS-001.md`.
- Added Runtime Service static hosting for the Workbench at `/workbench/`, so
  frontend/backend integration can start from the same service origin instead
  of a file-only shell.
- Added deterministic Draft Canvas flow: Runtime Service now turns safe
  brief/reference/script summaries into Hook / Proof / CTA canvas cards, and
  Workbench exposes this as a one-click Scene Planner action.

Boundaries:

- No live provider call was started.
- Browser-side workflow execution was not introduced; all execution still goes through Runtime Service.
- No secret, signed URL, private media, provider raw response, or generated media bytes were written.
- HTTP smoke for `/workbench/` passed through a temporary Runtime Service;
  Draft Canvas HTTP smoke created 3 canvas cards and a 3-item filmstrip;
  browser screenshot QA is still pending because no Browser/Playwright/headless
  browser runtime is available in the current environment.

## 2026-06-09 - Workbench Projection Slices

- Added backend-driven `creation_workspace` and `memory_workspace` projections for Create and Review/Style Memory views.
- Split Create and Memory frontend state/render modules, removed obsolete `render-review.js`, and reduced `workbench-state.js` below the 300-line threshold.
- Runtime HTTP smoke passed for the new static modules and deterministic projection states; no live provider, secret, signed URL, private media, provider raw response, or generated media bytes were written.

## 2026-06-09 - Workbench Operations Workspace Slice

- Added backend-driven `operations_workspace` projection, combining job queue, latest activity, provider preflight, provider controls, polling, and blocker counts into one Runtime Service-safe contract.
- Added frontend Operations Workspace state/render modules and moved Job Center normalization out of `workbench-state.js`, reducing the total adapter to 184 lines.
- Replaced the Jobs view's parallel Job Center / Activity / Provider Gate panels with one Operations Workspace product surface.
- Boundaries preserved: no provider calls, no secrets, no private paths, no signed URLs, no media bytes, no provider raw responses, no human acceptance/business validation/durable-memory claim.
- Focused verification: state/Web foundation `11 passed, 1 warning`; Runtime/Web/API/action suite `18 passed, 1 warning`; Runtime-hosted Operations Workspace HTTP smoke passed.

## 2026-06-09 - Landing Prep Content / Memory / Web 001

- 重新按 COS / 全局映射规则定位本轮：先跑通内容制作 / 记忆链路，再规划 Web workbench；纯切片链路暂不进入下一阶段开发。
- 调研 LibTV、RHTV、芒果灵创等外部画布/影视 AIGC 工作台，提炼为 AFS 的 evidence-native operator workbench，而不是照搬通用媒体画布。
- 审计 Runtime Service v0.2 前端 contract：当前已覆盖 project manifest、asset-test、feedback、two-round validation、provider validation plan、safe artifact read、project import/export。
- 使用 `examples/frontend_runtime_service/` 请求 fixture 跑通 deterministic Runtime Service 链路，runtime 输出保存在 ignored 目录 `data/processed/runs/landing_prep_001_runtime_service_20260609`。
- 形成后端协同开发判断：第一版 Web 实现前应补一个 normalized workbench state adapter，并统一 blocker/node status 形状。
- 新增规划 handoff：`docs/handoff/AFS-LANDING-PREP-CONTENT-MEMORY-WEB-001.md`。
- 根据用户反馈修正 Web 定位：默认界面应接近现有画布类工具的低学习成本体验，AFS 的 evidence / memory / harness 细节进入后台能力和高级检查抽屉，不作为主界面默认心智模型。
- 进一步将 Web 规划从单一画布扩展为完整工业化前端：Project Hub、Project Setup、Asset Library、Creation Canvas、Review Room、Project Style Memory、Generation Queue、Advanced Diagnostics，并将下一阶段任务拆成 backend adapter、frontend foundation、project/setup、creation workspace、review/style memory、provider smoke 和 QA release gate。

边界：

- 未实现 Web UI。
- 未启动 provider。
- 未写入 secret、signed URL、本地私有素材、provider 原始响应或生成媒体字节。
- 未声明 human acceptance、business validation 或 durable memory。
- 未写入或晋升 `10-Startup` / COS active rule。

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
## 2026-06-09 - Studio Workspace Integration

- Added backend `studio_workspace` as a safe Runtime Service projection and replaced the stacked Create view with one product-facing Studio Workspace module.
- Added frontend state/render/CSS coverage for the workspace and kept cross-stage commands disabled when their required inputs belong to another view.
- Boundaries preserved: no provider call, no secret/signed URL/private path/provider raw response/media byte, and no human acceptance/business validation/durable memory claim.
- Verification: Studio Workspace focused tests `3 passed, 1 warning`; focused Runtime/Web/API/Web suite `23 passed, 1 warning`; Runtime-hosted smoke for the workspace JS/CSS returned `200`.

## 2026-06-09 - Web Workbench UX Refoundation Stage 0-7
- Added the long-cycle roadmap, Chinese UI terms, and UX QA ledger under `docs/frontend_integration/`.
- Added `workspace-config.js`, Chinese multi-workspace shell, project setup wizard, collapsed diagnostics, and split shell/setup CSS while preserving Runtime Service action ids.
- Split Studio Workspace into side rail, canvas, and inspector modules; added node-flow canvas, connectors, toolbar, empty flow, and inspector facts.
- Added grouped Asset Library and independent Storyboard Workspace with shot sequence, safe preview, refs/blockers, and Review entry actions.
- Split Review Room and Project Memory into separate product workspaces: candidate review queue / decision dock vs style profile / next-round reuse.
- Productized the Jobs view into a focused Task Center / Provider Gate workspace, removed common workflow panels from the task window, hid internal action/job ids from the main task surface, and moved Provider blocker styling into a dedicated operations stylesheet.
- Added frontend display-label mapping and no-store Runtime-hosted static responses to keep user-facing Workbench copy Chinese and fresh during browser QA.
- Completed Stage 7 release-candidate browser QA on `proj_stage7_rc_1781016167554`: Assets -> Draft Canvas -> Create -> Storyboard -> Review -> first check -> feedback -> next round -> Style Memory -> Jobs -> Provider preflight -> Settings/Diagnostics.
- Tightened user-facing Chinese display mappings after QA exposed English/default Runtime terms in main views; diagnostics remain the place for internal ids and raw safe refs.
- Updated Workbench README and tracker so the next frontend line is project -> canvas -> assets/storyboard -> review/memory -> jobs/diagnostics.
Boundaries: no live provider call; no secret, signed URL, private path, provider raw response, generated media byte, or COS active rule; not human acceptance, business validation, or durable memory promotion.
Verification: CLI help/version passed; focused Runtime/Web/API `23 passed, 1 warning`; full pytest `844 passed, 1 warning`; maintenance audit `failed=0, passed=6, warning=0`; `git diff --check` passed with line-ending warnings only; Runtime-hosted `/workbench/`, app entry, asset/storyboard/artifact modules returned HTTP `200` with `Cache-Control: no-store`; browser smoke on `proj_ui_stage4_browser_smoke` reached Assets/Storyboard with `englishLeaks=[]`, 4 asset groups, 3 storyboard shots, no local path exposure, and provider still gated. Stage 5 browser smoke on `proj_demo_reference_flow_1781004364` opened the reference project from the project list, rendered 5 review candidates, recorded review decisions through the Review Room, and verified Review Room / Project Memory with no checked internal action/job id leaks, no local path exposure, and no provider secret exposure. Stage 6 browser smoke verified Jobs as a focused Task Center with 6 job cards, Provider Gate visible, no common workflow panels, and no checked internal action/job id leaks. Stage 7 browser QA on `proj_stage7_rc_1781016167554` recorded console errors `0`, visible English `false`, main-view internal leak `false`, text overflow `0`, 1 asset, 4 canvas nodes, 3 storyboard shots, 1 style preference, 6 jobs, and 4 provider blockers. Final Stage 7 verification: Workbench frontend `11 passed`; full pytest `844 passed, 1 warning`; maintenance audit `failed=0, passed=6, warning=0`; Runtime HTTP smoke returned `200` and `Cache-Control: no-store`; `git diff --check` passed with line-ending warnings only. Screenshots: `data/processed/runs/workbench_live_demo/qa/stage5-review-memory-smoke.png`, `data/processed/runs/workbench_live_demo/qa/stage6-jobs-provider-smoke.png`, `data/processed/runs/workbench_live_demo/qa/stage7-rc-1440x900-diagnostics.png`, `data/processed/runs/workbench_live_demo/qa/stage7-rc-1366x768.png`, `data/processed/runs/workbench_live_demo/qa/stage7-rc-390x844.png`.

## 2026-06-09 - Web Workbench Human Acceptance Prep
- Added `docs/frontend_integration/AFS_WEB_RELEASE_CANDIDATE_ACCEPTANCE_PACKET.zh-CN.md` so the current `/workbench/` release candidate can be judged through a concrete Chinese operator path instead of informal impressions.
- Added `AFS-WEB-HUMAN-ACCEPTANCE-001` to `TASK_TRACKER.md`; this explicitly keeps Stage 7 browser QA separate from human acceptance and from provider smoke.
- Normalized Workbench cache-bust markers from the older stage label to `stage7-rc` and verified Runtime-hosted index/app/render module responses use `Cache-Control: no-store`.
- Hardened the browser Runtime client so failed API responses and malformed JSON show safe Chinese status messages instead of raw response bodies.
- Added `docs/frontend_integration/AFS_WEB_RC_DEMO_INDEX.zh-CN.html` as a local visual index over the Stage 7 screenshots, acceptance path, and provider/human-acceptance boundaries.
- Added `docs/handoff/AFS-WEB-RC-DRAFT-PR-001.md` with a ready-to-copy draft PR body after local `gh` was unavailable and the GitHub connector token was expired.
- Boundaries unchanged: provider remains closed; no secret, private media, provider raw response, signed URL, COS active rule, human acceptance claim, business validation claim, or durable memory promotion.

## 2026-06-09 - Web Provider Smoke Readiness Prep
- Added `docs/handoff/AFS-WEB-PROVIDER-SMOKE-READINESS-001.md` to separate Web RC human acceptance from later capability-gated provider smoke.
- Registered the handoff in `docs/handoff/INDEX.md` and updated `AFS-PROVIDER-GATED-REAL-SMOKE-001` in `TASK_TRACKER.md`.
- Ran readiness-only provider gate without `--run-provider-validation`; it wrote ignored evidence under `data/processed/runs/web_rc_provider_gate_readiness/` with `status=blocked` and `provider_calls_started=false`.
- Boundaries unchanged: provider not executed; no secret, local private material, provider raw response, signed URL, generated media byte, COS active rule, human acceptance claim, business validation claim, or durable memory promotion.

## 2026-06-09 - Web Workbench Acceptance Rehearsal
- Made `/workbench/` auto-connect to Runtime Service and load the default project on cold start so the first screen is a usable workspace instead of an empty disconnected shell.
- Tightened user-facing display mappings for provider gate, activity, review, and storyboard reference surfaces; safe artifact ids remain hidden from main creative views.
- Browser rehearsal covered Projects, Create, Assets, Storyboard, Review, Style Memory, Jobs, and Settings: console errors `0`, checked English/internal-id/local-path leaks `0`, text overflow `0`.
- Evidence screenshot: `data/processed/runs/workbench_live_demo/qa/acceptance-rehearsal-auto-connect-clean-1440x900.png`.
- Boundaries unchanged: no live provider call, no secret/private media/provider raw response/signed URL/generated media byte committed, and this rehearsal is still not human acceptance, business validation, or durable memory promotion.
## 2026-06-10 - Web Workbench Acceptance Prep Cleanup
- Deleted retired Workbench renderers for old Job Center, old Creation Workspace, and old mixed Memory Workspace; current paths stay fixed on Operations, Studio/Storyboard, Review Room, and Project Memory.
- Updated `tools/workbench_vertical_flow_browser_smoke.py` for the current Chinese multi-workspace shell: expand diagnostics, set Runtime URL, switch to creation workspace, and wait on data-action/state instead of old English UI text.
- Reduced main-surface engineering leakage by collapsing asset profile seed / promotion fields behind `高级运行参数`, translating `ready_for_next_round` to `可进入下一轮`, and replacing smoke fixture copy with Chinese operator-facing text.
- Browser smoke reached `ready_for_next_round` with provider calls still not started; screenshot evidence is ignored under `data/processed/runs/workbench_browser_smoke/browser_evidence/`.
- Boundaries unchanged: no live provider call, no secret/private media/provider raw response/signed URL/generated media byte committed, and no human acceptance/business validation/durable memory claim.
