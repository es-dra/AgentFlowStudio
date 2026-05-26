# Company Operating Model Projection

This document is the AgentFlow Studio execution-facing projection of the local
company knowledge base.

The source-of-truth company rules live outside this repository:

```text
D:\Learning materials\Learning_notes\Company
```

This repository should contain only the subset needed to execute AgentFlow
Studio work safely. Do not copy confidential company strategy, private
retrospectives, real costs, customer information, provider secrets, or
unpublished business assumptions into this repo.

## Rule Hierarchy

Use this hierarchy when instructions appear in more than one place:

```text
Company source knowledge base
  -> global workflow skills
  -> project AGENTS.md
  -> task tracker / branch handoff
  -> local task prompt
```

### Company Source Knowledge Base

Purpose: durable company rules, strategy, operating system, research reserve,
asset memory, and private retrospectives.

Location:

```text
D:\Learning materials\Learning_notes\Company
```

Relevant current source areas:

- `00-company-os/`: company charter, knowledge governance, confidentiality,
  company memory.
- `20-operating-system/`: AI-native company operating model, task splitting,
  weekly cadence.
- `30-engineering/`: project development, worktree/subagent coordination,
  quality gates, release rules.
- `40-agent-workforce/`: agent roles and task templates.
- `60-assets-and-memory/`: reusable company assets, memory promotion, failure
  patterns.

### Global Workflow Skills

Purpose: executable rules used by coding agents across projects.

Current roles:

- The installed `project-development-workflow` skill remains the active project
  startup and engineering discipline used by Codex in concrete repositories.
- `Company/Workflow/ai-native-company-workflow/` is the newer company-level
  source-aligned workflow. It should guide future updates to installed skills
  and project rules.
- `Company/Workflow/project-development-workflow/` is legacy reference material.
  Reuse durable ideas, but do not treat it as the highest source.
- `Company/Workflow/research-coding-workflow/` is retained as research reserve
  for model, experiment, benchmark, and paper-sensitive work.

### Project AGENTS.md

Purpose: repo-local execution rules for AgentFlow Studio.

`AGENTS.md` should stay concise and execution-facing. It should not become a
copy of the private company knowledge base.

### TASK_TRACKER.md

Purpose: current multi-session task state for this repository.

It should track branch/worktree, owner role, write scope, acceptance criteria,
verification, evidence, and handoff status. A task is not complete just because
code was written.

## Worktree Policy

Keep the main checkout stable for scan, sync, and integration.

Use global worktrees for nontrivial or parallel development:

```text
C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\<branch-slug>
```

Use `codex/*` branch names by default.

Parallel work is allowed only when:

- write scopes do not overlap;
- verification commands are known;
- shared contracts have an owner;
- integration order is clear;
- remote provider calls remain explicitly gated.

Preserved branches need an extra gate:

- repair or move old worktrees after repository renames;
- compare divergence against `master`;
- push useful checkpoints for backup;
- classify the branch as `integrated`, `preserved`, `stale`, or `delete`;
- rebase or replay preserved branches before integration.

## Agent Work Policy

Subagent or delegated work must have:

- goal;
- non-goals;
- branch/worktree;
- write scope;
- do-not-touch list;
- acceptance criteria;
- verification commands;
- expected artifacts;
- remote-provider policy;
- return format.

Review order:

```text
spec compliance
  -> code quality
  -> QA / artifact verification
  -> integration
```

## Quality And Evidence

Separate these levels in reports:

- structure verification: tests, schema, compile, diff checks;
- runtime verification: CLI/workflow run and generated artifacts;
- human acceptance: reviewed output satisfies the intended task;
- business validation: real user or market signal.

For Memory OS work, keep these boundaries explicit:

- feedback source of truth is not the same as derived feedback signals;
- memory candidate is not durable memory;
- project prefix is not a complete memory runtime;
- context bundle existence does not prove context selection quality;
- demo success is not product validation.

## Current Parallel Tracks

Current tracked lanes:

| Branch | Purpose | Primary write scope | Status |
|---|---|---|---|
| `codex/company-os-projection` | Project-facing projection of company rules | `AGENTS.md`, `docs/company_operating_model.md`, `TASK_TRACKER.md` | completed |
| `codex/memory-os-loop` | Feedback to memory review to preference/profile/prefix loop | `agentflow/memory`, `narratostudio/posterflow`, tests | integrated |
| `codex/context-runtime-trace` | Minimal `context_bundle` and `context_assembly_trace` artifacts | `agentflow/context`, examples, tests | integrated with memory loop |
| `codex/quality-feedback-signals` | Failure attribution and quality feedback signal contracts | harness and quality tests | integrated |
| `codex/posterflow-two-round-demo` | True two-round Memory OS demo and comparison report | PosterFlow workflow/report/tests | integrated |
| `codex/posterflow-minimax-rebase` | MiniMax image provider replay on current mainline | `narratostudio/posterflow`, tests | integrated and branch cleaned |
| `codex/alpha-readiness-rebase` | Alpha readiness evidence replay on current mainline | docs, examples, tests | integrated and branch cleaned |
| `codex/narratocut-web-ui` | Independent local Web UI workbench | `apps/web`, `apps/web_bridge`, Web UI tests | preserved; rebase/replay required before merge |

For exact verification and branch hygiene state, use `TASK_TRACKER.md` as the
live project ledger.

## Promotion Back To Company

Project experience may be promoted back to `Company/` only when it is reusable
outside this repository.

Promotion candidates include:

- confirmed multi-agent workflow rules;
- worktree conflict patterns;
- reusable task templates;
- failure patterns;
- quality gates that prevented real regressions;
- Memory OS demo evidence and lessons.

Do not promote one-off observations, unverified AI suggestions, or single demo
successes as company rules.
