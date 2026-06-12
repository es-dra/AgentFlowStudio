# AgentFlow Studio Task Tracker

中文摘要：本文件是当前 AFS MVP 的任务入口，只记录仍需要执行、验证或交接的事项。当前主线已经锁定 Studio 前端、Runtime API、专业知识库、创作意图控制智能体和图片/关键帧 provider gate；旧 Workbench、旧 Web RC、历史候选记忆 UI 和过期支线不再作为任务来源。任何事项如果不能导向第一版 MVP 落地、真实模型接入或低成本维护，应从这里移除。

保留理由：本文的价值在于让后续维护者快速判断当前任务是否仍能推动 MVP 收口和真实模型接入。每个任务都必须对应明确接口、测试、证据和非声明边界；没有当前引用的旧任务直接删除。真实模型接入前，所有结论都要重新经过本地测试、provider gate 检查、safe manifest 检查和人工体验确认。

当前口径：待办只保留三类，一是 Studio 和 Runtime 的联合验收，二是图片/关键帧真实模型 gate，三是创作智能体规则、评分和反馈回路的可验证改进。除此之外的旧支线、旧 UI 设想和无测试证据的概念记录都不进入任务列表。

Last updated: 2026-06-12 by Codex

This file keeps only current work, blockers, and evidence entrypoints. Retired
Workbench, static memory-workbench, old Web RC, and old browser-QA threads are
not current task entrypoints.

## Current Work

