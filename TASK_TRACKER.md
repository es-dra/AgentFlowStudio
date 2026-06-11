# AgentFlow Studio 任务账本

最后更新：2026-06-11 by Codex

本文件只保留当前工作、下一步队列、阻塞项和证据入口。旧 Alpha、旧 Web
bridge、旧 demo 和旧逐节点 handoff 不再作为当前任务入口。

公司源头知识库：

```text
Company OS source knowledge base (local private path omitted)
```

AFS 仓库只保存执行投影：代码、contract、测试、runbook、维护账本和前端安全对接材料。

## 当前操作规则

- 不再新增编号式 memory advantage demo 模块。
- 不再恢复 `apps/web_bridge` 或 `web-bridge` CLI。
- provider smoke、deterministic tests、human acceptance、business validation、durable memory 必须分开。
- 不提交 secret、provider key、signed URL、cookie、本地媒体、模型缓存、生成 runtime artifact 或公司私密资料。
- 远程 provider 调用必须按能力显式 gate。

## 当前工作

| ID | Owner role | 范围 | 状态 | 证据 |
|---|---|---|---|---|
| AFS-MAINTENANCE-CLOSEOUT-001 | Maintainability Steward + Frontend Contract Steward | 强删旧 demo / Alpha / memory video pipeline / 旧 Web sample，调精维护审计，收紧当前 product spine | 已完成 | `docs/maintenance/AFS-MAINTENANCE-CLOSEOUT-001.zh-CN.md` |
| AFS-MAINTENANCE-DEBT-CLOSURE-001 | Architecture Reset Lead + QA / Release Gatekeeper | 解除剩余包级循环、收紧架构门禁、新增 CI 维护门禁 | 已完成 | `docs/maintenance/AFS-MAINTENANCE-DEBT-CLOSURE-001.zh-CN.md` |
| AFS-MODEL-GATEWAY-CYCLE-001 | Architecture Reset Lead | 解除 `agentflow_studio.model_gateway <-> agentflow_studio.production` 循环 | 已完成 | `docs/maintenance/AFS-MODEL-GATEWAY-CYCLE-001.zh-CN.md` |
| AFS-PRODUCT-SPINE-RESET-003 | Maintainability Steward + Architecture Reset Lead | 删除旧入口、压缩历史文档面、强化 retention review、消除旧包/CLI/Web surface | 已提交 | `docs/maintenance/AFS-PRODUCT-SPINE-RESET-003.zh-CN.md` |
| AFS-RUNTIME-SERVICE-V0-2-001 | Runtime/API Integrator + Frontend Contract Steward | Runtime Service、OpenAPI、frontend-safe refs、request fixture | 已合入基线 | `docs/frontend_integration/`；`docs/handoff/AFS-RUNTIME-SERVICE-V0-2-FRONTEND-CONTRACT-001.md` |
| AFS-LANDING-PREP-CONTENT-MEMORY-WEB-001 | AI-Native Operating Architect + Product / Engineering Orchestrator | 内容制作 / 记忆链路 Runtime Service 跑通证据、外部画布参考、Web 与后端协同开发规划 | 规划完成 | `docs/handoff/AFS-LANDING-PREP-CONTENT-MEMORY-WEB-001.md` |
| AFS-FRONTEND-WORKBENCH-INTEGRATION-001 | Product Integration Steward + Runtime/API Integrator | 外部画布前端接 Runtime Service，首屏只做 project、run、artifact、review safe view | 排队 | 前端不接触 CLI 内部、secret、私有路径、signed URL 或媒体字节 |
| AFS-WEB-REFOUNDATION-VERTICAL-001 | Product Integration Steward + Frontend Contract Steward + QA / Release Gatekeeper | 下狠手收敛 Web 首个可跑通生产纵切：剧本/目标输入 -> Runtime Service `/provider/script-draft-plan` -> 安全分镜 artifact -> 反馈复用 -> 浏览器 QA | 首轮已落地并通过 gate-closed 验证；等待人工体验复核和后续显式 provider gate | `docs/handoff/AFS-WEB-REFOUNDATION-VERTICAL-001.md`；`docs/maintenance/AFS-WEB-REFOUNDATION-CLEANUP-001.zh-CN.md` |
| AFS-WEB-CANVAS-EXPERIENCE-002 | Product Integration Steward + Frontend Interaction Designer + QA / Release Gatekeeper | 画布交互、显性资产架、2D 导演台、提示词优化器和状态反馈 v1 | 已落地并通过 focused tests + Runtime-hosted desktop/mobile browser QA；provider 仍关闭 | `docs/handoff/AFS-WEB-CANVAS-EXPERIENCE-002.md`；`docs/handoff/AFS-WEB-CANVAS-EXPERIENCE-002-BROWSER-QA.md`；`docs/maintenance/AFS-WEB-CANVAS-EXPERIENCE-002.zh-CN.md` |
| AFS-WEB-LIBTV-SHELL-RESET-003 | Product Integration Steward + Frontend Interaction Designer + QA / Release Gatekeeper | 用户侧 Web 产品壳层硬重置：只保留首页、创作画布、资产库；旧工程页和内部术语退出普通用户路径 | 已落地并通过 Runtime-hosted desktop/mobile browser QA；provider/MiniMax 仍未启动 | `docs/handoff/AFS-WEB-LIBTV-SHELL-RESET-003.md`；`data/processed/runs/libtv_shell_reset_003_browser_qa/browser_qa_report.json` |
| AFS-LIBTV-NODE-PROMPT-OPTIMIZER-INTEGRATION-001 | Runtime/API Integrator + Frontend Contract Steward | LibTV 节点提示词优化接 Runtime `prompt-optimizations`：Runtime 主路径、本地规则 fallback、安全 artifact refs、无显性记忆审核 UI | 已完成 Runtime/Web 对接和浏览器 QA；专业知识库位置已确认并由 `AFS-PROFESSIONAL-KNOWLEDGEBASE-PROMPT-ASSEMBLY-001` 落地 | `docs/handoff/AFS-LIBTV-NODE-PROMPT-OPTIMIZER-INTEGRATION-001.md`；`tests/test_api_runtime_prompt_memory_loop.py`；`tests/test_web_workbench_prompt_optimizer_browser_qa.py` |
| AFS-PROFESSIONAL-KNOWLEDGEBASE-PROMPT-ASSEMBLY-001 | Runtime/API Integrator + Knowledgebase Steward + QA / Release Gatekeeper | 专业影视提示词知识库双副本、规则检索/加权、中文槽位抽取、Prompt Assembly trace 与 safe manifest | 已完成 focused verification、浏览器 QA、full pytest、maintenance audit 和 diff check；provider 仍关闭 | `docs/handoff/AFS-PROFESSIONAL-KNOWLEDGEBASE-PROMPT-ASSEMBLY-001.md`；`agentflow/knowledge/`；`tests/test_agentflow_knowledgebase.py` |
| AFS-WEB-LIBTV-CANVAS-PROMPT-ONLY-006 | Frontend Interaction Designer + QA / Release Gatekeeper | 用户侧 Web 重置为 LibTV 风格画布；提示词记忆闭环保留在后台，只在 prompt 输入位暴露 `优化` | 已落地；画布头部、添加节点、提示词优化浮层、工具箱、画布交互、导演台 v3 和节点内本地预览反馈 QA 均通过，未启动 provider | `docs/handoff/AFS-WEB-LIBTV-CANVAS-PROMPT-ONLY-006.md`；`tools/workbench_libtv_canvas_header_browser_qa.py`；`tools/workbench_prompt_optimizer_browser_qa.py`；`tools/workbench_libtv_workflow_node_open_browser_qa.py` |
| AFS-WEB-LIBTV-DIRECTOR-TOPVIEW-006B | Frontend Interaction Designer + QA / Release Gatekeeper | LibTV-style Director Desk v3: 2D top-view editor, draggable camera/subject/lights/modifiers/props, apply-to-shot prompt context, and save-as-visible director setup asset | Landed with focused tests and Runtime-hosted browser QA on `http://127.0.0.1:8806/workbench/`; provider remains closed | `docs/handoff/AFS-WEB-LIBTV-CANVAS-PROMPT-ONLY-006.md`; `tools/workbench_libtv_director_interactions_browser_qa.py`; `data/processed/runs/workbench_libtv_director_interactions_browser_qa/workbench_libtv_director_interactions_browser_qa.json` |
| AFS-WEB-LIBTV-CANVAS-RELATION-VIEWPORT-006E-006G | Frontend Interaction Designer + QA / Release Gatekeeper | LibTV-style multi-select, relation focus, and viewport navigator | Landed: marquee batch toolbar, upstream/downstream/dimmed focus, MAP mini-map, fit view, center selected, reset viewport; provider remains closed | `apps/workbench/src/canvas-selection-actions.js`; `apps/workbench/src/canvas-relation-focus.js`; `apps/workbench/src/canvas-viewport-actions.js`; `tools/workbench_libtv_canvas_viewport_browser_qa.py` |

