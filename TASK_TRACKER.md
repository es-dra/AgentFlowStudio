# AgentFlow Studio Task Tracker

Last updated: 2026-06-03 by Codex

This tracker is the live AgentFlow Studio work ledger. Keep it limited to
active, next, and blocked work plus short evidence pointers. Historical rows
belong in `docs/archive/` or focused handoff files.

Company source knowledge base:

```text
D:\Learning materials\Learning_notes\Company
```

Project-facing operating model:

```text
docs/company_operating_model.md
```

## Current Operating Rule

- AgentFlow Studio is the current main project.
- Loulan is a production pressure sample only, not the current product branch.
- Do not open another numbered memory-advantage demo module.
- Keep provider smoke, deterministic tests, human acceptance, business
  validation, and durable memory claims separate.
- Do not commit secrets, provider keys, signed URLs, cookies, local media,
  model caches, generated runtime artifacts, or Company-private material.
- Keep remote provider calls gated by capability and explicit task approval.
- Use isolated `codex/*` worktrees for normal or substantial development.
- Start subagents only for bounded roles with independent scope, verifiable
  artifacts, integration order, and close conditions.

## Active Work

| ID | Owner role | Scope | Status | Verification / evidence |
|---|---|---|---|---|
| AFS-FULL-RENAME-MAINTAINABILITY-001 | Release Integrator + Memory / Evidence Steward | Rename package metadata, Python package, CLI script, public command surface, environment gates, and production-side naming to AgentFlow Studio / AFS | verified locally, PR pending | Evidence: `docs/maintenance/AFS-FULL-RENAME-MAINTAINABILITY-001.md`; `python -m pytest` passed with 980 tests; no provider call, Company KB write, durable-memory claim, human acceptance, or business validation |
| AFS-MAINTENANCE-SLIMMING-001 | Release Integrator + Memory / Evidence Steward | Slim documentation/status entrypoints, layer the CLI command surface, centralize Web artifact metadata, add a Production Memory asset facade, and record/clean safe ignored runtime residue | superseded by full rename pass | Evidence: `docs/maintenance/AFS-MAINTENANCE-SLIMMING-001.md`; no provider call, Company KB write, durable-memory claim, human acceptance, or business validation |

## Current Mainline Baseline

| Area | Status | Evidence |
|---|---|---|
| Git mainline | Local and remote `master` are the project mainline after merged Production Memory asset loop work | `docs/maintenance/AFS-MAINLINE-FOUNDATION-CLEANUP-001.md` |
| Production Memory Asset Loop | Deterministic local contract chain is merged through read-only Web cockpit | `docs/handoff/AFS-PRODUCTION-MEMORY-ASSET-COCKPIT-WEB-001.md` |
| Loulan pressure sample | Archived as evidence only; not a live product branch | `docs/strategy/AFS-POSITIONING-KB-FEEDBACK-2026-06-02.md` |
| Historical work ledger | Archived to keep active tracker readable | `docs/archive/task_history_2026_06_03_pre_slimming.md` |

## Next Queue

| ID | Scope | Dependency | Status |
|---|---|---|---|
| AFS-REAL-ASSET-TEST-RUN-HARNESS-001 | Run the merged deterministic asset loop with user-supplied final project materials under ignored runtime paths, then collect tester feedback | Wait for maintenance slimming and tester material handoff | queued |
| AFS-WEB-ASSET-REVIEW-SCREEN-001 | Build a tester-facing asset profile review screen from the deterministic asset loop, without provider execution or browser persistence | Wait for current maintenance pass and early tester feedback | queued |
| AFS-PRODUCTION-MEMORY-PROVIDER-VALIDATION-001 | Optional gated image/video validation with safe result manifests only | Requires explicit provider gates/config/materials after deterministic tests | blocked by explicit authorization |

## Archive

- Pre-slimming tracker history:
  `docs/archive/task_history_2026_06_03_pre_slimming.md`.
- Older pre-reset task history:
  `docs/archive/task_history_2026_05.md`.
- Long dated narrative belongs in `DEVLOG.md` only as short pointers to
  detailed docs, not as another full historical tracker.