| ID | Owner role | Scope | Status | Evidence |
|---|---|---|---|---|
| AFS-PROVIDER-ADAPTER-V0-1 | Runtime/API Integrator + Provider Gate Steward | Provider Adapter v0.1 contract, service descriptor registry, MiniMax image Runtime dispatch decoupling, descriptor-driven prompt budget/reference slots. | Focused adapter/keyframe/resolver tests 22 passed; MiniMax smoke regression 9 passed; provider gates remain closed except mocked dispatch paths. | `agentflow_studio/model_gateway/provider_adapter.py`, `configs/providers.example.json`, `apps/api/runtime_keyframes.py`, `apps/api/runtime_context_resolver.py`, `docs/provider_adapter_contract.md`, `tests/test_provider_adapter_registry.py`, `tests/test_api_runtime_creative_agent_keyframes.py`, `tests/test_api_runtime_keyframe_reference_assets.py` |
| AFS-ASSET-CONTEXT-S1-FOLLOWUP-001 | Runtime/API Integrator + QA Gatekeeper | S1 完成审计三缺口收尾:预算分段裁剪真执行(锁定永不裁/可见保底 550/分隔符余量)、冲突检测属性词表化、上游摘要与偏好段补填;交付特征卡模板、A/B/C runbook、内测手册。 | Focused pytest `tests/test_runtime_attribute_vocabulary_and_budget.py tests/test_api_runtime_context_resolver.py` 16 passed; changed Studio JS passed `node --check`; `git diff --check` clean except CRLF warnings. | `apps/api/runtime_attribute_vocabulary.py`, `apps/api/runtime_context_budget.py`, `apps/api/runtime_context_resolver.py`, `tests/test_runtime_attribute_vocabulary_and_budget.py`, `docs/handoff/AFS-ASSET-CONTEXT-S1-FOLLOWUP-001.md`, `docs/visual_asset_feature_card_template.zh-CN.md`, `docs/abc_comparison_runbook.zh-CN.md`, `docs/afs_studio_internal_test_handbook.zh-CN.md` |
| AFS-ASSET-CONTEXT-S1 | Runtime/API Integrator + Studio Interaction Designer + Provider Gate Steward | Fixed visual assets, graph-scoped context resolver, dual prompt/model channels, and A/B/C comparison report. | Gate-closed Runtime/Web implementation, browser QA, live-comparison readiness runner, sample reference generator, and completion audit passed on `codex/afs-asset-context-s1`; no-call readiness has used the ignored provider config path, and live provider evidence now requires explicit `AFS_ALLOW_REMOTE_IMAGE=true` plus `--allow-live-provider`. | `apps/api/runtime_visual_assets.py`, `apps/api/runtime_context_resolver.py`, `apps/api/runtime_generation_comparisons.py`, `apps/studio/`, `tools/studio_asset_context_browser_qa.py`, `tools/studio_asset_context_live_comparison.py`, `tools/studio_asset_context_sample_reference.py`, `tests/test_api_runtime_visual_assets.py`, `tests/test_api_runtime_context_resolver.py`, `tests/test_api_runtime_generation_comparison.py`, `tests/test_studio_asset_context_live_comparison_tool.py`, `docs/handoff/AFS-ASSET-CONTEXT-S1.md`, `docs/handoff/AFS-ASSET-CONTEXT-S1-COMPLETION-AUDIT.md`, `docs/maintenance/AFS-ASSET-CONTEXT-S1.md` |
| AFS-STUDIO-V02-DELIVERY-POLISH-001 | Frontend Interaction Designer + Runtime/API Integrator + QA Gatekeeper | AFS Studio v0.2 internal delivery polish: flow-native starter, safe Studio state save/restore, visible asset drawer actions, semantic edges, prompt copilot feedback, mobile overflow guard. | Verified on `codex/afs-studio-v02-delivery-polish-001`; provider gates remain closed. | `apps/studio/`, `apps/api/runtime_studio_state.py`, `tests/test_api_runtime_studio_state.py`, `tests/test_web_studio_static.py`, `docs/handoff/AFS-STUDIO-V02-DELIVERY-POLISH-001.md` |
| AFS-STUDIO-UI-POLISH-DIRECTOR-002 | Frontend Interaction Designer + Runtime/API Integrator | 修复 Studio 左上角布局；落地二维导演台；将导演台结构化布置接入节点提示词优化；修复 dock 添加节点安全区。 | 已验证：全量 pytest 和浏览器 QA 通过；provider 仍关闭。 | `apps/studio/`, `apps/api/runtime_prompt_memory_user_prompt.py`, `tests/test_api_runtime_director_setup_prompt.py`, `docs/maintenance/AFS-STUDIO-HARD-CLEANUP-001.zh-CN.md` |
| AFS-STUDIO-HARD-CLEANUP-001 | Frontend Contract Steward + Maintainability Steward + QA / Release Gatekeeper | Delete retired Workbench/static memory-workbench user surfaces; make `/studio/` the only frontend entry. | In integration verification on `codex/afs-studio-hard-cleanup-001` | `docs/maintenance/AFS-STUDIO-HARD-CLEANUP-001.zh-CN.md` |
| AFS-CREATIVE-INTENT-AGENT-V1 | Runtime/API Integrator + Creative Agent Architect | Add deterministic creative intent control agent trace: constraint layers, candidate scoring, selected prompt, provider translation. | Focused tests passing | `docs/architecture/AFS_CREATIVE_INTENT_CONTROL_AGENT_ENGINEERING_SUMMARY.zh-CN.md` |
| AFS-KEYFRAME-GENERATION-GATE-001 | Runtime/API Integrator + Provider Gate Steward | Add `POST /projects/{project_id}/keyframe-generations`; gate closed path returns blocked safe manifest without network. | Focused tests passing | `tests/test_api_runtime_creative_agent_keyframes.py` |
| AFS-PROFESSIONAL-KNOWLEDGEBASE-PROMPT-ASSEMBLY-001 | Runtime/API Integrator + Knowledgebase Steward | Professional rules, hidden background context, prompt assembly, trace and safe manifest. | Baseline active; now feeds creative agent | `agentflow/knowledge/`, `docs/handoff/AFS-PROFESSIONAL-KNOWLEDGEBASE-PROMPT-ASSEMBLY-001.md` |

## Current Baseline