## 当前基线

| 模块 | 状态 | 证据 |
|---|---|---|
| Git | 当前 worktree 分支 `codex/afs-libtv-node-prompt-optimizer-integration-001` | `git status --short --branch` |
| Production Memory Asset Loop | deterministic 本地 contract chain 已具备 | `agentflow/memory/`；`apps/cli/production_memory_command_registry.py` |
| Runtime Service | 前端主对接面 | `apps/api/`；`apps/cli/runtime_service_command.py` |
| 过渡 Web | 只保留 read-only / local-only artifact viewer | `apps/web/README.md` |
| 维护审计 | 本地维护审计和 retention review 可运行 | `tools/maintenance_audit.py`；`tools/repository_retention_review.py` |

## 下一步队列

| ID | 范围 | 状态 |
|---|---|---|
| AFS-FLOW-RUN-READY-001 | 基于当前低成本维护基线，进入自研轻量 Web 前的流程跑通准备 | 已完成首轮 Runtime Service 链路证据；下一步补 workbench-state adapter |
| AFS-WORKBENCH-STATE-ADAPTER-001 | Web 实现前补 Runtime Service UI state、canvas card、blocker、action vocabulary、event history 和 safe preview contract | 已完成首轮实现；`tests/test_api_runtime_workbench_state.py` |
| AFS-WEB-FOUNDATION-001 | 新自研轻量 Web 基础：runtime client、state adapter、app shell、project hub、workspace layout、Runtime-hosted entry | 已完成基础壳；`apps/workbench`、`/workbench/`、`tests/test_web_workbench_foundation.py` |
| AFS-WEB-PROJECT-SETUP-001 | Project Hub / setup / asset-reference library：项目创建、导入导出、目标平台、素材和参考入口 | 进行中：create/open/import/export、asset/reference library、source presets 和 Draft Canvas 入口已落地 |
| AFS-WEB-CREATION-WORKSPACE-001 | 创作画布主工作区：scene/content cards、inspector、filmstrip、first generation check | 进行中：Draft Canvas、scene/content cards、Inspector、filmstrip、first generation check control、safe artifact panel 和 Review Room candidate comparison 已落地 |
| AFS-WEB-REVIEW-STYLE-MEMORY-001 | 审片反馈与 Project Style Memory：keep/revise/reject、raw feedback、下一轮复用 | 进行中：raw feedback、keep/revise/reject、candidate-bound review decisions、Style Memory product view 和 next-round controls 已落地 |
| AFS-PROVIDER-GATED-REAL-SMOKE-001 | deterministic Web flow 稳定后，再按 capability gate 接真实模型 smoke | readiness-only gate 已跑通并写入 ignored runtime evidence：`data/processed/runs/web_rc_provider_gate_readiness/`；provider calls 未启动；仍需先完成人工验收，再由用户显式授权 image/video gate |
| AFS-WEB-QA-RELEASE-GATE-001 | 浏览器截图、响应式检查、HTTP smoke、focused tests、maintenance audit、diff check | 发布候选 QA 已完成：Stage 7 浏览器主路径、1440x900 / 1366x768 / 390x844 截图、console/internal-leak/text-overflow 检查和 provider-gated 边界记录已落地 |
| AFS-WEB-HUMAN-ACCEPTANCE-001 | 人工验收当前 Web release candidate，确认项目 -> 素材 -> 画布 -> 分镜 -> 审片 -> 记忆 -> 任务路径是否符合低学习成本创作工作台定位 | 待人工验收：验收包、可视化演示索引、draft PR handoff 已落地；验收前浏览器演练已通过自动连接和 8 个工作区切换，但仍不等于人工验收 |
| AFS-WEB-LIBTV-RESOURCE-ENTRY-001 | LibTV 添加资源入口：上传素材 / 从生成历史选择的本地安全投影 | 已完成 TDD、HTTP 资源检查、全量 pytest 和本地 Playwright 点击 QA；manifest `data/processed/runs/workbench_libtv_add_node_state_browser_qa/workbench_libtv_add_node_browser_qa.json` 覆盖 `resource_upload` / `resource_history`，selector 可见、console/page errors `0`、forbidden matches `[]`、provider_request_urls `[]` |
| AFS-WEB-REFOUNDATION-VERTICAL-001 | Web 创作台首个真实生产纵切：剧本/目标输入、目标时长、风格、LLM gate 提示、分镜计划 artifact、反馈和上一版 artifact 复用 | 首轮已落地：focused Web/API `26 passed, 1 warning`；全量 pytest `871 passed, 1 warning`；浏览器 QA `qa_status=passed`；`maintenance_audit` `failed=0, passed=6, warning=0`；仍不是 human acceptance 或真实 provider smoke |
| AFS-LIBTV-NODE-PROMPT-OPTIMIZER-INTEGRATION-001 | Web 画布提示词优化按钮接 Runtime `prompt-optimizations`，本地规则仅作 fallback；专业知识库位置已确认并进入后台规则主路径 | 已完成 Runtime/Web/LibTV focused、真实浏览器 QA、全量 pytest、维护审计和 diff check；知识库后台核心由 `AFS-PROFESSIONAL-KNOWLEDGEBASE-PROMPT-ASSEMBLY-001` 收口 |

