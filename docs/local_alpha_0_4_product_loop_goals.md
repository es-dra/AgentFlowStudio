# AgentFlow Studio Local Alpha 0.4 Product Loop Goals

Date: 2026-05-27

Current status: ready for planning and dispatch. Local Alpha 0.3 proved the
local engineering loop: workflow selection, supervised run, review refresh,
feedback capture, and evidence-to-context reuse. Local Alpha 0.4 raises the
bar from engineering loop to one real product loop.

## Purpose

Local Alpha 0.4 validates whether AgentFlow Studio can support one real local
product loop for a concrete content-production scenario.

This milestone is one real local product loop, not a general platform push.

The milestone question is:

```text
Can one local operator start from a real project brief and local media, produce
a reviewable content package, accept or reject the result, and reuse accepted
evidence in a second pass without hiding provider, memory, quality, or human
review boundaries?
```

This is still local Alpha. It is not SaaS readiness, customer validation, or
mature creative-quality proof.

## Target Scenario

Use one named internal scenario for the first 0.4 product loop:

```text
local content project brief
  + local ignored source video
  + optional local script / notes
  + local BGM
  -> production handoff or workflow plan
  -> NarratoCut local finished package run
  -> inspect / review / package report
  -> Web workbench artifact review
  -> operator acceptance feedback
  -> memory candidate / promotion decision
  -> context bundle for a second pass
```

The exact local media stays outside git. The committed repository may contain
only example schemas, runbooks, tests, docs, and non-secret templates.

## Acceptance Pillars

### 1. Product Scenario Acceptance

Acceptance criteria:

- A single scenario document names the target user job, local inputs, expected
  outputs, and acceptance checklist.
- Required local media paths are explicit and ignored by git.
- The runbook starts from current docs instead of historical phase notes.
- The scenario can be executed without remote LLM, ASR, image, or video
  providers unless a later task explicitly opts in.
- The scenario records non-claims: no SaaS, no customer validation, no mature
  editorial judgment, no durable Memory runtime.

Evidence:

- `docs/local_alpha_0_4_product_loop_goals.md`.
- A scenario package or runbook created by `AFS-PROD-LOOP-001`.
- `alpha-smoke --json` status.

### 2. Local Runtime Package Acceptance

Acceptance criteria:

- At least one real local run produces a finished package or a clearly blocked
  status with actionable missing-local-input reasons.
- Inspect, review, and package report outputs are linked from the run evidence.
- Generated media and run artifacts remain ignored and unstaged.
- Failure states are explicit and do not look like product acceptance.
- The runtime package can be re-run from documented commands.

Evidence:

- Runtime evidence paths under ignored `data/processed/` or `data/reports/`.
- CLI output summary recorded in handoff docs.
- Focused workflow and review tests.

### 3. Web Operator Acceptance

Acceptance criteria:

- The Web workbench can guide the operator through the 0.4 scenario path, not
  only a mock workflow.
- Production Mode still talks only to the local bridge at `127.0.0.1`.
- Review Mode still reads only explicitly selected local files.
- Feedback capture includes review and package evidence refs when available.
- Desktop and narrow-viewport browser smokes pass after UI changes.
- No browser persistence, uploads, SaaS backend, provider config, or account
  state is added.

Evidence:

- Focused Web tests and JavaScript syntax checks.
- Browser-smoke notes or screenshot path outside the repository.
- Web handoff for `AFS-WEB-OPERATOR-002`.

### 4. Evidence-To-Memory Reuse Acceptance

Acceptance criteria:

- Operator feedback remains the source evidence for memory candidates.
- Candidate, promotion decision, context bundle, and next-pass prompt remain
  auditable side-effect-free artifacts.
- The second pass clearly shows what accepted evidence was reused.
- The evaluation measures traceability first. It may record human preference,
  but it must not claim quality improvement without comparison evidence.
