# AgentFlow Studio Task Tracker

Last updated: 2026-05-26 by Codex

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

## Integration Gate

Current gate:

- `AFS-MEM-001`, `AFS-CTX-001`, and `AFS-QLT-001` are integrated to `master`.
- `AFS-DEMO-001` is integrated to `master` at `ff77b30`.
- `AFS-PROV-001` is integrated to `master` at `649d736`.
- Remaining active work is outside PosterFlow provider integration:
  `origin/codex/alpha-readiness-evidence` and
  `origin/codex/narratocut-web-ui`.

## Remote Branch Hygiene

Current branch classification as of 2026-05-26:

| Branch | Classification | Next action |
|---|---|---|
| `origin/codex/memory-os-loop` | integrated to `master` | Deleted after fast-forward merge and verification. |
| `origin/codex/quality-feedback-signals` | integrated to `master` | Deleted after fast-forward merge and verification. |
| `origin/codex/posterflow-memory-demo` | patch-equivalent stale pre-merge PosterFlow demo branch | Deleted after `git cherry -v master codex/posterflow-memory-demo` showed the branch patch is already in `master`. |
| `origin/codex/posterflow-minimax-provider-tests` | stale provider reference branch | Deleted after `AFS-PROV-001` replaced it on current `master`. |
| `origin/codex/posterflow-minimax-rebase` | integrated replacement provider branch | Deleted after fast-forward integration and verification. |
| `origin/codex/alpha-readiness-evidence` | unintegrated docs/evidence branch stacked with old MiniMax provider changes | Keep until split or reviewed; do not merge before separating stale provider changes. |
| `origin/codex/narratocut-web-ui` | independent Web UI line | Keep, but repair or recreate its worktree under the AgentFlowStudio path before further development. |

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

- implemented in worktree; pending final integration / commit flow

Evidence:

- Worktree: `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\memory-os-loop`
- Branch: `codex/memory-os-loop`
- Project record: `DEVLOG.md` in the implementation worktree
- Company memory update: `Company/60-assets-and-memory/02-失败归因与反模式库.md`

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