## 当前阻塞和残留

- `maintenance_audit` 的 secret-like warning 和 oversized warning 已清零；后续触碰模块时仍按 300 行理想线继续拆分。
- Hidden CLI support commands 仍是兼容支持面；删除前必须做独立 CLI 协议迁移。
- Provider validation 默认关闭，除非显式授权对应 capability gate。
- 维护审计当前为通过状态；新的前端模块仍按单职责和 300 行理想线维护。
- 当前 Web release candidate 还没有人工验收结论；不得把 Stage 7 浏览器 QA 说成 human acceptance。
- Provider smoke 准备包已落地，但尚未执行；不得把 readiness-only plan 说成真实模型接入成功。
- LibTV 添加资源入口已是本地安全投影，不等于真实上传、真实历史读取或生成资产复用验收。
- 本轮 Web refoundation 只启动 LLM/script 的 gate-closed 文本分镜纵切；图片、三视图、I2V 和视频片段生成仍需独立 provider gate、契约和 QA。


## 历史任务归档

- 2026-06-09 到 2026-06-10 的 Web foundation / RC / provider-prep 长记录已下沉到对应 handoff、maintenance 和 archive 文档；当前任务账本只保留活跃基线、阻塞项和 LibTV 006 系列收口记录。

## AFS-WEB-LIBTV-CANVAS-INTERACTIONS-006A

