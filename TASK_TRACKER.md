# AgentFlow Studio Task Tracker

Last updated: 2026-05-27 by Codex

This tracker records multi-session AgentFlow Studio work under the local
AI-native company operating model. A task is complete only when acceptance
criteria are checked and relevant verification evidence is recorded.

Company source knowledge base:

```text
D:\Learning materials\Learning_notes\Company
```

Project-facing operating model:

```text
docs/company_operating_model.md
```

## Active Tracks

| ID | Branch / worktree | Owner role | Scope | Status | Verification | Evidence / notes |
|---|---|---|---|---|---|---|
| AFS-OPS-001 | `codex/company-os-projection` | Orchestrator | Project-facing projection of Company rules into `AGENTS.md`, `docs/company_operating_model.md`, and `TASK_TRACKER.md` | completed | `git diff --check`; targeted doc review | Completed in main checkout per user request |
| AFS-MEM-001 | `codex/memory-os-loop` / `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\memory-os-loop` | Worker + reviewer | Add source-of-truth feedback and memory review loop for PosterFlow / Memory OS MVP | integrated to `master` | `python -m pytest tests/test_posterflow_workflow.py tests/test_posterflow_quality.py tests/test_posterflow_provider.py` -> 15 passed; `python -m pytest` -> 488 passed; `git diff --check`; CLI help/version | Added raw feedback JSONL, candidate JSONL, memory review JSONL |
| AFS-CTX-001 | `codex/memory-os-loop` / `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\memory-os-loop` | Worker + reviewer | Add minimal `context_bundle.json` and `context_assembly_trace.json` artifacts | integrated to `master` | `python -m pytest tests/test_posterflow_workflow.py tests/test_posterflow_quality.py tests/test_posterflow_provider.py` -> 15 passed; `python -m pytest` -> 488 passed; `git diff --check`; CLI help/version | Integrated together with AFS-MEM-001 because both slices share schema/workflow/quality surfaces |
| AFS-QLT-001 | `codex/quality-feedback-signals` / `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\quality-feedback-signals` | Worker + QA | Split PosterFlow quality harness and add candidate quality feedback signals for failed checks | integrated to `master` | `python -m pytest tests/test_posterflow_quality.py tests/test_posterflow_workflow.py tests/test_posterflow_provider.py` -> 15 passed; `python -m pytest` -> 488 passed; `git diff --check`; CLI help/version | Remote/local branch and worktree deleted after integration |
| AFS-DEMO-001 | `codex/posterflow-two-round-demo` / `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\posterflow-two-round-demo` | Worker + QA + human reviewer | Build a true two-round PosterFlow Memory OS demo with comparison report | integrated to `master` | `python -m pytest tests/test_posterflow_workflow.py tests/test_posterflow_quality.py tests/test_posterflow_provider.py` -> 16 passed; `python -m pytest` -> 489 passed; `git diff --check`; CLI help/version | Integrated at `ff77b30`; local and remote branch/worktree deleted after verification |
| AFS-PROV-001 | `codex/posterflow-minimax-rebase` / `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\posterflow-minimax-rebase` | Worker + QA | Replay MiniMax PosterFlow provider support on fresh `master` without merging stale branch state | integrated to `master` | `python -m pytest tests/test_posterflow_provider.py` -> 12 passed; `python -m pytest tests/test_posterflow_provider.py tests/test_posterflow_workflow.py tests/test_posterflow_quality.py` -> 22 passed; `python -m pytest` -> 495 passed; `git diff --check`; CLI help/version | Integrated at `649d736`; superseded stale MiniMax branch and both provider branches were deleted |
| AFS-ALPHA-001 | `codex/alpha-readiness-rebase` / `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\alpha-readiness-rebase` | Worker + QA | Replay Alpha readiness evidence from old stacked branch onto clean `master` | integrated to `master` | `python -m pytest tests/test_video_to_finished_package_local_asr_workflow.py tests/test_agentflow_roadmap_docs.py tests/test_posterflow_provider.py tests/test_posterflow_workflow.py tests/test_posterflow_quality.py` -> 35 passed; `python -m pytest` -> 496 passed; `git diff --check`; CLI help/version | Integrated at `ac2254e`; old stacked alpha branch and replacement branch/worktree deleted |
| AFS-WEB-001 | `codex/narratocut-web-ui` / archived | Worker + QA | Preserve and classify the independent NarratoCut Web UI line after repository rename | archived and superseded | Web UI targeted tests -> 41 passed; branch full `pytest` -> 374 passed; CLI help/version; JS syntax checks; `compileall`; `git diff --check` | Archived at tag `archive/narratocut-web-ui-de8ca8e`; useful work replayed by `AFS-WEB-REPLAY`; branch/worktree deleted |
| AFS-OPS-002 | main checkout | Orchestrator + Docs Projection Agent | Add project execution entry points for agent roster, task brief, provider gates, and Company feedback | completed | `git diff --check`; `python -m pytest tests/test_agentflow_roadmap_docs.py` -> 8 passed; CLI help/version | Documents-only operating-system pass; no runtime code or provider calls |
| AFS-PROD-001 | `codex/afs-prod-alpha-smoke` / `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-prod-alpha-smoke` | Workflow Engineer | Add read-only Alpha smoke/status CLI for current engineering readiness | integrated to `master` | `python -m pytest tests/test_video_to_finished_package_local_asr_workflow.py tests/test_narratostudio_workflow.py tests/test_posterflow_provider.py tests/test_alpha_smoke_cli.py` -> 25 passed; `alpha-smoke --json`; `git diff --check` | Integrated at `5c88d21`; writes no run artifacts and calls no providers |
| AFS-QA-001 | `codex/afs-quality-evidence-summary` / `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-quality-evidence-summary` | Harness / QA Reviewer | Add shared evidence summary vocabulary for quality and review reports | integrated to `master` | `python -m pytest tests/test_agent_reviewer.py tests/test_harness_quality_checks.py tests/test_posterflow_quality.py tests/test_narratostudio_review_hardening.py tests/test_evidence_summary.py tests/test_alpha_smoke_cli.py` -> 26 passed; CLI help/version; `alpha-smoke --json`; `git diff --check` | Integrated at `17c72e5`; additive report field only, no provider calls |
| AFS-MEM-002 | `codex/afs-memory-promotion-review` / `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-memory-promotion-review` | Memory / Evidence Steward | Validate memory promotion review decisions without durable memory writes | integrated to `master` | `python -m pytest tests/test_agentflow_asset_memory_validator.py tests/test_contract_examples.py tests/test_narratostudio_asset_feedback_smoke.py tests/test_narratostudio_asset_reuse_chain_audit_smoke.py tests/test_posterflow_quality.py tests/test_evidence_summary.py tests/test_alpha_smoke_cli.py` -> 57 passed; `compileall agentflow\memory agentflow\harness`; CLI help/version; `alpha-smoke --json`; `git diff --check` | Integrated at `8fd9fe4`; no DB, RAG, provider calls, or durable Memory runtime |
| AFS-WEB-REPLAY | `codex/afs-web-ui-replay` / `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-web-ui-replay` | Web UI Agent + Release Integrator | Replay local Review/Production Web UI workbench on current mainline | integrated to `master` | Web targeted tests -> 60 passed; JS `node --check`; `compileall apps\web_bridge apps\cli tests`; CLI help/version/web-bridge help; browser smoke: local bridge + static UI + mock workflow + review refresh | Integrated at `5d0392f`; local-only, no provider calls, no browser persistence |
| AFS-OPS-003 | main checkout | Orchestrator | Align operating docs with the Local Alpha 0.2 product queue and create task briefs | completed | `python -m pytest tests/test_agentflow_roadmap_docs.py`; `python -m apps.cli.main alpha-smoke --json`; `git diff --check` | Updates only project execution docs; no runtime code or provider calls |
| AFS-ALPHA-PKG-001 | `codex/afs-alpha-package` / `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-alpha-package` | Orchestrator + Release Integrator | Local Alpha 0.2 acceptance package and demo script | completed | `python -m apps.cli.main alpha-smoke --json`; `python -m pytest tests/test_agentflow_roadmap_docs.py`; `git diff --check` | Evidence: `docs/local_alpha_0_2_acceptance.md`; no runtime code or provider calls |
| AFS-WEB-UX-001 | `codex/afs-web-ux-pass` / `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-web-ux-pass` | Web UI Agent + QA Reviewer | Web workbench usability pass | completed | Web targeted tests -> 42 passed; JS `node --check`; `compileall apps\web_bridge apps\cli tests`; `git diff --check`; browser smoke local bridge + static UI + mock workflow + review refresh | Evidence: `docs/handoff/AFS-WEB-UX-001.md`; temp smoke screenshot outside repo at `C:\Users\chenzy\AppData\Local\Temp\afs-web-ux-pass-smoke-main.png`; fixed small-screen sticky topbar click coverage; no provider calls or browser persistence |
| AFS-MEMORY-DEMO-001 | `codex/afs-memory-demo-hardening` / `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-memory-demo-hardening` | Memory / Evidence Steward | Two-round Memory OS demo hardening | completed | PosterFlow workflow/quality/provider tests -> 23 passed; `alpha-smoke --json` -> blocked as expected because remote image provider is disabled; `git diff --check` -> passed | Added explicit `poster_round_comparison.json.evidence_chain` and review checks; handoff: `docs/handoff/AFS-MEMORY-DEMO-001.md`; integrated into current merge batch |
| AFS-POSTER-LIVE-001 | `codex/afs-poster-live-smoke` / `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-poster-live-smoke` | Provider Adapter Agent + Security / Secret Audit Agent | Gated PosterFlow live-smoke checklist or run evidence | blocked checklist integrated | `alpha-smoke --json` -> blocked because image provider env is unset; PosterFlow provider/workflow/quality tests -> 22 passed; `git diff --check` -> passed | Evidence: `docs/handoff/AFS-POSTER-LIVE-001.md`; no live provider call, no provider config, no secrets |

