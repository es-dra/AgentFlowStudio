# Devlog

中文摘要：本文件只保留当前阶段的短记录和验证入口，不再承载旧 Web、旧 Workbench 或历史浏览器 QA 的长流水。当前判断以 Studio、Runtime Service、知识库、创作智能体和 provider gate 为主线；测试通过只代表工程验证，不代表人工验收、商业验证或长期记忆晋升。后续如果某条记录不再支持当前 MVP、真实模型接入或维护收口，应直接删除，避免把过期资料继续带入主线。

当前状态：本轮收口已经把旧 Workbench、旧静态 Web、过期前端对接包和旧浏览器 QA 记录移出主线，同时补上创作意图控制智能体、关键帧生成 gate、Studio 静态入口和 OpenAPI 契约。后续记录只写影响当前落地的验证结果、阻塞项和真实模型接入证据，不再追加无明确后续用途的过程叙事。

Status: short current-session log. Historical long narratives are not current
product documentation.

## 2026-06-12 - AFS Asset Context S1

- Created isolated branch/worktree `codex/afs-asset-context-s1`.
- Added `visual_asset v0.1` Runtime storage and promote/list/retire APIs.
- Stopped prompt-background placeholder pollution: `Primary character` / `Primary scene` no longer create records, and extracted context stays candidate-only.
- Added `context_subgraph v0.1` and `context_bundle v0.1`; prompt optimization and keyframe generation now share the resolver when a subgraph is supplied.
- Split optimize/generate views: optimize injects only connected or label-matched signatures, generate consumes only connected fixed assets.
- Added request-level temporary lock overrides and unconditional negative-lock injection for non-overridden locks.
- Kept no-subgraph keyframe requests on the old `asset_refs` path for compatibility.
- Added `generation_comparison_report v0.1` with fixed A/B/C arm definitions.
- Added one-click connect for named unconnected assets, request-level temporary unlock, and reproducible gate-closed browser QA in `tools/studio_asset_context_browser_qa.py`.
- Browser QA drives upload -> fixed asset -> optimize warning -> one-click connect -> temporary unlock -> generate -> A/B/C report and writes `runs/studio_asset_context_browser_qa_report.json`.
- Added `tools/studio_asset_context_live_comparison.py` as the S1 A/B/C evidence runner. It writes a gate-closed readiness report by default and requires `AFS_ALLOW_REMOTE_IMAGE=true`, `--allow-live-provider`, provider config, and a real `--reference-image` or explicit `--sample-reference-output` before any image provider call can start.
- Added `tools/studio_asset_context_sample_reference.py` to write a deterministic non-provider PNG reference for reproducible provider smoke setup.
- Added `docs/handoff/AFS-ASSET-CONTEXT-S1-COMPLETION-AUDIT.md` to keep the current pass/block state explicit until live MiniMax evidence is available.
- Added Studio single-canvas fixed-asset confirmation panel, `context_subgraph` request building, asset connection status display, and "本次携带" bundle summary.

Verification so far:

```text
Focused Runtime/Web set: 34 passed, 1 Starlette/httpx warning.
Full pytest: 798 passed, 1 Starlette/httpx warning.
Studio changed JS node --check: passed.
Browser QA script: passed with provider gate closed; report records browser API POST proxy via FastAPI TestClient due local Chrome POST hang.
Live comparison runner gate-closed readiness: passed with ignored provider config path supplied; provider_calls_started=false.
Live comparison gate-safety preflight: simulated `AFS_ALLOW_REMOTE_IMAGE=true` without `--allow-live-provider`; blocked with `live_provider_flag_missing`, provider_calls_started=false.
Maintenance audit: passed with 0 warnings.
git diff --check: passed with Windows CRLF notices only.
```

Boundaries:

- Provider gates remain closed in local verification.
- No provider raw response, media bytes, local absolute paths, signed URLs, or secrets were added.
- This is not human acceptance, business validation, provider smoke, or durable-memory promotion.

## 2026-06-12 - MiniMax Text/Image Integration And Reference Flow

- Added gated MiniMax-M3 prompt enhancement for the creative intent agent path; deterministic local prompt assembly remains the fallback when the LLM gate or config is unavailable.
- Added gated MiniMax image-01 keyframe generation and safe candidate preview refs; API responses do not expose provider raw payloads, local absolute paths, signed URLs, media bytes, or secrets.
- Added Studio image upload assets and generated-keyframe reusable assets so connected downstream image nodes can send upstream reference images for image-to-image style tests.
- Kept the Studio user surface product-facing: optimization remains a node action, keyframe sending is image-node scoped, and trace/rule/weight/provider internals stay out of the UI.
- Local provider keys remain environment-only through `MINIMAX_API_KEY`; tracked config files contain examples and placeholders only.

Boundaries:

- Provider smoke is not human acceptance, business validation, video validation, or durable-memory promotion.
- Video generation remains closed.

## 2026-06-12 - AFS Studio v0.2 Delivery Polish

