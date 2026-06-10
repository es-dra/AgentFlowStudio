---
doc_type: web_rc_freeze_closeout
status: engineering_rc_pending_human_acceptance
last_updated: 2026-06-10
owner_role: Engineering Delivery Lead
provider_gate: closed
writes_company_kb: false
---

# AFS Web RC Freeze Closeout - 2026-06-10

## 中文摘要

本文件是当前 Web Workbench 工程候选版本的冻结收口记录。它的用途不是继续定义新功能，而是把当前分支的真实状态一次性讲清楚：哪些文件属于本轮工作，哪些文件只是被删除或归档，哪些模块已经接近维护线，哪些浏览器证据和测试证据可以支撑工程候选版本进入人工验收。当前界面的目标是让使用者先理解项目入口、创作画布、节点状态、素材和历史入口、工具箱、执行意图、审片、项目记忆、任务中心和 Provider Gate，而不是要求使用者理解全部 Company OS 概念。所有自动化结果都只代表运行时验证；它们不能替代人工验收，也不能替代真实 provider smoke、商业验证或长期记忆晋升。本阶段的核心判断是：停止继续横向复刻 LibTV 的更多功能，先冻结一个本地安全、可操作、可验收的工作台，再用最小 provider 纵切验证 AFS 自己的差异化链路。

本文件还明确记录了下一步 provider 接入的顺序。第一条纵切建议从脚本和分镜文本开始，因为文本产物更容易检查、脱敏、复用和回滚；图片能力应作为第二步，视频能力应作为第三步。视频生成涉及异步任务、成本、失败恢复、媒体字节、质量判断和人工审片，过早接入会把多个风险一次性叠加。当前仓库只保存执行投影和项目本地证据，不保存公司源头知识库内容，不写入密钥、签名链接、本地私有素材、provider 原始响应或生成媒体字节。这里形成的 Company OS 经验只作为候选反馈，必须等待用户审阅，不能自动晋升为 active rule。

阅读本文件时应按三个层次理解。第一层是工程事实：当前工作树中有哪些修改、删除和新增文件，哪些新增文件归属于本轮 Web Workbench，哪些测试和浏览器脚本负责证明主路径可运行。第二层是产品事实：当前界面已经具备低学习成本入口和本地安全创作骨架，但仍未经过用户人工验收，因此不能把自动化结果说成产品通过。第三层是规则事实：本阶段产出的复盘只进入候选反馈，不写入公司源头知识库，不形成长期记忆，也不改变 provider gate 的默认关闭状态。这个分层能防止后续工作把工程可运行、用户接受、模型接入成功、商业有效和规则晋升混成同一个结论。

本收口文档有意保留大量路径和命令，因为后续代理需要直接复跑证据，但这些路径和命令只是定位信息。真正的判断口径是中文描述中的边界：主界面不得暴露内部标识、本地路径、密钥、签名链接、provider 原始响应或生成媒体字节；诊断层可以保留安全引用和内部状态；浏览器截图和清单可以证明界面在本地运行，但不能证明真实 provider 质量；审片反馈可以成为下一轮候选约束，但不能自动成为 durable memory。后续如果要继续推进，应该先让人完成验收，再按最小纵切打开明确的 LLM gate，而不是在未验收的横向 UI 上继续堆功能。

## 1. Freeze Decision

当前阶段从“继续扩展 LibTV 复刻”切换为“冻结 Web RC + 准备 provider 纵切”。

本阶段不再新增 LibTV 功能面，只处理以下类型问题：

- blocker 或 major UX 问题。
- 可见泄漏：raw project id、本地路径、secret、signed URL、provider raw response、generated media bytes。
- 移动端遮挡、横向溢出、按钮不可触达。
- focused tests、full pytest、maintenance audit、browser QA 或 `git diff --check` 失败。

当前结论是工程 RC，不是人工验收结论、provider smoke、business validation 或 durable memory promotion。

## 2. Worktree Closeout Audit

### Modified