## Integration Gate

Current gate:

- `AFS-MEM-001`, `AFS-CTX-001`, and `AFS-QLT-001` are integrated to `master`.
- `AFS-DEMO-001` is integrated to `master` at `ff77b30`.
- `AFS-PROV-001` is integrated to `master` at `649d736`.
- `AFS-ALPHA-001` is integrated to `master` at `ac2254e`.
- `AFS-PROD-001` is integrated to `master` at `5c88d21`.
- `AFS-QA-001` is integrated to `master` at `17c72e5`.
- `AFS-MEM-002` is integrated to `master` at `8fd9fe4`.
- `AFS-WEB-REPLAY` is integrated to `master` at `5d0392f`.
- The old preserved Web UI branch `origin/codex/narratocut-web-ui` at
  `de8ca8e` is archived by tag `archive/narratocut-web-ui-de8ca8e` and deleted.
- All four lanes from the previous dispatch batch are integrated. Mainline full
  verification passed with 548 tests. The four replay/integration worktrees and
  local branches were removed after merge.
- `AFS-OPS-003` is the current docs-only setup slice for the first formal
  Local Alpha 0.2 product push.
- Four Local Alpha 0.2 worktrees are opened, pushed, tracking origin, and ready
  for task execution. Main checkout remains the integration surface.