- Created isolated branch/worktree `codex/afs-studio-v02-delivery-polish-001` because the main checkout was occupied by a parallel MiniMax integration branch.
- Reframed the user-facing Studio surface into AFS Studio 创作图谱: flow-native starters for script-to-storyboard, character turnaround, 2D director board, keyframe prompt, and 5s video prompt.
- Added safe Runtime Studio state API: `GET /projects/{project_id}/studio-state` and `PUT /projects/{project_id}/studio-state`; only meta, viewport, nodes, semantic edges, visible assets, and safe summaries are persisted.
- Added frontend Runtime save/restore with localStorage fallback and visible save status: 已保存 / 保存中 / 同步中 / 本地暂存.
- Added lightweight undo/redo for meaningful canvas edits while excluding high-frequency pan/zoom/drag/prompt typing from history bloat.
- Upgraded visible assets: local preview and director saves create typed asset cards; asset drawer supports 设为参考, 用于当前节点, and 从画布定位.
- Added semantic edge types: generation, director, and reference; director/reference edges have distinct line styles and labels.
- Director board saves now upsert a `director_setup` asset and mark downstream edges as director constraints when applied to connected nodes.
- Prompt optimizer remains input-anchored and product-facing; result actions now give replace/append/copy feedback and source chips stay limited to 影视结构, 项目风格, 角色/场景设定, 导演台布置.
- Fixed narrow viewport horizontal overflow and split asset drawer CSS into `assets.css` to keep maintenance audit clean.

Verification:

```text
Runtime-hosted browser QA on http://127.0.0.1:8807/studio/: desktop director starter/modal path passed; mobile overflow false.
Focused tests: 27 passed, 1 Starlette/httpx warning.
Full pytest: 772 passed, 1 Starlette/httpx warning.
apps/studio JS node --check: passed.
maintenance_audit: passed.
git diff --check: passed with Windows CRLF notices only.
```

Boundaries:

- Provider gates remain closed.
- No image/video/media bytes were generated.
- This is not human acceptance, business validation, provider smoke, or durable-memory promotion.

## 2026-06-12 - AFS Studio UI Polish + 2D 导演台 Prompt 联动

- 修复 Studio 左上角重叠：抽屉展开时项目身份只由抽屉承载，顶栏从 `var(--drawer-w)` 右侧开始；抽屉收起时才显示 compact 项目 pill。
- 将导演台占位壳改成二维顶视图布置板：对象列表、网格画布、相机视锥、灯光光束、人物朝向、道具形状和右侧参数面板均可见。
- 导演台布置保存为节点本地 `directorSetup`；导演台节点展示机位 / 主体 / 灯光摘要，并可驱动相连图片或视频节点。
- Prompt 优化会从当前导演台节点或最近上游导演台节点提取安全版 `director_setup`；优化浮层显示用户可懂的“导演台布置”来源 chip。
- 后端用户版六段提示词已消费导演台上下文：人物站位、道具空间、机位/FOV/构图、灯光、运动连续性和光源/机位/空间冲突负面约束。
- 修复从底部 dock 添加节点时新节点落入 dock 安全区的问题：菜单仍从 dock 弹出，但节点出生点改为当前画布可视中心。
- 拆分导演台字段控件到 `apps/studio/src/panels/director-fields.js`，并将导演台 prompt API 测试移到 `tests/test_api_runtime_director_setup_prompt.py`，让本轮触达文件回到维护阈值内。
- 将 AgentFlow local AgentOps contract 示例的 `doc_path` 从已删除旧维护文档改到当前 `docs/company_operating_model.md`。

验证：

```text
Full pytest: 767 passed, 1 Starlette/httpx warning
Focused Studio / prompt / contract set: 21 passed
apps/studio JS node --check: passed
Runtime-hosted browser QA: passed
repository_retention_review manual_review_required_count: 0
git diff --check: passed with Windows CRLF notices only
maintenance_audit: 仅剩既有 human-facing Markdown 中文覆盖 warning；oversized_files 已通过
```

边界：

- Provider gate 仍关闭。
- 未生成图片/视频字节，也未保存 provider 原始响应。
- 这不是 human acceptance、business validation、provider smoke 或 durable-memory promotion。

## 2026-06-12 - Creative Intent Agent And Keyframe Gate

- Added deterministic `creative_intent_control_agent_v1` trace for prompt optimization.
- Added hard / strong / soft constraint layering, three internal candidates, multi-axis scores, deterministic selected candidate, and provider translation metadata.
- Treated `node_parameters` as hard controls in prompt assembly and trace.
- Added English `user preference:` extraction so lower-priority preferences can be suppressed when they conflict with professional/node constraints.
- Added `POST /projects/{project_id}/keyframe-generations`.
- Keyframe generation is gated by `AFS_ALLOW_REMOTE_IMAGE`; with the gate closed it writes only safe JSON artifacts and starts no network/provider call.
- Added repo-safe engineering summary: `docs/architecture/AFS_CREATIVE_INTENT_CONTROL_AGENT_ENGINEERING_SUMMARY.zh-CN.md`.
- Added private algorithm design note under `10-Startup/70-Projects/AgentFlow-Studio/30-agent-infrastructure/creative-intent-control-agent-v1.zh-CN.md`.
- Deleted stale Web/Workbench handoffs, old Web superpowers plans/specs, stale Web maintenance ledgers, and old Web archive files instead of archiving them.

Verification so far:

```text
tests/test_api_runtime_creative_agent_keyframes.py: 3 passed
prompt/runtime/studio focused set: 25 passed
apps/studio JS node --check: passed
```

Boundaries:

- No real provider call was made.
- No image/video bytes were generated through Runtime.
- This is not human acceptance, business validation, or durable-memory promotion.

## 2026-06-11 - AFS Studio Hard Cleanup

- Retired old Workbench/static memory-workbench user routes.
- Current frontend entry is `/studio/`, backed by `apps/studio/`.
- Deleted old UI source, old UI-specific tests, old Workbench browser QA tools, and old frontend integration docs.
- Prompt optimizer contract moved to `docs/architecture/AFS_NODE_PROMPT_OPTIMIZER_CONTRACT.zh-CN.md`.
- Verified earlier in this branch: full pytest, maintenance audit, `git diff --check`, Runtime-hosted `/studio/` browser QA, and `/workbench/` 404.
