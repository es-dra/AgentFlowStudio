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

Mainline is the stable integration surface. Local Alpha 0.2 is integrated and
cleaned up. Local Alpha 0.3 engineering acceptance is integrated on `master`
for the planning boundary, Web operator loop, and Memory runtime contract.
PosterFlow live image smoke remains intentionally blocked until a local
image-provider environment is configured.

The next milestone is:

```text
AgentFlow Studio Local Alpha 0.4:
one real local product loop with evidence-to-memory reuse
```

The product loop for this milestone is:

```text
local content project brief
  + local ignored source media
  + optional local script / notes
  + local BGM
  -> production handoff or workflow plan
  -> local finished package run
  -> inspect / review / package report
  -> Web workbench artifact review
  -> operator acceptance feedback
  -> memory candidate
  -> explicit promotion decision
  -> context bundle for a second pass
```

Use `docs/local_alpha_0_4_product_loop_goals.md` as the milestone boundary and
`TASK_TRACKER.md` as the live project ledger. `AFS-PROD-LOOP-001` must create
the concrete scenario package before opening implementation worktrees.

Local Alpha 0.4 planned queue:

| ID | Purpose | Suggested branch | Status |
|---|---|---|---|
| AFS-PROD-LOOP-001 | Define the 0.4 scenario package and runbook | `codex/afs-prod-loop-brief` | ready after this planning baseline |
| AFS-RUN-PACKAGE-001 | Produce local runtime package evidence or an actionable blocker | `codex/afs-run-package-loop` | depends on scenario package |
| AFS-WEB-OPERATOR-002 | Adapt Web operator path to the 0.4 scenario | `codex/afs-web-operator-loop` | depends on scenario package |
| AFS-MEMORY-QUALITY-002 | Evaluate traceable evidence reuse in a second pass | `codex/afs-memory-quality-loop` | depends on runtime evidence shape |
| AFS-POSTER-LIVE-002 | Optional live image smoke or blocked evidence | `codex/afs-poster-live-002` | optional; blocked by missing local provider env |

Open 0.4 implementation worktrees only after a fresh brief records write scope,
verification, provider policy, evidence path, and integration order. Treat
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
