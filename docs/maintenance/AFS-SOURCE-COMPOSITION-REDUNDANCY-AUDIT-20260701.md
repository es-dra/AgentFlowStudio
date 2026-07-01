# AFS Source Composition / Redundancy Maintenance Ledger - 2026-07-01

中文摘要：本账本是旧 redundancy maintenance lane 的 fresh rebuild。旧 lane 位于 `C:\Users\chenzy\.codex\worktrees\7dd1\AgentFlowStudio`，已经在合入 `d7478b7e` 时停在 `DEVLOG.md` conflict；该 lane 不再修补，标记为 superseded source。本文件从最新 continuation head `d7478b7e` 重新建立干净维护入口，不删除代码、不移动 legacy 文件、不处理 `docs/demo-docs-20260629/`。

## Lane Contract

- Fresh worktree: `C:\Users\chenzy\.codex\worktrees\afs-redundancy-rebuild-20260701`
- Branch: `codex/afs-redundancy-maintenance-ledger-rebuild-20260701`
- Base: `origin/codex/afs-post-main-loop-e2e-continuation-20260630` at `d7478b7e`
- Superseded source: `codex/afs-redundancy-maintenance-ledger-20260701` at `bb71d16a` plus unresolved `MERGE_HEAD=d7478b7e`
- Write scope: this maintenance ledger and a short `DEVLOG.md` record only
- Non-goals: no functional code change, no deletion, no quarantine move, no master merge, no push
- Provider gates: closed for LLM, ASR, image, video, external download, and high-cost actions
- Claim boundary: repository maintenance evidence only; not provider smoke, human creative acceptance, business validation, public claim, legal/patent conclusion, or COS active-rule promotion

## Startup Evidence

- Old worktree status was read-only checked and left untouched: `UU DEVLOG.md` plus upstream staged merge paths from the failed merge.
- Clean source checkout was `D:\Projects\AgentFlowStudio` at `d7478b7e`; it had only the known do-not-touch `docs/demo-docs-20260629/` untracked local state.
- Fresh worktree was created from `origin/codex/afs-post-main-loop-e2e-continuation-20260630`, not from the conflicted lane.
- Local `.venv` note: this fresh worktree does not carry its own virtualenv; verification can use `D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe` with cwd set to this worktree.

## 中文维护判断

这次重建的核心目标是 blocker reduction：不要继续围绕旧 `DEVLOG.md` conflict 被动汇报，而是把旧 lane 的有用结论转成干净、可 review、可 push 的维护分支。当前仓库没有可以立即删除的 tracked 候选；真正需要治理的是历史 Production Memory、旧 SOP 分发链、legacy Runtime v02、过长 handoff/DEVLOG/TASK_TRACKER、以及 oversized tests 与 provider/video 相关文件之间的边界。第一阶段应当只建立分类账本和后续 cleanup prompt，不直接删除、不 quarantine、不触碰 provider。

后续维护必须先保护当前 MVP 主链路：`/studio/`、Runtime Service、OpenAPI、prompt/storyboard/context/fixed asset/keyframe evidence、safe manifest、maintenance audit、retention review 和当前 T46/T47/T48 handoff。旧 Production Memory 与旧 SOP 面可以列为 quarantine candidate，但不能在本 lane 直接移动；它们需要单独 legacy quarantine lane、import scan、legacy pytest、CLI help/version 和 owner review。文档治理也必须先索引再迁移，避免把历史证据误删成无法回溯的状态。

本账本的执行原则是先降低调度阻塞，再降低维护债。旧冲突分支已经证明直接在原地缝合会把维护账本和后续 full pytest 残余提交混在一起，增加 review 成本；因此新的干净分支只保留两类变化：一是维护账本本身，二是 DEVLOG 中说明旧 lane 已被替代。后续 owner review 时应重点确认分类是否准确、第一批 cleanup prompt 是否足够窄、验证路线是否覆盖实际风险，而不是把本账本当作删除授权。任何删除、隔离、重构、provider smoke、公开发布或公司规则晋升，都必须另开 lane 并重新通过对应 gate。

## Source Map

| Area | Current role | MVP relevance | Maintenance posture |
|---|---|---|---|
| `agentflow/algorithms` | Current contracts for context, evidence, fixed assets, human gate, feedback, provider-gate manifests | High | Keep; dedicated lanes only |
| `agentflow/memory` | Frozen Production Memory legacy surface | Low for current MVP, high historical risk | Quarantine candidate, not current delete |
| `apps/api` | Runtime Service, prompt/storyboard/context/assets/keyframe/video routes | Highest | No-touch core except scoped Runtime lanes |
| `apps/studio` | Current `/studio/` canvas and Runtime client | Highest | No-touch core except scoped UI lanes |
| `apps/cli` | Current CLI plus hidden legacy Production Memory commands | Mixed | Keep current commands; review hidden legacy separately |
| `agentflow_studio/model_gateway` | Provider adapters, relays, Codex image worker, video adapters | Current and gate-sensitive | Defer broad cleanup |
| `agentflow_studio/*_sop`, `production`, `workflow_engine` | Legacy/optional distribution chain | Not current MVP spine | Quarantine candidate with legacy tests |
| `docs`, `tests`, `tools`, `examples` | Evidence, verification, maintenance, fixtures | Supporting | Migrate/index before deletion |