## Operating Entry Points

Use this minimum entry set:

- Small local doc edits: `AGENTS.md` plus the touched file.
- Normal AFS work: `AGENTS.md`, `docs/company_operating_model.md`, and this
  tracker.
- Parallel or delegated work: also use `docs/agent_operating_roster.md` and
  `docs/agent_task_brief_template.md`.

Subagents are ephemeral. A visible old agent card is not an active lane unless
the agent manager can still resume or close that ID. If a close attempt returns
`not found`, record the agent as inactive history.

## Next Parallel Queue

Do not start these from the main checkout. Create separate `codex/*` worktrees
after `AFS-OPS-003` verification is recorded.

| ID | Suggested branch / worktree | Owner role | Primary write scope | Initial verification |
|---|---|---|---|---|
| AFS-ALPHA-PKG-001 | `codex/afs-alpha-package` / `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-alpha-package` | Orchestrator + Release Integrator | `docs/`, `TASK_TRACKER.md` integration notes only | `python -m apps.cli.main alpha-smoke --json`; `python -m pytest tests/test_agentflow_roadmap_docs.py`; `git diff --check` |
| AFS-WEB-UX-001 | `codex/afs-web-ux-pass` / `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-web-ux-pass` | Web UI Agent + QA Reviewer | `apps/web/`, `apps/web_bridge/`, Web tests, `apps/web/README.md` | Web targeted tests; JS `node --check`; browser smoke with local bridge |
| AFS-MEMORY-DEMO-001 | `codex/afs-memory-demo-hardening` / `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-memory-demo-hardening` | Memory / Evidence Steward | PosterFlow demo artifacts/docs/tests under `narratostudio/posterflow`, `workflows`, `tests`, `docs` | PosterFlow workflow/provider/quality tests; `alpha-smoke --json`; `git diff --check` |
| AFS-POSTER-LIVE-001 | `codex/afs-poster-live-smoke` / `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-poster-live-smoke` | Provider Adapter Agent + Security / Secret Audit Agent | PosterFlow live-smoke docs/checklist and optional ignored local run evidence | provider env check; no-secret scan; PosterFlow provider tests; optional live smoke only with explicit local env |

Integration order:

1. `AFS-ALPHA-PKG-001` first, because it defines what Local Alpha 0.2 accepts.
2. `AFS-MEMORY-DEMO-001` and `AFS-WEB-UX-001` can integrate in either order if
   their write scopes stay disjoint.
