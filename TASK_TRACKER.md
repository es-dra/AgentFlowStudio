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
| AFS-WEB-001 | `codex/narratocut-web-ui` / `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\narratocut-web-ui` | Worker + QA | Preserve and classify the independent NarratoCut Web UI line after repository rename | preserved parallel branch | Web UI targeted tests -> 41 passed; branch full `pytest` -> 374 passed; CLI help/version; JS syntax checks; `compileall`; `git diff --check` | Pushed at `de8ca8e`; worktree repaired and moved; branch still diverges from `master` and must be rebased or replayed before integration |
| AFS-OPS-002 | main checkout | Orchestrator + Docs Projection Agent | Add project execution entry points for agent roster, task brief, provider gates, and Company feedback | completed | `git diff --check`; `python -m pytest tests/test_agentflow_roadmap_docs.py` -> 8 passed; CLI help/version | Documents-only operating-system pass; no runtime code or provider calls |

## Integration Gate

Current gate:

- `AFS-MEM-001`, `AFS-CTX-001`, and `AFS-QLT-001` are integrated to `master`.
- `AFS-DEMO-001` is integrated to `master` at `ff77b30`.
- `AFS-PROV-001` is integrated to `master` at `649d736`.
- `AFS-ALPHA-001` is integrated to `master` at `ac2254e`.
- Remaining active work is the independent Web UI line
  `origin/codex/narratocut-web-ui` at `de8ca8e`.
- Do not merge the Web UI line directly. It is preserved and backed up, but
  still diverges from `master`; the next integration step is a fresh
  rebase/replay branch with Python 3.12 verification.
- `AFS-OPS-002` is an operating-system projection pass in the main checkout.
  It must finish before opening the next batch of parallel implementation
  worktrees.

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
after `AFS-OPS-002` verification is recorded.

| ID | Suggested branch / worktree | Owner role | Primary write scope | Initial verification |
|---|---|---|---|---|
| AFS-PROD-001 | `codex/afs-prod-alpha-smoke` / `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-prod-alpha-smoke` | Workflow Engineer | `apps/cli/`, workflow docs, focused tests | `tests/test_video_to_finished_package_local_asr_workflow.py`, `tests/test_narratostudio_workflow.py`, `tests/test_posterflow_provider.py`, CLI help/version |
| AFS-QA-001 | `codex/afs-quality-evidence-summary` / `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-quality-evidence-summary` | Harness / QA Reviewer | `agentflow/harness/`, `narratocut/harness/`, quality tests | `tests/test_agent_reviewer.py`, `tests/test_harness_quality_checks.py`, `tests/test_posterflow_quality.py`, `tests/test_narratostudio_review_hardening.py` |
| AFS-MEM-002 | `codex/afs-memory-promotion-review` / `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-memory-promotion-review` | Memory / Evidence Steward | `agentflow/memory/`, PosterFlow/NarratoStudio memory tests | `tests/test_agentflow_asset_memory_validator.py`, `tests/test_narratostudio_asset_reuse_chain_audit_smoke.py`, `tests/test_posterflow_quality.py` |
| AFS-WEB-REPLAY | `codex/afs-web-ui-replay` / `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-web-ui-replay` | Web UI Agent + Release Integrator | `apps/web`, `apps/web_bridge`, Web UI tests | Web UI targeted tests, Python 3.12 full relevant suite, JS syntax checks |

Integration order should prefer `AFS-PROD-001` or `AFS-QA-001` first because
they create better artifact summaries for later Web UI replay.

Current dispatch:

| ID | Branch | Worker |
|---|---|---|
| AFS-PROD-001 | `codex/afs-prod-alpha-smoke` | subagent `019e6549-7170-72c3-b588-8eecf1b05784` (`Dewey`) |
| AFS-QA-001 | `codex/afs-quality-evidence-summary` | subagent `019e6549-8563-72b0-b6fb-6f5a486b5d52` (`Nietzsche`) |
| AFS-MEM-002 | `codex/afs-memory-promotion-review` | subagent `019e6549-9a28-79a1-92be-d7e39a082350` (`Mencius`) |
| AFS-WEB-REPLAY | `codex/afs-web-ui-replay` | main controller until a worker slot is free |

All four branches were created from `6d0cf88 docs: add agent operating entry
points`.

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
| `origin/codex/narratocut-web-ui` | preserved independent Web UI line | Keep. Worktree repaired and moved to the AgentFlowStudio path; next action is rebase/replay before any merge to `master`. |

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
- Company memory update: `Company/60-assets-and-memory/02-失败归因与反模式库.md`

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
  `D:\Learning materials\Learning_notes\Company\60-assets-and-memory\02-失败归因与反模式库.md`

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

- preserved parallel branch at `de8ca8e`; not integrated to `master`

Evidence:

- Worktree:
  `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\narratocut-web-ui`
- Branch: `codex/narratocut-web-ui`
- Remote: `origin/codex/narratocut-web-ui`
- Current integration note: rebase or replay the branch on current `master`
  before opening a PR or merging. The old verification ran under Python 3.13.5;
  integration verification should rerun under Python 3.12.

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