- `DEVLOG.md`
- `TASK_TRACKER.md`
- `apps/workbench/README.md`
- `apps/workbench/index.html`
- `apps/workbench/src/app.js`
- `apps/workbench/src/display-labels.js`
- `apps/workbench/src/render-project-hub.js`
- `apps/workbench/src/render-studio-canvas.js`
- `apps/workbench/src/render-studio-inspector.js`
- `apps/workbench/src/render-studio-workspace.js`
- `apps/workbench/src/render.js`
- `apps/workbench/src/state.js`
- `apps/workbench/styles-app-shell.css`
- `apps/workbench/styles-project-hub.css`
- `apps/workbench/styles-studio-canvas-v2.css`
- `apps/workbench/styles-studio-workspace.css`
- `docs/frontend_integration/AFS_WEB_RELEASE_CANDIDATE_ACCEPTANCE_PACKET.zh-CN.md`
- `docs/frontend_integration/AFS_WEB_UX_QA_LEDGER.zh-CN.md`
- `tests/test_web_workbench_foundation.py`
- `tests/test_web_workbench_studio.py`
- `tests/test_web_workbench_vertical_flow.py`

### Deleted

- `apps/workbench/styles-studio-canvas-focus.css`

Deletion decision: intentional retirement of the old canvas focus stylesheet. The current Workbench path uses split Studio/LibTV canvas styles instead, and the foundation tests cover that the retired stylesheet is no longer referenced.

### Untracked - Workbench Source Modules

- `apps/workbench/src/canvas-interactions.js`
- `apps/workbench/src/project-showcase-data.js`
- `apps/workbench/src/render-project-showcase.js`
- `apps/workbench/src/render-studio-add-node-flow.js`
- `apps/workbench/src/render-studio-audio-node-flow.js`
- `apps/workbench/src/render-studio-canvas-header.js`
- `apps/workbench/src/render-studio-execution-scaffold.js`
- `apps/workbench/src/render-studio-history.js`
- `apps/workbench/src/render-studio-panels.js`
- `apps/workbench/src/render-studio-resource-entry.js`
- `apps/workbench/src/render-studio-starter-flows.js`
- `apps/workbench/src/render-studio-toolbox.js`
- `apps/workbench/src/render-studio-video-node-flow.js`
- `apps/workbench/src/studio-canvas-header-events.js`
- `apps/workbench/src/studio-mode.js`

Classification: all belong to the current Web Workbench RC. They are split renderer/state/event modules for project portal, LibTV-style canvas, safe local node states, resource entry, history, toolbox, execution intent, canvas header, and mode control.

### Untracked - Workbench Styles

- `apps/workbench/styles-project-directory.css`
- `apps/workbench/styles-project-drawer.css`
- `apps/workbench/styles-project-showcase.css`
- `apps/workbench/styles-studio-add-node-flow.css`
- `apps/workbench/styles-studio-audio-node-flow.css`
- `apps/workbench/styles-studio-audio-video-flow.css`
- `apps/workbench/styles-studio-canvas-header.css`
- `apps/workbench/styles-studio-canvas-panels.css`
- `apps/workbench/styles-studio-character-flow.css`
- `apps/workbench/styles-studio-director-merge-flow.css`
- `apps/workbench/styles-studio-execution-scaffold.css`
- `apps/workbench/styles-studio-image-video-flow.css`
- `apps/workbench/styles-studio-resource-entry.css`
- `apps/workbench/styles-studio-script-generator-flow.css`
- `apps/workbench/styles-studio-starters.css`
- `apps/workbench/styles-studio-text-node-flow.css`
- `apps/workbench/styles-studio-toolbox.css`
- `apps/workbench/styles-studio-utility-panels.css`
- `apps/workbench/styles-studio-video-node-flow.css`

Classification: all belong to the current Web Workbench RC. The split is intentional to keep canvas, portal, node flows, toolbox, resource entry, and execution scaffold below maintenance pressure.

### Untracked - Tests

- `tests/test_web_workbench_libtv_add_node_flows.py`
- `tests/test_web_workbench_libtv_audio_add_node_flow.py`
- `tests/test_web_workbench_libtv_browser_qa.py`
- `tests/test_web_workbench_libtv_canvas_header.py`
- `tests/test_web_workbench_libtv_canvas_header_browser_qa.py`
- `tests/test_web_workbench_libtv_execution_scaffold.py`
- `tests/test_web_workbench_libtv_mobile_layout.py`
- `tests/test_web_workbench_libtv_resource_entries.py`
- `tests/test_web_workbench_libtv_toolbox_browser_qa.py`
- `tests/test_web_workbench_libtv_toolbox_skeleton.py`

Classification: all belong to the current Web Workbench RC. They cover the local safe LibTV-style skeleton, node/resource states, toolbox, canvas header, execution scaffold, mobile layout, and browser QA script contracts.

### Untracked - Browser QA Tools