3. `AFS-POSTER-LIVE-001` last, because live provider evidence must remain
   gated and may be blocked by local environment.

## Remote Branch Hygiene

Current branch classification as of 2026-05-26:

| Branch | Classification | Next action |
|---|---|---|
| `origin/codex/memory-os-loop` | integrated to `master` | Deleted after fast-forward merge and verification. |
| `origin/codex/quality-feedback-signals` | integrated to `master` | Deleted after fast-forward merge and verification. |
| `origin/codex/posterflow-memory-demo` | patch-equivalent stale pre-merge PosterFlow demo branch | Deleted after `git cherry -v master codex/posterflow-memory-demo` showed the branch patch is already in `master`. |
| `origin/codex/posterflow-minimax-provider-tests` | stale provider reference branch | Deleted after `AFS-PROV-001` replaced it on current `master`. |
| `origin/codex/posterflow-minimax-rebase` | integrated replacement provider branch | Deleted after fast-forward integration and verification. |
| `origin/codex/alpha-readiness-evidence` | stale stacked alpha evidence branch | Deleted after `AFS-ALPHA-001` replayed the evidence on current `master`. |
| `origin/codex/alpha-readiness-rebase` | integrated replacement alpha evidence branch | Deleted after fast-forward integration and verification. |
| `origin/codex/narratocut-web-ui` | superseded independent Web UI line | Deleted after pushing current `master` and archive tag `archive/narratocut-web-ui-de8ca8e`. The replay branch integrated the useful Web UI surface and the old branch would now regress `apps/cli/main.py`, `apps/web_bridge/bridge.py`, Web bridge tests, and handoff docs. |

Current local cleanup as of 2026-05-27:

- Removed integrated worktrees:
  `afs-prod-alpha-smoke`, `afs-quality-evidence-summary`,
  `afs-memory-promotion-review`, and `afs-web-ui-replay`.
- Deleted integrated local branches:
  `codex/afs-prod-alpha-smoke`, `codex/afs-quality-evidence-summary`,
  `codex/afs-memory-promotion-review`, and `codex/afs-web-ui-replay`.
- Pushed `master` and archive tag `archive/narratocut-web-ui-de8ca8e`, then
  deleted remote `origin/codex/narratocut-web-ui`.
- Removed the old local `narratocut-web-ui` worktree and local branch after
  confirming the archive tag points to the same commit.

## Current Task Detail

### AFS-OPS-001: Company OS Projection

Goal:

- Keep `Company/` as the source knowledge base while giving this repository a
  concise execution-facing projection.

Acceptance criteria:

- [x] `AGENTS.md` names the Company source boundary and AI-native workflow
      hierarchy.
- [x] `docs/company_operating_model.md` explains how Company rules, global
      workflow skills, project rules, and task trackers relate.
- [x] `TASK_TRACKER.md` records the initial parallel tracks and completion
      policy.
- [x] No confidential Company strategy, secrets, real costs, customer details,
      or private retrospectives are copied into this repository.
- [x] `git diff --check` passes for the repository.

Status:

- completed

### AFS-MEM-001: PosterFlow Memory OS Loop

Goal:

- Add a minimal evidence-backed feedback-to-memory-review loop to PosterFlow
  without adding durable Memory runtime or changing remote provider behavior.

Acceptance criteria:

- [x] `poster_feedback.jsonl` is written as the raw feedback source of truth.
- [x] `poster_feedback_signal_log.json` remains derived and points to
      `poster_feedback.jsonl`.
- [x] `poster_memory_candidates.jsonl` is candidate-only and matches the
      existing `poster_memory_candidates.json` candidate IDs.
- [x] `poster_memory_review.jsonl` records explicit review decisions and does
      not write long-term memory.
- [x] PosterFlow inspect/review fails when raw feedback is missing or memory
      review claims durable writes.
- [x] Full test suite passes in the implementation worktree.

Verification:

```powershell
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests/test_posterflow_workflow.py tests/test_posterflow_quality.py tests/test_posterflow_provider.py
# 14 passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest
# 487 passed

git diff --check
# passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0
```

Status:

- integrated to `master` with AFS-CTX-001

Evidence:

- Worktree: `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\memory-os-loop`
- Branch: `codex/memory-os-loop`
- Project record: `DEVLOG.md` in the implementation worktree
- Company memory update: `Company/60-assets-and-memory/02-失败归因与反模式�?md`

### AFS-OPS-002: Agent Operating Entry Points

Goal:

- Convert the Company operating rules and recent AFS lessons into concrete
  project entry points for parallel development.

