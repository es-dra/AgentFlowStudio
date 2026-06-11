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