- `tools/workbench_libtv_add_node_browser_qa.py`
- `tools/workbench_libtv_canvas_header_browser_qa.py`
- `tools/workbench_libtv_execution_scaffold_browser_qa.py`
- `tools/workbench_libtv_toolbox_browser_qa.py`

Classification: all belong to the current Web Workbench RC. They provide repeatable Playwright evidence for desktop, tablet, and mobile viewports.

### Untracked - Documentation

- `docs/archive/DEVLOG-2026-06-09-web-foundation-archive.md`

Classification: belongs to the current Web Workbench cleanup. It archives older long-form Web foundation/devlog material so `DEVLOG.md` remains a current entrypoint.

## 3. Maintainability Audit

Line-count scan across `apps/workbench`, `tests`, and `tools` found no file above 300 lines.

Near-threshold files:

| Lines | Path | Decision |
|---:|---|---|
| 300 | `tests/test_web_workbench_foundation.py` | Accept for RC freeze; do not split unless the next edit adds new assertions. |
| 291 | `apps/workbench/src/display-labels.js` | Accept for RC freeze; next label expansion should split by domain. |
| 290 | `tests/test_web_workbench_studio.py` | Accept for RC freeze; no split without new coverage. |
| 287 | `apps/workbench/src/app.js` | Accept for RC freeze; already under the maintenance line. |
| 282 | `apps/workbench/src/render-studio-add-node-flow.js` | Accept for RC freeze; the flow-specific submodules are already split. |
| 262 | `apps/workbench/styles-project-showcase.css` | Accept. |
| 261 | `tools/workbench_libtv_execution_scaffold_browser_qa.py` | Accept. |
| 259 | `apps/workbench/styles-studio-canvas-panels.css` | Accept. |
| 255 | `apps/workbench/src/render-project-hub.js` | Accept. |
| 254 | `apps/workbench/styles-project-hub.css` | Accept. |
| 249 | `apps/workbench/styles-studio-character-flow.css` | Accept. |
| 248 | `tools/workbench_libtv_add_node_browser_qa.py` | Accept. |
| 248 | `tools/workbench_libtv_toolbox_browser_qa.py` | Accept. |
| 247 | `apps/workbench/src/render-studio-starter-flows.js` | Accept. |
| 244 | `tests/test_web_workbench_libtv_add_node_flows.py` | Accept. |
| 242 | `apps/workbench/styles-studio-canvas-v2.css` | Accept. |

RC decision: no mandatory split now. The next edit touching `tests/test_web_workbench_foundation.py`, `display-labels.js`, or `tests/test_web_workbench_studio.py` should prefer a responsibility split before adding bulk.

## 4. RC Capability Map

| User-facing requirement | Current status | Evidence boundary |
|---|---|---|
| User can understand the project entry | Present | Projects portal, project directory, start creation entry, showcase detail; not human acceptance. |
| User can operate a creation canvas | Present | LibTV-style canvas, pan/zoom, bottom dock, add node, resource/history/toolbox panels; local-only. |
| Nodes, assets, history, toolbox, execution intent are locally safe | Present | Node/resource/tool/execution intent receipts state local registration, no task creation, no provider start. |
| Review, project memory, task center, Provider Gate main path exists | Present from Stage 7 RC | Review Room, Project Memory, Jobs/Task Center, Provider preflight are product surfaces; provider stays closed. |
| No visible raw id/path/secret/provider/raw media leak | Covered by browser QA scripts and focused assertions | Diagnostics may expose safe refs; main creative surfaces should not. |
| Verification boundaries are explicit | Present in acceptance packet, QA ledger, task tracker, and this closeout | Runtime verification remains separate from human acceptance, provider smoke, business validation, and durable memory. |

## 5. Reference-only vs AFS Product Objects

Reference-only LibTV material:

- Real LibTV screenshots, DOM extracts, menu labels, and node-control observations.
- LibTV account/login/payment/community surfaces.
- LibTV provider/model names such as GVLM, Lib Image, and Seedance as UI reference labels only.
- LibTV generated content, uploaded media, or provider behavior. These were not copied into AFS as validated provider capability.

AFS product objects:

- Project portal and project directory as low-learning-cost entry points.
- Local creation canvas with nodes, assets, history, toolbox, canvas header, and execution intent.
- Review Room, Project Memory, Task Center, Provider Gate, and Settings/Diagnostics as first-class AFS work areas.
- Evidence chain and boundary copy: local intent, no real task, provider not started, candidate memory not durable memory.

## 6. Final QA Checklist