Acceptance criteria:

- [x] `AGENTS.md` points substantial work to the agent roster and task brief.
- [x] `docs/company_operating_model.md` records fast entry points,
      capability-specific provider gates, and next parallel lanes.
- [x] `docs/agent_operating_roster.md` defines standing roles, temporary
      roles, dispatch triggers, lifecycle, and next queue.
- [x] `docs/agent_task_brief_template.md` provides the AFS task template.
- [x] `TASK_TRACKER.md` fixes stale integrated-task status and records the next
      parallel queue.
- [x] Reusable lessons are promoted to Company source rules and anti-patterns.

Verification:

```powershell
git diff --check
# passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests/test_agentflow_roadmap_docs.py
# 8 passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0
```

Status:

- completed

Evidence:

- Project docs: `docs/agent_operating_roster.md`,
  `docs/agent_task_brief_template.md`, `docs/company_operating_model.md`
- Company rule updates:
  `D:\Learning materials\Learning_notes\Company\30-engineering\01-分支-worktree-子智能体协作规范.md`
  and
  `D:\Learning materials\Learning_notes\Company\60-assets-and-memory\02-失败归因与反模式�?md`

### AFS-OPS-003: Local Alpha 0.2 Product Queue

Goal:

- Align project execution docs with the real post-cleanup branch state and
  create executable task briefs for the first formal product push.

Acceptance criteria:

- [x] `docs/company_operating_model.md` names Local Alpha 0.2 as the current
      product milestone.
- [x] `docs/agent_operating_roster.md` removes stale preserved Web branch
      language and lists the next product queue.
- [x] `TASK_TRACKER.md` records the current queue, integration order, and branch
      hygiene state.
- [x] `docs/task_briefs/` contains direct briefs for the next four lanes.
- [x] No runtime code, generated artifacts, provider config, or Company private
      content is copied.

Verification:

```powershell
python -m pytest tests/test_agentflow_roadmap_docs.py
# 8 passed

python -m apps.cli.main alpha-smoke --json
# status: blocked because remote image provider is not enabled

git diff --check
# passed with Windows line-ending warnings only
```

Status:

- completed

Evidence:

- `docs/company_operating_model.md`
- `docs/agent_operating_roster.md`
- `docs/task_briefs/`

### AFS-ALPHA-PKG-001: Local Alpha 0.2 Acceptance Package

Goal:

- Turn current engineering evidence into a repeatable local Alpha acceptance
  flow for future agents and human review.

Acceptance criteria:

- [x] A Local Alpha 0.2 acceptance package doc exists under `docs/`.
- [x] The package defines current demoable capabilities, blockers, non-claims,
      rerun commands, and acceptance checklist.
- [x] The package links the Web workbench, NarratoStudio, NarratoCut, and
      PosterFlow evidence paths.
- [x] `TASK_TRACKER.md` records lane status and evidence.
- [x] No confidential Company content or provider secrets are copied.

Verification:

```powershell
python -m apps.cli.main alpha-smoke --json
# status: blocked because remote image provider is not enabled

python -m pytest tests/test_agentflow_roadmap_docs.py
# 8 passed

git diff --check
# passed with Windows line-ending warnings only
```

Status:

- completed

Evidence:

- `docs/local_alpha_0_2_acceptance.md`
- `docs/task_briefs/AFS-ALPHA-PKG-001.md`

### AFS-PROD-001: Alpha Smoke Status CLI

Goal:

- Add a read-only Alpha smoke/status entry that summarizes current engineering
  readiness without running workflows, writing run artifacts, or calling
  providers.

Acceptance criteria:

- [x] CLI exposes `alpha-smoke`.
- [x] `alpha-smoke` prints human-readable status for NarratoStudio handoff,
      NarratoCut finished package, and PosterFlow provider readiness.
- [x] `alpha-smoke --json` prints machine-readable JSON.
- [x] With no image-provider environment, PosterFlow is `blocked`, not
      `pass`.
- [x] The command does not call remote providers and does not write runtime
      artifacts.
- [x] Documentation links the command from the alpha readiness report and docs
      index.

Verification:

```powershell
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests/test_video_to_finished_package_local_asr_workflow.py tests/test_narratostudio_workflow.py tests/test_posterflow_provider.py tests/test_alpha_smoke_cli.py
# 25 passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main alpha-smoke --json
# status: blocked; no providers called

git diff --check
# passed with Windows line-ending warnings only
```

Status:

- integrated to `master` at `5c88d21`

Evidence:

- `apps/cli/alpha_commands.py`
- `tests/test_alpha_smoke_cli.py`
- `docs/handoff/AFS-PROD-001.md`