- No durable memory write, database, vector store, RAG service, or hosted
  Memory runtime is added.

Evidence:

- Memory candidate, promotion decision, context bundle, and trace artifacts.
- Focused tests or audit checks that fail on broken evidence references.
- Handoff for `AFS-MEMORY-QUALITY-002`.

### 5. Provider Boundary Acceptance

Acceptance criteria:

- PosterFlow live image smoke remains optional for 0.4.
- If image-provider env is absent, the live lane stays `blocked` and does not
  block the local product loop.
- If image-provider env is intentionally configured, the task must use
  `NARRATOCUT_ALLOW_REMOTE_IMAGE=true` and record no-secret / no-artifact
  staging evidence.
- A provider smoke never counts as creative-quality or business validation.

Evidence:

- `alpha-smoke --json`.
- `docs/handoff/AFS-POSTER-LIVE-002.md` if the lane is reopened.

## Overall Pass Criteria

Local Alpha 0.4 can be marked accepted when all of the following are true:

- [ ] A named product scenario has a clear runbook, local input policy, and
      acceptance checklist.
- [ ] A local product run either completes to reviewable package evidence or
      reports an actionable local-input blocker.
- [ ] The Web workbench can guide the operator through scenario review and
      feedback without browser persistence or remote services.
- [ ] Feedback-to-memory-to-context reuse is visible in a second pass or in a
      documented blocked state with the missing evidence named.
- [ ] `alpha-smoke --json` remains accurate and side-effect-free.
- [ ] Browser smoke, focused tests, compile/syntax checks, and `git diff
      --check` pass for changed surfaces.
- [ ] Reports separate structure verification, runtime verification, human
      acceptance, business validation, provider smoke, and memory promotion.
- [ ] Generated media, run artifacts, provider config, secrets, and private
      Company knowledge remain out of committed files.

## Non-Claims

Local Alpha 0.4 does not claim:

- hosted SaaS readiness;
- customer or market validation;
- durable Memory runtime;
- vector store, database, or RAG quality;
- autonomous AgentFlow Router or skill runtime;
- mature creative or editorial judgment;
- provider cost-quality optimization;
- publishing or distribution integration.

## Planned Queue

| ID | Suggested branch | Owner role | Primary outcome | Dependency |
|---|---|---|---|---|
| AFS-PROD-LOOP-001 | `codex/afs-prod-loop-brief` | Orchestrator + Product Lead | 0.4 scenario package and runbook | first |
| AFS-RUN-PACKAGE-001 | `codex/afs-run-package-loop` | Workflow Engineer + Harness / QA Reviewer | Local runtime package or actionable blocker | after scenario package |
| AFS-WEB-OPERATOR-002 | `codex/afs-web-operator-loop` | Web UI Agent + QA Reviewer | Web path for the 0.4 scenario | after scenario package |
| AFS-MEMORY-QUALITY-002 | `codex/afs-memory-quality-loop` | Memory / Evidence Steward | Traceable evidence reuse evaluation | after runtime evidence shape is known |
| AFS-POSTER-LIVE-002 | `codex/afs-poster-live-002` | Provider Adapter Agent + Security / Secret Audit Agent | Optional live image smoke or blocked evidence | optional |

Integration order:

```text
AFS-PROD-LOOP-001
  -> AFS-RUN-PACKAGE-001 and AFS-WEB-OPERATOR-002 in parallel
  -> AFS-MEMORY-QUALITY-002 after the runtime evidence shape is stable
  -> AFS-POSTER-LIVE-002 only if local image-provider env is intentionally configured
  -> controller-side verification, branch cleanup, and memory promotion review
```

## Controller Responsibilities

The controller must reproduce critical evidence before integration:

- browser smoke claims;
- local runtime package or blocked-input claims;
- provider-boundary and no-secret claims;
- generated artifact staging state;
- evidence-to-memory trace claims;
- task brief acceptance criteria.