| Area | Path | Notes |
|---|---|---|
| Frontend | `apps/studio/` | Served through `/studio/`; only current user-facing Web product. |
| Runtime API | `apps/api/` | Frontend boundary; no CLI internals, provider secrets, local private paths, signed URLs, provider raw, or media bytes. |
| Prompt optimizer contract | `docs/architecture/AFS_NODE_PROMPT_OPTIMIZER_CONTRACT.zh-CN.md` | Node prompt optimization only; no memory review UI. |
| Creative agent summary | `docs/architecture/AFS_CREATIVE_INTENT_CONTROL_AGENT_ENGINEERING_SUMMARY.zh-CN.md` | Repo-safe engineering summary; detailed algorithm note is private in `10-Startup`. |
| Maintenance ledger | `docs/maintenance/AFS-STUDIO-HARD-CLEANUP-001.zh-CN.md` | Deletion decisions and verification plan. |

## Boundaries

- Provider gates are closed unless a task explicitly opens one capability.
- Image/keyframe authorization does not authorize video, LLM, ASR, or downloads.
- Browser/runtime verification, provider smoke, human acceptance, business validation, and durable-memory promotion are separate claim levels.
- Feedback and extracted context remain evidence/background unless explicitly promoted by a human workflow.

## Next Queue

| ID | Scope | Trigger |
|---|---|---|
| AFS-STUDIO-BROWSER-QA-001 | Runtime-hosted `/studio/` browser QA: create nodes, move nodes, connect ports, optimize prompt, open director panel, check mobile layout. | Before merging/pushing this branch. |
| AFS-IMAGE-PROVIDER-SMOKE-001 | Open `AFS_ALLOW_REMOTE_IMAGE=true` and run explicit MiniMax keyframe smoke with safe artifacts. | After branch is clean and user confirms real image provider smoke. |
| AFS-KEYFRAME-QA-001 | Add visual QA for generated keyframes: subject count, text/watermark, black/blank, composition, reference consistency. | After first real keyframe provider output exists. |
| AFS-STUDIO-SPRITE-V2-S0 | v2 画布小精灵首迭代前置：undo/redo 命令栈、Action Registry（L0-L3 白名单 + schema 校验）、`#sprite-layer`。规划见 `docs/architecture/AFS_STUDIO_SPRITE_V2_PLAN.zh-CN.md`（S0-S5 全里程碑、三工作模式、LLM gate 降级策略、lottie vendored 例外）。 | After MVP v1 联合验收（AFS-STUDIO-BROWSER-QA-001）收口。 |

## Current Addendum - MiniMax Provider Smoke Prep

| ID | Owner role | Scope | Status | Evidence |
|---|---|---|---|---|
| AFS-MINIMAX-TEXT-IMAGE-INTEGRATION-001 | Runtime/API Integrator + Provider Gate Steward | Add gated MiniMax-M3 prompt enhancement and MiniMax `image-01` keyframe path; keep video/audio off. | Local live smoke passed on `127.0.0.1:8793`; manual comparison pending. | `docs/handoff/AFS-MINIMAX-TEXT-IMAGE-INTEGRATION-001.md`, `configs/models.example.yaml`, `configs/providers.example.json` |
| AFS-MINIMAX-MANUAL-COMPARISON-001 | QA / Release Gatekeeper + Creative Director | Run A/B/C keyframe comparison: raw prompt, deterministic agent prompt, MiniMax-M3 enhanced prompt. | Ready for manual operation; latest provider output shows text/watermark risk to score. | `docs/handoff/AFS-MINIMAX-TEXT-IMAGE-INTEGRATION-001.md` |
| AFS-CONNECTED-REFERENCE-KEYFRAME-001 | Runtime/API Integrator + Studio Interaction Designer | Upload images on any Studio node; collect connected upstream reference images and prompt notes for keyframe generation. | Focused tests and Runtime upload smoke passed; live creative comparison pending. | `apps/api/runtime_image_assets.py`, `apps/studio/src/optimizer-contract.js`, `tests/test_api_runtime_creative_agent_keyframes.py` |