### AFS-QA-001: Evidence Summary Adapter

Goal:

- Add a compact shared evidence summary vocabulary that report consumers can
  use without inferring acceptance or business validation from raw test status.

Acceptance criteria:

- [x] `agentflow.harness.evidence_summary` exposes builders for quality and
      review surfaces.
- [x] `build_quality_report()` adds `evidence_summary` without changing
      existing report fields.
- [x] `review_run()` adds `evidence_summary` without changing existing report
      fields.
- [x] Pass/fail/warning variants are normalized to the shared AgentFlow
      status constants.
- [x] Decision boundaries distinguish machine verification, human acceptance,
      business validation, and memory promotion.
- [x] The change does not call providers, run workflows, or write durable
      memory.

Verification:

```powershell
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests/test_agent_reviewer.py tests/test_harness_quality_checks.py tests/test_posterflow_quality.py tests/test_narratostudio_review_hardening.py tests/test_evidence_summary.py tests/test_alpha_smoke_cli.py
# 26 passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main alpha-smoke --json
# status: blocked because remote image provider is not enabled

git diff --check
# passed
```

Status:

- integrated to `master` at `17c72e5`

Evidence:

- `agentflow/harness/evidence_summary.py`
- `tests/test_evidence_summary.py`
- `docs/handoff/AFS-QA-001.md`

### AFS-MEM-002: Memory Promotion Review Decisions

Goal:

- Validate candidate memory promotion decisions as review artifacts without
  writing durable memory or implying a Memory runtime exists.

Acceptance criteria:

- [x] `agentflow.memory.promotion` validates promotion review decisions as a
      side-effect-free contract surface.
- [x] Supported decisions are limited to `promoted`, `rejected`, `merged`, and
      `expired`.
- [x] Promotion decisions must link exactly one source candidate.
- [x] Promotion decisions must keep non-empty `evidence_refs` and preserve the
      candidate evidence refs.
- [x] Durable memory claim fields such as `durable_memory_ref` and
      `persisted_memory_id` are rejected.
- [x] Outputs keep `runtime_status: not_implemented`,
      `does_not_execute: true`, and `writes_long_term_memory: false`.

Verification:

```powershell
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests/test_agentflow_asset_memory_validator.py tests/test_contract_examples.py tests/test_narratostudio_asset_feedback_smoke.py tests/test_narratostudio_asset_reuse_chain_audit_smoke.py tests/test_posterflow_quality.py tests/test_evidence_summary.py tests/test_alpha_smoke_cli.py
# 57 passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m compileall agentflow\memory agentflow\harness
# passed

git diff --check
# passed
```

Status:

- integrated to `master` at `8fd9fe4`

Evidence:

- `agentflow/memory/promotion.py`
- `docs/agentflow_memory_contract.md`
- `examples/agentflow/memory_promotion_decision.example.json`
- `tests/test_agentflow_asset_memory_validator.py`
- `docs/handoff/AFS-MEM-002.md`

### AFS-WEB-REPLAY: Local Web UI Workbench

Goal:

- Replay the preserved Web UI line onto current `master` without bringing back
  stale backend/module changes from the old branch.

Acceptance criteria:

- [x] Only Web-facing code, Web bridge code, Web fixtures, and Web tests are
      integrated from the replay lane.
- [x] Review Mode remains local-only and reads only explicitly selected files.
- [x] Production Mode connects only to the local bridge at `127.0.0.1`.
- [x] `python -m apps.cli.main web-bridge` starts the local bridge entrypoint
      used by the README.
- [x] Production Mode can generate a plan, run a demo workflow, poll status,
      list artifacts, and refresh review reports.
- [x] Browser state remains non-persistent: no `localStorage`, IndexedDB,
      cookies, uploads, provider config, SaaS, or cloud backend.

Verification:

```powershell
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests/test_web_static_artifact_viewer.py tests/test_web_production_mode_static.py tests/test_web_production_bridge.py tests/test_alpha_smoke_cli.py tests/test_evidence_summary.py tests/test_agentflow_asset_memory_validator.py
# 60 passed

node --check apps/web/app.js
node --check apps/web/app-elements.js
node --check apps/web/feedback-wiring.js
node --check apps/web/feedback-event.js
node --check apps/web/production-mode.js
node --check apps/web/production-render.js
node --check apps/web/production-workflows.js
node --check apps/web/artifact-values.js
node --check apps/web/video-preview.js
node --check apps/web/artifact-contracts.js
node --check apps/web/artifact-ledgers.js
node --check apps/web/artifact-workspace.js
node --check apps/web/render-helpers.js
node --check apps/web/ui-copy.js
# passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m compileall apps\web_bridge apps\cli tests
# passed
```