- Scope: extended `AFS-WEB-LIBTV-CANVAS-PROMPT-ONLY-006` from static LibTV-like layout into real canvas behavior.
- Landed: empty-canvas pan, double-click node creation menu, floating custom nodes, damped node dragging with snap, dynamic Bezier pending/connected edges, selected-linked highlighting, and long-press marquee multi-select.
- Evidence: `python tools\workbench_libtv_canvas_interactions_browser_qa.py --base-url http://127.0.0.1:8806/workbench/` passed; full `python -m pytest -q` passed with `886 passed`.
- Boundary: no provider call, no MiniMax call, no secret or raw provider response exposed.
- Follow-up: split `apps/workbench/src/canvas-interactions.js` below 300 lines if this interaction layer grows further.

## AFS-WEB-LIBTV-DIRECTOR-TOPVIEW-006B

- Scope: moved the Director Desk user path from static layout toward a LibTV-style canvas editor node.
- Landed: `renderDirectorFlowV3`, 2D top-view stage, draggable camera/subject/lights/modifiers/props, selected-object panel sync, clamped stage bounds, apply-to-shot prompt context, and save-as-visible `director_setup` asset.
- Evidence: `python tools\workbench_libtv_director_interactions_browser_qa.py --base-url http://127.0.0.1:8806/workbench/` passed; `python tools\workbench_libtv_add_node_browser_qa.py --base-url http://127.0.0.1:8806/workbench/ --viewport desktop` passed; focused Web tests `18 passed`; full pytest `888 passed`; `maintenance_audit` `failed=0, warning=1`; `git diff --check` passed with CRLF warnings only.
- Boundary: no provider call, no MiniMax call, no secret, signed URL, local private asset path, provider raw response, or generated media byte exposure.

