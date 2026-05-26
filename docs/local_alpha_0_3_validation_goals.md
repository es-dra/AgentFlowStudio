# AgentFlow Studio Local Alpha 0.3 Validation Goals

Date: 2026-05-27

Current status: engineering acceptance integrated on `master` for
`AFS-PROD-NEXT-001`, `AFS-WEB-REVIEW-001`, and
`AFS-MEMORY-RUNTIME-001`. `AFS-POSTER-LIVE-002` remains blocked by missing
local image-provider environment and is not required for the local-only
engineering pass.

## Purpose

Local Alpha 0.3 validates whether AgentFlow Studio can support a repeatable
local operator loop, not just isolated engineering evidence.

The milestone question is:

```text
Can one local operator select a workflow, run it under supervision, inspect the
artifacts, record acceptance feedback, and reuse accepted evidence in the next
round without confusing tests, human acceptance, product validation, or durable
memory?
```

## Product Loop

The target loop is:

```text
local brief / local media
  -> workflow selection
  -> workflow plan
  -> supervised local run
  -> artifact inspection
  -> review report
  -> Web workbench acceptance event
  -> memory candidate
  -> explicit promotion decision
  -> context bundle / next-round prompt
```

This loop must remain local-first. Browser state, provider credentials,
generated media, and private Company knowledge must not be persisted in the
repository.

## Acceptance Pillars

### 1. Operator Workflow Acceptance

Acceptance criteria:

- A local operator can start from documented entry points instead of reading
  historical phase notes.
- At least one mock or local workflow can be planned, run, inspected, reviewed,
  and surfaced in the Web workbench.
- The Web workbench shows the current state and next action clearly enough for
  repeated use.
- Desktop and narrow-viewport browser smokes pass after UI changes.
- Review Mode still reads only explicitly selected local files.
- Production Mode still talks only to the local bridge at `127.0.0.1`.

Evidence:

- Browser-smoke notes or screenshot path outside the repository.
- Focused Web tests and JavaScript syntax checks.
- Review report or bridge run evidence for the selected workflow.

### 2. Evidence-To-Memory Loop Acceptance

Acceptance criteria:

- A feedback event remains the source evidence for memory candidates.
- Candidate memory artifacts point back to source feedback and run evidence.
- Promotion, rejection, merge, or expiry is an explicit review decision.
- Promotion artifacts do not write or claim durable long-term memory.
- The next-round context bundle or prompt visibly references accepted evidence.

Evidence:

- Memory candidate artifact.
- Promotion decision artifact.
- Context bundle and context assembly trace.
- Review checks that fail if the evidence chain is broken.

### 3. Runtime Reliability Acceptance

Acceptance criteria:

- `alpha-smoke --json` remains the first status command and does not write run
  artifacts or call providers.
- At least one local workflow reruns cleanly end to end on this machine.
- Failure states produce actionable reports, not silent pass states.
- Generated runtime artifacts and media stay ignored unless a task explicitly
  says otherwise.

Evidence:

- `alpha-smoke --json` output status.
- Focused pytest result for the selected workflow surface.
- CLI rerun, inspect, and review command results when the workflow is rerun.

### 4. Provider Boundary Acceptance

Acceptance criteria:

- PosterFlow live image smoke is `blocked` by default when image-provider env is
  not configured.
- A live image smoke runs only when the local task intentionally enables
  `NARRATOCUT_ALLOW_REMOTE_IMAGE=true`.
- Provider keys, base URLs, signed URLs, cookies, generated media, and private
  credentials are not committed.
- If provider env is absent, Local Alpha 0.3 may still pass with live image
  smoke explicitly recorded as blocked.

Evidence:

- Provider env checklist that does not print secrets.
- No-secret scan or staged-file review.
- `alpha-smoke --json` blocked/pass status with reason.

### 5. Company Operating-System Acceptance

Acceptance criteria:

- Fresh task briefs exist before opening implementation worktrees.
- Each lane has write scope, do-not-touch list, verification commands,
  provider policy, evidence path, and integration order.
- Subagents are task-scoped and closed after results are collected.
- The controller reproduces critical browser, provider-boundary, and no-secret
  claims before integration.
- Reusable lessons are recorded in project memory and considered for promotion
  to the private Company knowledge base.

Evidence:

- `TASK_TRACKER.md` queue state.
- `docs/task_briefs/` entries for the next lanes.
- DEVLOG, handoff, or tracker notes with verification and remaining risk.

## Overall Pass Criteria

Local Alpha 0.3 engineering acceptance can be marked accepted when all of the
following are true:

- [x] A documented local operator path can be followed from entry point to
      review result.
- [x] At least one local or mocked workflow completes plan/run/review through
      the Web or bridge surface.
- [x] Feedback-to-candidate-to-context evidence chain is visible and
      side-effect-free.
- [x] `alpha-smoke --json` reports accurate `pass`, `blocked`, or `fail`
      states without provider calls.
- [x] PosterFlow live image smoke is either completed under the explicit image
      gate or recorded as blocked by missing local env.
- [x] Browser smoke, focused tests, and `git diff --check` pass for changed
      surfaces.
- [x] Reports separate structure verification, runtime verification, human
      acceptance, business validation, and memory promotion.
- [x] All generated media, run artifacts, provider config, and private Company
      content remain out of committed files.

This is not commercial or human creative-quality validation. Those remain
outside the Local Alpha 0.3 engineering pass.

## Non-Claims

Local Alpha 0.3 does not claim:

- hosted SaaS readiness;
- durable Memory runtime;
- vector store, database, or RAG quality;
- autonomous AgentFlow Router runtime;
- skill runtime;
- mature creative quality;
- provider cost-quality optimization;
- publishing or distribution integration;
- business validation from real customers.

## Parallel Queue Outcome

This queue has been executed as the Local Alpha 0.3 engineering pass.

| ID | Branch | Owner role | Outcome |
|---|---|---|---|
| AFS-PROD-NEXT-001 | main checkout | Orchestrator + Product Lead | integrated |
| AFS-WEB-REVIEW-001 | `codex/afs-web-review-loop` | Web UI Agent + QA Reviewer | integrated |
| AFS-MEMORY-RUNTIME-001 | `codex/afs-memory-runtime-contract` | Memory / Evidence Steward | integrated |
| AFS-POSTER-LIVE-002 | not opened | Provider Adapter Agent + Security / Secret Audit Agent | blocked by missing local image-provider env |

Integration order:

```text
AFS-PROD-NEXT-001
  -> AFS-WEB-REVIEW-001 and AFS-MEMORY-RUNTIME-001 in parallel
  -> AFS-POSTER-LIVE-002 remained blocked by local provider boundary
  -> controller-side verification and project/company memory updates
```

## Controller Responsibilities

The controller must not treat worker reports as final evidence. Before merging
or marking a lane complete, reproduce or inspect:

- browser smoke claims;
- provider-boundary and no-secret claims;
- evidence-chain claims;
- generated artifact staging state;
- task brief acceptance criteria.