Browser smoke:

- Started `python -m apps.cli.main web-bridge --host 127.0.0.1 --port 8787`.
- Started `python -m http.server 8769 -d apps/web --bind 127.0.0.1`.
- Opened `http://127.0.0.1:8769/index.html`.
- Confirmed Review Mode rendered with no browser error logs.
- Confirmed Production Mode bridge health showed `bridge ready`.
- Selected `mock_text_to_slices`, generated `workflow_plan.json`, ran workflow
  to `success`, saw all four steps pass, and refreshed review to `passed`.

Status:

- integrated to `master` at `5d0392f`

Evidence:

- `apps/web/`
- `apps/web_bridge/`
- `apps/cli/main.py`
- `tests/test_web_static_artifact_viewer.py`
- `tests/test_web_production_mode_static.py`
- `tests/test_web_production_bridge.py`
- `docs/handoff/AFS-WEB-REPLAY.md`

### AFS-CTX-001: PosterFlow Context Runtime Trace

Goal:

- Add a minimal, auditable context assembly path after project prefix and
  preference profile generation.

Acceptance criteria:

- [x] `context_bundle.json` records hot/warm/cold/policy context layers.
- [x] `context_assembly_trace.json` records why context was included or
      excluded.
- [x] `next_round_prompt.json` references `context_bundle.json` and the cache
      key.
- [x] PosterFlow inspect/review fails when the context trace no longer points
      to the generated bundle.
- [x] No RAG, prefix-cache service, Router runtime, database, or provider
      orchestration is added.

Verification:

```powershell
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests/test_posterflow_workflow.py tests/test_posterflow_quality.py tests/test_posterflow_provider.py
# 15 passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest
# 488 passed

git diff --check
# passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0
```

Status:

- integrated to `master` with AFS-MEM-001

Evidence:

- Worktree: `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\memory-os-loop`
- Project record: `DEVLOG.md` in the implementation worktree

Follow-up:

- AFS-QLT-001 started after this integration and handles the quality harness
  split plus candidate quality feedback signals.

### AFS-QLT-001: PosterFlow Quality Feedback Signals

Goal:

- Split the PosterFlow quality harness so future checks do not expand one large
  file, then add a minimal quality-failure feedback signal path for Memory OS
  learning.

Acceptance criteria:

- [x] `narratocut/harness/posterflow_quality.py` is reduced below 300 lines.
- [x] JSON/JSONL reading and schema checks are moved into a focused module.
- [x] Cross-artifact reference checks are moved into a focused module.
- [x] Failed PosterFlow quality checks produce candidate feedback signals in
      `quality_report.json`.
- [x] Passing PosterFlow runs produce zero quality feedback signals.
- [x] Quality feedback signals are candidate-only and set
      `writes_long_term_memory: false`.

Verification:

```powershell
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests/test_posterflow_quality.py tests/test_posterflow_workflow.py tests/test_posterflow_provider.py
# 15 passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest
# 488 passed

git diff --check
# passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0
```

Status:

- integrated to `master`

Evidence:

- Worktree: `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\quality-feedback-signals`
- Branch: `codex/quality-feedback-signals`
- Integration commit: `34dd51b feat(posterflow): add quality feedback signals`
- Remote/local branch and worktree were deleted after integration.

### AFS-DEMO-001: PosterFlow Two-Round Memory Demo

Goal:

- Turn the single-run PosterFlow memory demo into a true two-round workflow:
  round 1 generates candidates and memory-context artifacts; round 2 uses the
  next-round prompt to generate new candidates and writes an auditable
  comparison report.

Acceptance criteria:

- [x] `next_round_prompt.json` is converted into a second-round prompt pack.
- [x] Round 2 writes its own prompt pack, candidate manifest, model invocation
      log, and image candidates under `round_2/`.
- [x] Round 2 uses the existing remote-image provider gate; no new provider
      policy or automatic remote call path is added.
- [x] `poster_round_comparison.json` records round 1 vs round 2, reused memory
      refs, cache key, and `writes_long_term_memory: false`.
- [x] `poster_two_round_report.md` gives an agent-readable summary.
- [x] Inspect/review fails when the round-2 comparison no longer matches the
      round-2 candidate manifest.
- [x] New and touched code files remain below the 300-line target.

Verification:

```powershell
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests/test_posterflow_workflow.py tests/test_posterflow_quality.py tests/test_posterflow_provider.py
# 16 passed
```