## AFS-WEB-LIBTV-WORKFLOW-NODE-OPEN-006C

- Scope: made the default AFS workflow nodes behave like independently operable LibTV canvas nodes instead of static cards.
- Landed: stable workflow-node kind mapping, `data-open-node-kind`/`data-opened-node-id`, reversible topbar return action, node open/create state transitions in `studio-node-actions.js`, and prompt-card repositioning so selection feedback no longer blocks adjacent node actions.
- Evidence: `python tools\workbench_libtv_workflow_node_open_browser_qa.py --base-url http://127.0.0.1:8806/workbench/` passed across all 8 default workflow nodes; `python tools\workbench_libtv_canvas_interactions_browser_qa.py --base-url http://127.0.0.1:8806/workbench/` passed after the node-card repositioning; `python tools\workbench_libtv_director_interactions_browser_qa.py --base-url http://127.0.0.1:8806/workbench/` passed; `python tools\workbench_libtv_add_node_browser_qa.py --base-url http://127.0.0.1:8806/workbench/ --viewport desktop` passed; focused Workbench tests `20 passed`; full pytest `888 passed`; `maintenance_audit` `failed=0, warning=1`; `git diff --check` passed with CRLF warnings only.
- Boundary: no provider call, no MiniMax call, no secret, signed URL, local private asset path, provider raw response, or generated media byte exposure.

## AFS-WEB-LIBTV-GROUP-DRAG-EDGE-PORTS-006D-006I

- Scope: improved the canvas from static node arrangement toward a real node editor interaction model.
- Landed: selected-node group drag, visible input/output node ports, output-to-input Bezier anchoring, connection target magnet behavior, `target-locked` pending styling, success-ripple edge state, and persistent directional edge flow.
- Evidence: canvas interactions browser QA passed with visible source/target ports, `pending_target_locked=true`, `target_highlight_during_drag=true`, `success_ripple_count=1`, `connected_edge_animation=edge-flow, edge-idle-flow`, and another selected node moving during group drag; adjacent browser QA passed; focused Workbench tests `14 passed`.
- Boundary: no provider call, no MiniMax call, no secret, signed URL, local private asset path, provider raw response, or generated media byte exposure.

## AFS-WEB-LIBTV-MULTISELECT-BATCH-006E

