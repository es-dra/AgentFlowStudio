# AFS-WORKBENCH-REDESIGN-001 - Memory Production Workbench Design

## Task

Design the next AgentFlow Studio workbench around the memory-backed production
loop before editing the current Web implementation.

## Goal

Define a usable local workbench that can guide one operator through brief,
assets, memory loaded, generation runs, side-by-side review, feedback capture,
promotion decision, and next pass.

## Non-goals

- Do not implement Web UI in this design brief.
- Do not add SaaS, auth, accounts, uploads, cookies, localStorage, IndexedDB,
  or cloud sync.
- Do not add durable Memory runtime.
- Do not call providers.
- Do not scan local directories automatically.

## Owner Role

Web UI Agent + Orchestrator + QA Reviewer

## Branch / Worktree

```text
Branch: codex/afs-workbench-redesign
Worktree: C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-workbench-redesign
Base branch: master after AFS-MAINTENANCE-RESET-001
```

## Write Scope

- `docs/workbench/`
- `apps/web/README.md` only if adding a pointer to the design
- `docs/task_briefs/`
- `TASK_TRACKER.md`

## Do Not Touch

- `apps/web/*.js`, `apps/web/*.css`, `apps/web/index.html`
- `apps/web_bridge/`
- provider code or configs
- generated artifacts and local media
- private Company knowledge base

## Input Docs

- `AGENTS.md`
- `docs/company_operating_model.md`
- `apps/web/README.md`
- `docs/retrospectives/agentflow_studio_development_retro_2026_05_29.md`
- `docs/retrospectives/memory_architecture_next_loop_2026_05_29.md`

## Acceptance Criteria

- [x] The design names the primary operator workflow and excludes generic
      dashboard sprawl.
- [x] The first screen is defined around project, assets, memory loaded,
      baseline run, memory-backed run, review, and feedback.
- [x] The UI states distinguish no plan, planned, generating, review ready,
      feedback captured, memory candidate drafted, and blocked.
- [x] The design states exactly what is local-only and non-persistent.
- [x] It specifies how the workbench presents memory provenance: what loaded,
      why eligible, what prompt projection it produced, and what feedback will
      change next time.
- [x] It defines a verification plan for desktop and narrow viewport browser
      smoke before implementation.

## Verification Commands

```powershell
git diff --check
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests/test_agentflow_roadmap_docs.py -q
```

## Expected Artifacts

- Workbench design document under `docs/workbench/`.
- Updated task tracker or task brief index.
- Follow-up implementation brief if design is approved.

## Remote Provider Policy

- [x] No remote provider needed.
- [ ] Remote LLM needed. Requires `NARRATOCUT_ALLOW_REMOTE_LLM=true`.
- [ ] Remote ASR needed. Requires `NARRATOCUT_ALLOW_REMOTE_ASR=true`.
- [ ] Remote image needed. Requires `NARRATOCUT_ALLOW_REMOTE_IMAGE=true`.
- [ ] Remote video generation needed. Requires an explicit task-specific gate.
- [ ] External download needed. Requires explicit source and artifact policy.

## Evidence Path

```text
docs/workbench/AFS-WORKBENCH-REDESIGN-001.md
```

## Return Format

1. Status: `DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or `BLOCKED`.
2. Changed files.
3. Verification commands and results.
4. Design decisions and unresolved product questions.
5. Risks and unfinished work.
6. Whether the worktree should be closed, preserved, or continued.
