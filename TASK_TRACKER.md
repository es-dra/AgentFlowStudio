# AgentFlow Studio Task Tracker

Last updated: 2026-05-25 by Codex

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
| AFS-QLT-001 | `codex/quality-feedback-signals` | Worker + QA | Add failure attribution / quality feedback signal path for Memory OS learning loop | planned | harness quality tests | Should not block context trace |
| AFS-DEMO-001 | `codex/posterflow-two-round-demo` | Worker + QA + human reviewer | Build a true two-round PosterFlow Memory OS demo with comparison report | planned | PosterFlow workflow/quality/provider tests; inspect/review artifacts | Starts after memory/context artifacts stabilize |

## Integration Gate

Current gate:

- `AFS-MEM-001` and `AFS-CTX-001` are integrated to `master`.
- The next code track can start, but `AFS-QLT-001` must begin by splitting or
  refactoring `narratocut/harness/posterflow_quality.py`.
- Before `AFS-QLT-001`, split or refactor
  `narratocut/harness/posterflow_quality.py`; it is close to the 300-line
  project limit.

## Remote Branch Hygiene

Current branch classification as of 2026-05-25:

| Branch | Classification | Next action |
|---|---|---|
| `origin/codex/memory-os-loop` | integrated to `master` | Deleted after fast-forward merge and verification. |
| `origin/codex/posterflow-memory-demo` | stale pre-merge PosterFlow demo branch | Compare against PR #71 history; likely delete after confirming no unique changes are needed. |
| `origin/codex/posterflow-minimax-provider-tests` | unintegrated provider branch | Keep as candidate future provider track. |
| `origin/codex/alpha-readiness-evidence` | unintegrated docs/evidence branch stacked with MiniMax provider changes | Keep until split or reviewed. |
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

- implemented as a stacked follow-up on `codex/memory-os-loop`; pending final
  integration / commit flow

Evidence:

- Worktree: `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\memory-os-loop`
- Project record: `DEVLOG.md` in the implementation worktree

Follow-up:

- Before starting `AFS-QLT-001`, either integrate this stacked branch or
  explicitly continue stacked. `narratocut/harness/posterflow_quality.py` is at
  285 lines and should be split before adding more quality checks.

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