- Scope: made marquee selection visibly actionable instead of only highlighting nodes.
- Landed: selection bounding frame, floating batch toolbar, duplicate, align row/column, safe delete for custom nodes, and clear selection through `canvas-selection-actions.js`.
- Evidence: canvas interactions browser QA passed with `toolbar_visible=true`, `frame_visible=true`, `align_row_applied=true`, `duplicate_increased_node_count=true`, and `delete_restored_node_count=true`; focused Workbench tests `20 passed`; full pytest `888 passed`; `maintenance_audit` `failed=0, warning=0`.
- Boundary: provider/MiniMax remained closed; no secrets, provider raw response, signed URL, local private media path, or generated media bytes were exposed.

## AFS-WEB-LIBTV-RELATION-VIEWPORT-NODE-CONTROL-006F-006L

- Scope: made click selection, viewport movement, node opening, graph-context navigation, node-local controls, and edge selection explain and recover the canvas graph instead of leaving users lost in a large world or isolated node panel.
- Landed: `canvas-relation-focus.js` for selected/upstream/downstream/dimmed roles, `canvas-viewport-actions.js` for MAP mini-map/fit/center/reset, `render-studio-node-context.js` for clickable upstream/current/downstream chips, prompt-node local generation feedback in `render-node-prompt.js`, and a selected-edge toolbar for centering endpoints or disconnecting custom links.
- Evidence: relation-focus, canvas-viewport, workflow-node-open, and canvas-interactions QA passed with selected role, direct upstream/downstream counts, dimmed node/edge counts, mini-map viewport, fit transform, selected-node centering, opened node context id/kind/chains, node generation status moving to `complete`, downstream context navigation from `script-input` to `storyboard`, and edge toolbar evidence `toolbar_visible=true`, `edge_selected=true`, `disconnect_removed_edge=true`; no console/page errors and no provider requests.
- Boundary: provider/MiniMax remained closed; no secrets, provider raw response, signed URL, local private media path, or generated media bytes were exposed.

## AFS-WEB-LIBTV-NODE-PARAM-CONTROLS-006M

- Scope: made LibTV-style node parameter chips behave as real per-node controls instead of static decorative labels.
- Landed: `studio-node-control-state.js`, unified `data-node-control` handling, active/pressed state styling, and stateful controls for text/script attempts, image modes/specs, video modes/specs/toggles, and audio target/mode/voice/spec controls.
- Evidence: workflow-node-open browser QA passed with node-control activation for text, script, image, and video workflow nodes; add-node desktop browser QA passed with node-control activation for text, image, video, audio, and script, and text-node overflow reduced to zero; full pytest `889 passed`; `maintenance_audit` `failed=0, warning=1` only for long-running `DEVLOG.md` / `TASK_TRACKER.md`; `git diff --check` passed with CRLF warnings only.
- Boundary: provider/MiniMax remained closed; controls update local UI state only and do not start model generation or expose backend memory internals.

## AFS-WEB-LIBTV-NODE-TRANSITIONS-006N

- Scope: added spatial feedback between the infinite canvas and opened node panels so node open, graph-chain navigation, and return-to-canvas feel connected to the canvas rather than like a hard page swap.
- Landed: `nodeOpenTransition` state, `nodeOpenTransitionForCanvas`, node panel `enter` animation, context-chip `chain` swap animation, return-to-canvas node pulse, edge-flow restart on return, compact director v3 desktop sizing, and add-resource menu close behavior after choosing upload/history.
- Evidence: workflow-node-open browser QA passed with all 8 workflow nodes using `enter` / `node-enter-from-canvas`, script-to-storyboard context navigation using `chain` / `node-chain-swap`, and return-to-canvas using `return` / `canvas-node-return`; add-node browser QA passed on desktop/tablet/mobile, including desktop director/add-resource overflow fixes; focused Web tests `9 passed`; full pytest `889 passed`; `maintenance_audit` `failed=0, warning=1` only for long-running `DEVLOG.md` / `TASK_TRACKER.md`; `git diff --check` passed with CRLF warnings only.
- Boundary: provider/MiniMax remained closed; transitions are local UI state only and do not start model generation or expose backend memory internals.

## AFS-WEB-LIBTV-MOBILE-NODE-WORKSPACE-006O

