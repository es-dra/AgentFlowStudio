# Agent Operating Roster

This document defines how AgentFlow Studio uses agent roles, subagents, and
worktrees during development. It is an execution surface, not the private
10-Startup source of truth.

Source rules remain in:

```text
D:\Learning materials\Learning_notes\10-Startup
```

## Current State

- Main checkout: `D:\Projects\AgentFlowStudio`, kept on `master` for scan,
  integration, and final verification.
- Worktree root:
  `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\`.
- Current branch state: active maintenance work is on
  `codex/afs-product-spine-reset-003`; `master` / `origin/master` remain the
  integration baselines.
- Subagents are ephemeral task workers. A visible historical agent card in the
  UI is not an active lane unless the agent manager can still resume or close
  the ID.

## Entry Rule

For small single-file documentation edits, `AGENTS.md` plus targeted context is
enough.

For substantial work, use this sequence:

```text
AGENTS.md
  -> docs/company_operating_model.md
  -> TASK_TRACKER.md
  -> docs/agent_operating_roster.md
  -> docs/agent_task_brief_template.md
```

Do not make a new parallel branch until the task brief has a write scope,
verification command, provider policy, and integration order.

## Standing Roles

| Role | Responsibility | Default artifact |
|---|---|---|
| Orchestrator | Split work, assign worktrees, protect main checkout, integrate results | Updated `TASK_TRACKER.md` and handoff summary |
| Contract Engineer | Maintain `agentflow` contracts, schema examples, router/skill validators | Contract diff plus focused tests |
| Workflow Engineer | Maintain workflow engine nodes, YAML workflows, CLI workflow path | Workflow diff plus runner/loader tests |
| Harness / QA Reviewer | Maintain inspect/review gates, quality reports, evidence vocabulary | Review report and verification matrix |
| Memory / Evidence Steward | Maintain feedback source, candidate memory, promotion decisions, context traces | Memory decision artifact with evidence refs |
| Release Integrator | Rebase/replay branches, run final verification, clean branch/worktree state | Integration record and branch hygiene update |

These are roles, not always-running agents. Assign them to a human, the main
controller, or a fresh subagent for the current task.

## Temporary Roles

| Role | Use when | Guardrail |
|---|---|---|
| Provider Adapter Agent | ASR, image, LLM, or video provider behavior changes | Must name the capability gate and avoid live calls unless opted in |
| Web UI Agent | Improve transitional `apps/web` read-only artifact views or frontend integration docs | Must keep browser state local-only and avoid provider secrets or persistence |
| Media QA Agent | Real video, subtitle, BGM, cover, or package artifact checks | Must separate runtime verification from human acceptance |
| Security / Secret Audit Agent | Config, provider, release, or publishing-sensitive work | Must inspect for secrets and private paths before integration |
| Docs Projection Agent | Company-to-project rule projection or public docs alignment | Must not copy confidential Company content into the repo |

## Dispatch Triggers

Use subagents when at least one condition is true:

- there are two or more independent workstreams;
- an implementation and a review can run in parallel without sharing writes;
- a branch needs read-only audit while the main controller continues another
  task;
- a UI, provider, media, or security lane needs a focused specialist view.

Keep work local when:

- the next action is blocked on one answer;
- the write scope overlaps a shared contract or CLI entry point;
- the task is a tiny deterministic edit;
- a bug root cause is still unclear and parallel workers would duplicate
  investigation.

## Subagent Lifecycle

1. Give the subagent a completed task brief.
2. Require a concrete artifact: diff, plan, test output, review report,
   evidence summary, or handoff.
3. Verify the returned result from the main controller before integration.
4. Record durable lessons in `DEVLOG.md`, `TASK_TRACKER.md`, or Company memory
   candidates.
5. Close the subagent after its result is collected. If a close attempt returns
   `not found`, record that the agent is inactive history.

Do not keep generic subagents open just because the project is agent-native.
Idle agents create stale context, not capacity.

## Current Parallel Queue Status

| ID | Suggested branch | Owner role | Primary scope | Dependency |
|---|---|---|---|---|
| AFS-PRODUCT-SPINE-RESET-003 | `codex/afs-product-spine-reset-003` | Maintainability Steward + Architecture Reset Lead | Delete retired surfaces and remove package cycles | Active |
| AFS-RUNTIME-SERVICE-V0-2-001 | master / current branch | Runtime/API Integrator | Runtime Service and frontend-safe API contract | Integrated baseline |
| AFS-FRONTEND-WORKBENCH-INTEGRATION-001 | external frontend branch | Web UI Agent + Runtime/API Integrator | External canvas workbench -> Runtime Service | Pending external frontend handoff |

Open the next queue as separate worktrees only if their write scopes remain disjoint.
When a shared contract becomes unstable, stop parallel implementation and assign
one Contract Engineer owner first.
