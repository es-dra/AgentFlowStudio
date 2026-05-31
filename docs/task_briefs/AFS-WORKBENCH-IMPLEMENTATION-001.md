# AFS-WORKBENCH-IMPLEMENTATION-001 - Static Memory Workbench First Screen

## Task

Implement the first Web slice of the memory production workbench from
`docs/workbench/AFS-WORKBENCH-REDESIGN-001.md`.

This is the first implementation slice only. It should render a static
first-screen view from a committed fixture shaped like
`agentflow_memory_video_pipeline_package`.

## Goal

Make the memory-backed production loop visible in the local Web workbench:

```text
Project
-> Assets
-> Memory Loaded
-> Baseline Run
-> Memory-backed Run
-> Review
-> Feedback
-> Next Pass
```

The operator should be able to see the package state, lane parity, bounded
review status, feedback draft state, and memory provenance without opening raw
JSON first.

## Non-goals

- Do not call providers.
- Boundary keyword: no provider calls.
- Do not enable live image or video execution.
- Do not edit `apps/web_bridge/`.
- Boundary keyword: no apps/web_bridge changes.
- Do not add SaaS, auth, accounts, uploads, cookies, localStorage, IndexedDB,
  or cloud sync.
- Do not add automatic directory scanning.
- Boundary keyword: no automatic directory scanning.
- Do not add durable Memory runtime.
- Do not persist generated media, provider URLs, signed URLs, or secrets.
- Do not claim human acceptance, business validation, or final quality proof.

## Owner Role

Web UI Agent + QA Reviewer

## Write Scope

- `apps/web/` for the static first-screen view and local fixture wiring.
- `tests/test_web_production_mode_static.py` or a focused Web static test.
- `apps/web/README.md` only if adding a short pointer to the workbench slice.
- `TASK_TRACKER.md` and `DEVLOG.md` after verification.

## Do Not Touch

- `apps/web_bridge/`
- provider adapters and config files;
- `.env`, `.dev.vars`, `configs/models.yaml`;
- `data/processed/`, `data/raw/`, generated media, or local model caches;
- private Company knowledge base.

## Input Docs

- `AGENTS.md`
- `docs/workbench/AFS-WORKBENCH-REDESIGN-001.md`
- `docs/handoff/AFS-POST-DEMO-PRODUCTIZATION-ROADMAP.md`
- `docs/handoff/AFS-MEMORY-PIPELINE-MVP-001.md`
- `examples/agentflow/memory_video_pipeline_package.example.json`

## Required UI Content

The first screen must include:

- Project summary from the package/protocol fixture.
- Assets summary.
- Memory Loaded summary.
- Baseline Run state.
- Memory-backed Run state.
- Review state.
- Feedback state.
- Next Pass state.
- State labels for no plan, planned, generating, review ready, feedback
  captured, memory candidate drafted, promotion decision ready, and blocked.
- A memory provenance panel.

The memory provenance panel must show:

- what memory was loaded;
- why it was eligible;
- source evidence refs;
- prompt/request projection summary;
- what feedback will change next time.

## Fixture Policy

Use a small committed Web fixture derived from
`agentflow_memory_video_pipeline_package`.

The fixture must not contain:

- private local absolute paths;
- generated media paths;
- provider URLs;
- signed URLs;
- credentials;
- bearer headers;
- data URLs.

## Acceptance Criteria

- [ ] A static first-screen view renders from the fixture without bridge access.
- [ ] The view exposes all eight loop regions: Project, Assets, Memory Loaded,
      Baseline Run, Memory-backed Run, Review, Feedback, Next Pass.
- [ ] The view includes all state labels: no plan, planned, generating, review
      ready, feedback captured, memory candidate drafted, promotion decision
      ready, blocked.
- [ ] The memory provenance panel is visible and test-covered.
- [ ] Provider execution actions are absent or disabled in this slice.
- [ ] The implementation uses no browser persistence.
- [ ] The implementation performs no automatic directory scanning.
- [ ] Tests assert the fixture and UI do not include secrets, provider URLs, or
      generated media refs.
- [ ] Browser screenshot verification covers desktop and narrow viewport with
      no overlapping text.

## Verification Commands

```powershell
node --check apps/web/app.js
node --check apps/web/production-render.js
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests/test_web_production_mode_static.py tests/test_agentflow_roadmap_docs.py -q
git diff --check
```

After implementation, run Browser screenshot verification against the local Web
target. The final report should include the tested URL, viewport sizes, and
whether text overlap was observed.

## Remote Provider Policy

- [x] No remote provider needed.
- [ ] Remote LLM needed. Requires explicit LLM gate.
- [ ] Remote image needed. Requires explicit image gate.
- [ ] Remote video needed. Requires explicit video gate.

## Expected Evidence

- Web fixture for `agentflow_memory_video_pipeline_package`.
- Static first-screen render path.
- Focused Web static tests.
- Browser screenshot evidence.
- Updated tracker/devlog.

## Return Format

1. Status: `DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or `BLOCKED`.
2. Changed files.
3. Verification commands and results.
4. Browser screenshot targets and outcomes.
5. Remaining risks and next implementation slice.
