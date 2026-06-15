# Handoff Index

中文摘要：本索引只保留仍能服务当前本地 MVP 的交接文件。当前有效主线是 Studio、Runtime Service、专业知识库、创作智能体、图片关键帧 gate 和安全 artifact；旧 Workbench、旧静态 Web、旧 LibTV 迭代、发布候选包和过期浏览器 QA 已按“证据足够即删除”处理。后续接手时只能从本索引进入，不应回到已删除历史入口。

维护标准：索引中的文件必须能说明当前接口、测试、验证证据、provider 边界或下一步真实模型接入。不能解释当前主线的文件不再保留。每次新增 handoff 都要写明非目标、非声明、是否发生 provider call、是否写入长期记忆以及对应的验证命令。

Status: current handoff directory index for AgentFlow Studio.

This directory keeps only handoff files that still support the current local
MVP. Retired Workbench, static memory-workbench, old LibTV canvas iterations,
release-candidate Web docs, and old browser-QA handoffs were deleted instead of
archived.

## AFS Studio

- `AFS-STUDIO-V02-DELIVERY-POLISH-001.md`
- `AFS-STUDIO-MVP-M1-001.md`
- `AFS-STUDIO-MVP-M1-5-CORE-LOOPS-001.md`
- `AFS-ASSET-CONTEXT-S1.md`
- `AFS-ASSET-CONTEXT-S1-COMPLETION-AUDIT.md`
- `AFS-ASSET-CONTEXT-S1-FOLLOWUP-001.md`
- `AFS-STUDIO-FRONTEND-POLISH-001.md`
- `AFS-DIRECTOR-COMPILER-V1.md`
- `AFS-MVP-CLOSEOUT-20260612.md`
- `AFS-MVP-FOLLOWUP-LIVE-COMPARISONS-20260612.md`
- `AFS-KLING-PREFLIGHT-001.md`
- `AFS-VIDEO-LOCALIZED-REGEN-20260615.md`
- `AFS-BROWSER-ACCEPTANCE-DRILL-20260615.md`
- `AFS-MVP-EXPERIENCE-HARDENING-20260615.md`
- `AFS-FULL-CHAIN-LOCALIZED-QA-20260615.md`

`/studio/` is the only current user-facing frontend entry. Do not resume old
`/workbench/` or `apps/web` work from historical references.

## Prompt / Knowledge Runtime

- `AFS-PROMPT-MEMORY-LOOP-MVP-001.md`
- `AFS-PROFESSIONAL-KNOWLEDGEBASE-PROMPT-ASSEMBLY-001.md`

These handoffs cover the deterministic prompt assembly baseline, professional
knowledgebase rules, and hidden background context policy.

## Runtime Service

- `AFS-MINIMAX-TEXT-IMAGE-INTEGRATION-001.md`
- `AFS-PROVIDER-ADAPTER-V0-1.md`
- `AFS-PROVIDER-GATEWAY-V0-1.md`
- `AFS-KLING-PREFLIGHT-001.md`

Runtime remains the frontend boundary. Browser UI must not consume CLI
internals, provider secrets, local private paths, signed URLs, raw provider
responses, or media bytes.

## Current Maintenance Evidence

- `../maintenance/AFS-LEGACY-FREEZE-20260613.md`
- `AFS-PROJECT-INVENTORY-001.md`
- `../maintenance/AFS-PROJECT-INVENTORY-20260612.md`
- `../maintenance/AFS-STUDIO-HARD-CLEANUP-001.zh-CN.md`
- `../maintenance/AFS-ACTUAL-CLEANUP-002.zh-CN.md`
- `../maintenance/AFS-MODEL-GATEWAY-CYCLE-001.zh-CN.md`

## Routing Rule

- Studio work starts from `apps/studio/` and the two Studio handoffs.
- Prompt optimization work starts from the prompt/knowledge runtime handoffs.
- Provider work starts from provider-gated Runtime contracts and requires an
  explicit capability gate.
- Historical Web terms are not task entry points.