Final QA is run after this freeze record is written.

| Gate | Command | Status |
|---|---|---|
| Focused Workbench tests | `.\.venv\Scripts\python.exe -m pytest ... -q` | passed: `34 passed` |
| Full pytest | `.\.venv\Scripts\python.exe -m pytest` | passed: `868 passed, 1 warning` |
| Maintenance audit | `.\.venv\Scripts\python.exe tools\maintenance_audit.py` | passed: `failed=0, passed=6, warning=0` |
| Diff check | `git diff --check` | passed with Windows CRLF normalization warnings only |
| CLI help | `.\.venv\Scripts\python.exe -m apps.cli.main --help` | passed |
| CLI version | `.\.venv\Scripts\python.exe -m apps.cli.main version` | passed: `0.1.0` |
| Browser QA: add node/resource | `.\.venv\Scripts\python.exe tools\workbench_libtv_add_node_browser_qa.py --base-url http://127.0.0.1:8790/workbench/` | passed: `qa_status=passed`, `provider_request_urls=[]` |
| Browser QA: toolbox | `.\.venv\Scripts\python.exe tools\workbench_libtv_toolbox_browser_qa.py --base-url http://127.0.0.1:8790/workbench/` | passed: `qa_status=passed`, `provider_request_urls=[]` |
| Browser QA: execution scaffold | `.\.venv\Scripts\python.exe tools\workbench_libtv_execution_scaffold_browser_qa.py --base-url http://127.0.0.1:8790/workbench/` | passed: `qa_status=passed`, `provider_request_urls=[]` |
| Browser QA: canvas header | `.\.venv\Scripts\python.exe tools\workbench_libtv_canvas_header_browser_qa.py --base-url http://127.0.0.1:8790/workbench/` | passed: `qa_status=passed`, `provider_request_urls=[]` |

## 7. Provider Vertical Slice Plan

Recommended first vertical slice: LLM/script, not image or video.

Minimum path:

1. User enters a goal in Workbench.
2. Runtime creates an explicit LLM provider request only when `AFS_ALLOW_REMOTE_LLM=true`.
3. Provider response is reduced to safe script/storyboard text artifact and safe manifest.
4. UI shows the safe artifact in the script/storyboard node, not provider raw response.
5. Review Room records keep/revise/reject feedback.
6. Second round uses the feedback as candidate constraints, still without durable memory promotion.

Why LLM/script first:

- Text artifacts are easier to diff, inspect, redact, and store safely.
- Failure recovery is simpler than image/video generation.
- Cost, async orchestration, retry policy, and quality judgment are smaller than video.
- It directly exercises the AFS-native loop: goal -> artifact -> review -> feedback reuse -> evidence.

Second vertical slice: image provider, after the script artifact contract and review feedback reuse are stable.

Third vertical slice: video provider, after async task lifecycle, cost guard, failure recovery, media-byte handling, and quality review contract are isolated.

## 8. Residual Risks

- Human acceptance is still pending. Browser QA proves runtime verification only.
- Several files are near the 300-line maintenance line; future feature additions should split before expanding.
- LibTV-derived labels remain reference labels, not provider capability claims.
- Provider smoke has not run; no real model integration is validated.
- Business validation has not started; no claim about production value or customer fit.
- Candidate feedback is not durable memory or active Company OS rule.

## 9. Stage Closeout

Engineering Delivery Lead:

- Freeze current Web Workbench as an engineering RC.
- Stop horizontal LibTV expansion.
- Move next engineering work to final QA, human acceptance support, and LLM/script provider vertical slice planning.

Evidence Reviewer:

- Treat all Playwright and pytest results as runtime verification evidence only.
- Keep screenshots and JSON manifests under `data/processed/runs/...` as ignored evidence artifacts.
- Do not use QA pass as a substitute for human acceptance, provider smoke, business validation, or durable memory promotion.

Rule Steward:

- Candidate lesson: when replicating an external product, first land the low-learning-cost functional skeleton and safe local states, then gradually surface AFS-native evidence/quality/memory/provider-gate differences.
- Do not auto-promote this lesson into active Company OS rules.
- Route candidate feedback through the project-local packet: `docs/frontend_integration/AFS_WEB_RC_COMPANY_OS_FEEDBACK_2026-06-10.zh-CN.md`.

Company OS feedback: `docs/frontend_integration/AFS_WEB_RC_COMPANY_OS_FEEDBACK_2026-06-10.zh-CN.md`