## No-Touch Core

- `apps/api/runtime_service.py`, `runtime_keyframe_routes.py`, `runtime_keyframes.py`, `runtime_context_resolver.py`, `runtime_visual_assets.py`, `runtime_human_gate.py`, `runtime_feedback_candidate.py`, `runtime_prompt_memory*`
- `apps/studio/src/runtime-client.js`, `node-generation-guards.js`, `node-keyframe-actions.js`, `keyframe-source-evidence-trace.js`, `generation-preflight-source-evidence.js`
- `agentflow/algorithms/context_resolver`, `generation_bridge`, `evidence_ledger`, `fixed_asset_memory`, `human_gate`, `feedback_*`, `provider_gate_manifest`
- `docs/openapi/afs-runtime-service.openapi.json`, current `docs/handoff/INDEX.md`, T46/T47/T48 handoffs, maintenance and retention tools

## Classification Ledger

| Class | Candidate | Evidence | Caller risk | Verification route | Follow-up lane |
|---|---|---|---|---|---|
| keep | Runtime/Studio main path | Project docs and handoffs identify `/studio/` plus Runtime Service as current boundary | High | full pytest, Studio JS if touched, CLI help/version, maintenance audit | No unless changed |
| keep | `agentflow/algorithms` current modules | Runtime E2E and keyframe/context evidence depend on these contracts | High | focused context/keyframe tests and main-loop E2E | No unless changed |
| migrate | `DEVLOG.md`, `TASK_TRACKER.md`, `docs/handoff/` | Large docs and many handoffs remain useful but heavy | Medium | maintenance audit, handoff index check | Docs/index lane |
| migrate | oversized active tests | Audit consistently reports large Runtime/Studio tests | Medium/high | targeted pytest plus full pytest | Test-maintenance lane |
| quarantine | `agentflow/memory` and `apps/cli/production_memory_*` | Legacy-frozen surface from maintenance audit | High | `pytest -m legacy`, CLI registry tests, CLI help/version | Legacy quarantine lane |
| quarantine | `agentflow_studio/*_sop`, `production`, `workflow_engine` | Legacy-frozen optional distribution chain | Medium/high | import scan, legacy collection, maintenance audit | Legacy quarantine lane |
| quarantine | `apps/api/runtime_v02.py` | Gate-controlled by `AFS_ENABLE_LEGACY_RUNTIME_V02` | Medium | v02 gate on/off tests and OpenAPI default snapshot | Runtime legacy lane |
| delete-candidate | none immediate | Prior retention review found no immediate tracked delete candidates | N/A | rerun retention before any deletion | Not authorized here |
| delete-candidate after proof | `apps/cli/support_command_registry.py` no-op transition wrapper | Prior audit noted low-risk no-op wrapper | Low/medium | CLI help/version and CLI registry boundary tests | Tiny code lane only if authorized |
| defer | provider/video surfaces and low-confidence secret-like fragments | Gate-sensitive or false-positive-prone | High | read-only classification first | Later provider/security lane |

## First Cleanup Prompt

```text
You are AFS Redundancy Cleanup Lane Worker. Start from docs/maintenance/AFS-SOURCE-COMPOSITION-REDUNDANCY-AUDIT-20260701.md on the latest continuation branch. Do not delete legacy code, do not quarantine files, do not touch docs/demo-docs-20260629/, and do not open provider gates. First scope is docs/test maintenance planning only, or one separately authorized tiny no-op cleanup for apps/cli/support_command_registry.py after proving caller risk. Verification must include repository_retention_review --summary-only, maintenance_audit, git diff --check, CLI help/version, and focused tests if code is touched. Do not claim human acceptance, business validation, provider smoke, public/legal/patent conclusion, or COS active-rule promotion.
```

## Verification Route

```powershell
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe tools\repository_retention_review.py --summary-only
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe tools\maintenance_audit.py
git diff --check
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main --help
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main version
```

Close condition: old conflicted lane is superseded, fresh ledger is committed on a clean branch, no-op verification passes, and branch diff against continuation is limited to `DEVLOG.md` plus this maintenance ledger.