Status:

- integrated to `master` at `ff77b30`

Evidence:

- Worktree: `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\posterflow-two-round-demo`
- Branch: `codex/posterflow-two-round-demo`
- Main implementation module: `narratostudio/posterflow/two_round.py`
- Full verification in the worktree: 489 tests passed, CLI help/version
  passed, and `git diff --check` passed with Windows line-ending warnings only.
- Branch and worktree were deleted after integration and remote cleanup.

### AFS-PROV-001: PosterFlow MiniMax Provider Replay

Goal:

- Add native MiniMax image provider support to PosterFlow without directly
  merging the stale old MiniMax branch or changing default provider behavior.

Acceptance criteria:

- [x] `NARRATOCUT_IMAGE_PROVIDER=openai_compatible` remains the default.
- [x] `NARRATOCUT_IMAGE_PROVIDER=minimax` selects a native MiniMax provider via
      `create_image_provider_from_env()`.
- [x] MiniMax requests use `/v1/image_generation`,
      `response_format=base64`, `image-01` by default, and support base URLs
      with or without a trailing `/v1`.
- [x] MiniMax candidate count is validated in-process before any remote call.
- [x] Provider invocation logs do not include API keys, provider base URLs, raw
      response ids, or response error bodies.
- [x] PosterFlow round 1 and round 2 generation nodes use the provider factory
      and keep the existing remote-image opt-in gate.
- [x] New and touched code files remain below the 300-line target.

Verification:

```powershell
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests/test_posterflow_provider.py
# 12 passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests/test_posterflow_provider.py tests/test_posterflow_workflow.py tests/test_posterflow_quality.py
# 22 passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest
# 495 passed

git diff --check
# passed with Windows line-ending warnings only

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main --help
# passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main version
# 0.1.0
```

Status:

- integrated to `master` at `649d736`

Evidence:

- Worktree: `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\posterflow-minimax-rebase`
- Branch: `codex/posterflow-minimax-rebase`
- Main implementation modules:
  `narratostudio/posterflow/minimax_provider.py` and
  `narratostudio/posterflow/provider_common.py`
- Reference branch deliberately not merged:
  `origin/codex/posterflow-minimax-provider-tests`
- Local worktree and both remote provider branches were deleted after
  integration.

### AFS-WEB-001: Web UI Parallel Lane Repair

Goal:

- Preserve the independent NarratoCut Web UI line without letting stale
  branch/worktree state block future parallel development.

Acceptance criteria:

- [x] Broken worktree metadata from the old `D:\Projects\NarratoCut` path is
      repaired.
- [x] The worktree is moved under the AgentFlowStudio global worktree root.
- [x] Uncommitted Web UI M3.1 production workbench changes are committed and
      pushed to `origin/codex/narratocut-web-ui`.
- [x] The branch is explicitly classified as preserved but not merge-ready.
- [x] Verification evidence is recorded before the branch is treated as
      backed up.

Verification:

```powershell
python -m pytest tests/test_web_static_artifact_viewer.py tests/test_web_production_mode_static.py tests/test_web_production_bridge.py
# 41 passed

python -m pytest
# 374 passed

python -m apps.cli.main --help
# passed

python -m apps.cli.main version
# 0.1.0

node --check apps/web/app.js
node --check apps/web/app-elements.js
node --check apps/web/feedback-wiring.js
node --check apps/web/feedback-event.js
node --check apps/web/production-mode.js
node --check apps/web/production-render.js
node --check apps/web/production-workflows.js
node --check apps/web/artifact-values.js
node --check apps/web/video-preview.js
# passed

python -m compileall apps/web_bridge apps/cli narratocut/workflow_engine tests
# passed

git diff --check
# passed
```

Status:

- archived at tag `archive/narratocut-web-ui-de8ca8e`; useful work replayed by
  `AFS-WEB-REPLAY`; local and remote branches deleted

Evidence:

- Archive tag: `archive/narratocut-web-ui-de8ca8e`
- Replay integration: `AFS-WEB-REPLAY` at `5d0392f`
- Old worktree, local branch, and remote branch were deleted after replay and
  final verification.

## Planned Worktree Layout

Use global worktrees for implementation tracks:

```text
C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\<branch-slug>
```

The main checkout should stay stable for scan, sync, and final integration.

## Completion Rules

Do not mark a task complete unless:

- implementation or documentation change is done;
- acceptance criteria are checked;
- verification command results are recorded;
- generated artifacts or evidence paths are listed when relevant;
- follow-up work is moved into this tracker or backlog;
- reusable experience is considered for Company memory promotion.