- Scope: made opened LibTV-style node panels usable on tablet/mobile instead of only passing desktop QA.
- Landed: `styles-studio-mobile-node-workspace.css` loaded after the LibTV shell, compact topbar, compact 12-column bottom dock, wrapped node context bar, node panel width clamp, scrollable node-detail stage, single-column parameter grids, tablet/mobile video-merge/director layout fixes, director top-view object compaction, and stronger return animation rule.
- Evidence: add-node browser QA now fails on visible text/control overflow for every viewport; after the fix it passed on desktop/tablet/mobile with all node/resource cases reporting `overflow_node_count=0`; workflow-node-open browser QA passed with enter/chain/return animations intact; focused Web tests `9 passed`; full pytest `889 passed`.
- Boundary: provider/MiniMax remained closed; this is a front-end responsive/workspace interaction slice only.

## AFS-WEB-LIBTV-CANVAS-USABILITY-006P

- Scope: tightened the canvas from a visually similar shell into a more usable node editor surface.
- Landed: selected/dragging workflow nodes now stay above the bottom dock, workflow canvas has a bottom safe band, add-node QA dynamically drags a node into the dock area to verify it remains operable, and image/video/audio node panels show a live current-setting summary that updates when local controls are clicked.
- Evidence: canvas-interactions browser QA passed with bottom-safe drag evidence `selected_node_above_dock=true`, Bezier pending/connected edges, connection target lock, success ripple, edge toolbar, marquee multi-select, group drag, duplicate/align/delete; add-node browser QA passed on desktop/tablet/mobile with image/video/audio `summary_changed=true`; workflow-node-open browser QA passed across all 8 default workflow nodes.
- Boundary: provider/MiniMax remained closed; this is local UI state and browser verification only, not provider smoke, human acceptance, or durable memory promotion.

## AFS-WEB-LIBTV-CANVAS-INTERACTION-SAFETY-006Q

- Scope: tightened the LibTV-style canvas from z-index-based operability toward real geometry-safe interaction.
- Landed: connected Bezier edges now follow dragged nodes during pointer movement; node drag end calculates the visible work area from the topbar and bottom dock and pans the canvas so selected nodes do not intersect the dock; browser QA now fails on geometric bottom-dock overlap instead of accepting a higher z-index.
- Evidence: `python tools\workbench_libtv_canvas_interactions_browser_qa.py --base-url http://127.0.0.1:8806/workbench/` passed with `selected_node_clear_of_dock=true`, node bottom `912`, dock top `930`, Bezier pending/connected edges, target lock, success ripple, edge toolbar, marquee multi-select, group drag, duplicate/align/delete; `python tools\workbench_libtv_canvas_viewport_browser_qa.py --base-url http://127.0.0.1:8806/workbench/` passed with mini-map, fit-view, center-selection, reset, no horizontal overflow, and no provider requests.
- Boundary: provider/MiniMax remained closed; this is front-end interaction state and Runtime-hosted browser verification only, not provider smoke, human acceptance, business validation, or durable memory promotion.

## AFS-WEB-LIBTV-VIDEO-MOTION-CONTROLS-006R

- Scope: made the video node's `运镜` area a real per-node setting panel instead of a decorative LibTV-like label.
- Landed: animated motion preview, camera movement controls, movement strength, subject action, rhythm controls, and live summary rows synchronized with local node-control state.
- Evidence: add-node browser QA passed on desktop/tablet/mobile with `video_motion.panel_visible=true`, `clicked=true`, `active=true`, and `summary_mentions_value=true`; workflow-node-open QA passed for the `clip` workflow node with the new motion summary rows; canvas-interactions QA passed with pan, double-click creation, bottom-dock-safe drag, pending/connected Bezier edges, marquee multi-select, group drag, and edge toolbar.
- Final gates: full `python -m pytest -q` passed with `890 passed`; `maintenance_audit` reported `failed=0` and one known long-record warning; `git diff --check` passed with Windows line-ending warnings only.
- Boundary: provider/MiniMax remained closed; no secret, signed URL, local private media path, provider raw response, generated media byte, or prompt-memory internals were exposed.
