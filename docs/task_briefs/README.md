# AgentFlow Studio Task Briefs

Task briefs are copy-paste execution packets for parallel workers and future
agents. Use them after reading `AGENTS.md`, `docs/company_operating_model.md`,
`TASK_TRACKER.md`, and `docs/agent_operating_roster.md`.

Current queue state:

- Local Alpha 0.2 briefs below are completed historical briefs.
- Local Alpha 0.3 planning, Web review loop, and memory runtime contract briefs
  have been executed and integrated on `master`; the accepted 0.3 evidence is
  recorded in
  [`../local_alpha_0_3_validation_goals.md`](../local_alpha_0_3_validation_goals.md).
- Local Alpha 0.4 has completed its first runtime/Web/memory structural loop.
  Start from
  [`../local_alpha_0_4_product_loop_goals.md`](../local_alpha_0_4_product_loop_goals.md).
- `AFS-PROD-LOOP-001` has produced the concrete scenario package at
  [`../local_alpha_0_4_scenario_package.md`](../local_alpha_0_4_scenario_package.md).
  The acceptance reconciliation is recorded at
  [`../local_alpha_0_4_acceptance_reconciliation.md`](../local_alpha_0_4_acceptance_reconciliation.md).

Local Alpha 0.4 queue state:

| ID | Brief | Purpose |
|---|---|---|
| AFS-PROD-LOOP-001 | [AFS-PROD-LOOP-001.md](AFS-PROD-LOOP-001.md) | 0.4 product scenario package and runbook |
| AFS-RUN-PACKAGE-001 | [AFS-RUN-PACKAGE-001.md](AFS-RUN-PACKAGE-001.md) | Local runtime package or actionable blocker |
| AFS-WEB-OPERATOR-002 | [AFS-WEB-OPERATOR-002.md](AFS-WEB-OPERATOR-002.md) | Web operator path for the 0.4 scenario |
| AFS-MEMORY-QUALITY-002 | [AFS-MEMORY-QUALITY-002.md](AFS-MEMORY-QUALITY-002.md) | Traceable evidence reuse evaluation |
| AFS-POSTER-LIVE-002 | [AFS-POSTER-LIVE-002.md](AFS-POSTER-LIVE-002.md) | Optional live image smoke or blocked evidence |

Do not reopen `AFS-MEMORY-QUALITY-002` just to repeat the structural review.
Use a new brief for memory-review CLI, Web evidence summary, real second-pass
run, or human acceptance feedback.

Post-retro stabilization queue:

The current productization direction is summarized in
[`../handoff/AFS-POST-DEMO-PRODUCTIZATION-ROADMAP.md`](../handoff/AFS-POST-DEMO-PRODUCTIZATION-ROADMAP.md).
The memory workbench design is recorded in
[`../workbench/AFS-WORKBENCH-REDESIGN-001.md`](../workbench/AFS-WORKBENCH-REDESIGN-001.md).

| ID | Brief | Purpose |
|---|---|---|
| AFS-MAINTENANCE-RESET-001 | [AFS-MAINTENANCE-RESET-001.md](AFS-MAINTENANCE-RESET-001.md) | Classify and reduce dirty worktree sprawl before more implementation |
| AFS-MEMORY-PIPELINE-MVP-001 | [AFS-MEMORY-PIPELINE-MVP-001.md](AFS-MEMORY-PIPELINE-MVP-001.md) | Replace numbered demo execution with one protocol-driven memory video pipeline |
| AFS-WORKBENCH-REDESIGN-001 | [AFS-WORKBENCH-REDESIGN-001.md](AFS-WORKBENCH-REDESIGN-001.md) | Design the memory production workbench before Web implementation |
| AFS-WORKBENCH-IMPLEMENTATION-001 | [AFS-WORKBENCH-IMPLEMENTATION-001.md](AFS-WORKBENCH-IMPLEMENTATION-001.md) | Implement the static memory workbench first screen from a safe package fixture |

Completed Local Alpha 0.2 queue:

| ID | Brief | Purpose |
|---|---|---|
| AFS-ALPHA-PKG-001 | [AFS-ALPHA-PKG-001.md](AFS-ALPHA-PKG-001.md) | Local Alpha acceptance package |
| AFS-WEB-UX-001 | [AFS-WEB-UX-001.md](AFS-WEB-UX-001.md) | Web workbench usability pass |
| AFS-MEMORY-DEMO-001 | [AFS-MEMORY-DEMO-001.md](AFS-MEMORY-DEMO-001.md) | Memory OS demo hardening |
| AFS-POSTER-LIVE-001 | [AFS-POSTER-LIVE-001.md](AFS-POSTER-LIVE-001.md) | Gated PosterFlow live-smoke path |

Completed / blocked Local Alpha 0.3 queue:

| ID | Brief | Purpose |
|---|---|---|
| AFS-PROD-NEXT-001 | [AFS-PROD-NEXT-001.md](AFS-PROD-NEXT-001.md) | Local Alpha 0.3 task briefs and acceptance matrix |
| AFS-WEB-REVIEW-001 | [AFS-WEB-REVIEW-001.md](AFS-WEB-REVIEW-001.md) | Operator plan/run/review/feedback Web path |
| AFS-MEMORY-RUNTIME-001 | [AFS-MEMORY-RUNTIME-001.md](AFS-MEMORY-RUNTIME-001.md) | Candidate promotion and context reuse contract |
| AFS-POSTER-LIVE-002 | [AFS-POSTER-LIVE-002.md](AFS-POSTER-LIVE-002.md) | Explicit PosterFlow live-smoke run or blocked evidence |

Do not treat a brief as approval to call a remote provider. Provider gates in
the brief and `AGENTS.md` still apply.
