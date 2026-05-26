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

## Fast Entry Points

Use the lightest entry that fits the task:

- Small local question or one-file doc edit: `AGENTS.md` plus the touched file.
- Normal project work: `AGENTS.md`, this document, and `TASK_TRACKER.md`.
- Parallel or delegated work: also use `docs/agent_operating_roster.md` and
  `docs/agent_task_brief_template.md`.
- Company-rule change: edit the source rule in `Company/` first, then project
  only the execution-facing subset back into this repository.

The goal is to reduce routing overhead. Do not reread every Company document
for routine implementation after the relevant source rule has already been
projected here.

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

Subagents are task-scoped. Close them after the assigned artifact, review, or
QA result is collected. If the agent manager reports an old agent ID as
`not found`, treat it as inactive history rather than an open workstream.

Use `docs/agent_operating_roster.md` for role selection and
`docs/agent_task_brief_template.md` for the brief passed to workers or
reviewers.

### Provider Capability Gates

Remote-provider policy must name the capability:

| Capability | Default | Required gate |
|---|---|---|
| LLM | off | `NARRATOCUT_ALLOW_REMOTE_LLM=true` |
| ASR | off | `NARRATOCUT_ALLOW_REMOTE_ASR=true` |
| image generation | off | `NARRATOCUT_ALLOW_REMOTE_IMAGE=true` |
| video generation | off | task-specific explicit approval until a project gate exists |
| external download | off | task-specific source and artifact policy |

Authorization for one capability does not authorize another. Tests and dry-run
validators should prefer mocked providers unless a task explicitly requests a
live provider smoke.

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

## Current Product Push

Mainline is the stable integration surface. The previous parallel development
batch is complete: alpha smoke, evidence summary, memory promotion review, and
the local Web workbench are integrated into `master`; old Web UI branch state is
archived and cleaned.

The next milestone is:

```text
AgentFlow Studio Local Alpha 0.2:
evidence-driven local AI content production workbench
```

The product loop for this milestone is:

```text
brief / local media
  -> workflow plan
  -> supervised local run
  -> artifacts
  -> inspect / review / package report
  -> Web workbench acceptance
  -> feedback event
  -> memory candidate
  -> next-round context reuse
```

For exact verification and branch hygiene state, use `TASK_TRACKER.md` as the
live project ledger.

Current recommended parallel queue:

| ID | Purpose | Suggested branch | Status |
|---|---|---|---|
| AFS-ALPHA-PKG-001 | Turn existing evidence into a coherent local Alpha acceptance package | `codex/afs-alpha-package` | ready to open |
| AFS-WEB-UX-001 | Productize the local Web workbench for repeated real use | `codex/afs-web-ux-pass` | ready to open |
| AFS-MEMORY-DEMO-001 | Harden the two-round Memory OS demonstration without claiming durable memory runtime | `codex/afs-memory-demo-hardening` | ready to open |
| AFS-POSTER-LIVE-001 | Prepare or run the gated PosterFlow live image smoke without committing secrets or runtime artifacts | `codex/afs-poster-live-smoke` | ready to open |

Start these in separate worktrees only after the matching task brief records
write scope, verification, provider policy, and integration order. Treat
`docs/task_briefs/` as the copy-paste source for delegated workers.

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
