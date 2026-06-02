# AFS-MAINTENANCE-RESET-001 - Repository Maintenance Reset

## Task

Classify and reduce the current dirty worktree before opening more demo or Web
implementation work.

## Goal

Turn the mixed Local Alpha 0.4, provider, Web, and memory-advantage changes
into reviewable groups with clear promotion, archive, or removal paths.

## Non-goals

- Do not delete or rewrite user work without explicit approval.
- Do not remove ignored generated evidence under `data/processed/*`.
- Do not change provider behavior or call providers.
- Do not redesign the Web UI in this lane.
- Do not implement durable Memory runtime.

## Owner Role

Release Integrator + Orchestrator

## Branch / Worktree

```text
Branch: codex/afs-maintenance-reset
Worktree: C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-maintenance-reset
Base branch: master
```

## Write Scope

- `TASK_TRACKER.md`
- `DEVLOG.md` only as short index entries
- `docs/archive/`
- `docs/handoff/`
- `docs/task_briefs/`
- cleanup notes under `docs/maintenance/`
- tests only if needed to preserve current behavior during archival

## Do Not Touch

- provider config files, `.env`, `.dev.vars`, `configs/models.yaml`
- local media, generated runs, model caches
- private Company knowledge base
- Web implementation files unless only updating references after archive
- Memory/provider implementation files unless explicitly promoted by a
  separate task brief

## Input Docs

- `AGENTS.md`
- `docs/company_operating_model.md`
- `TASK_TRACKER.md`
- `docs/retrospectives/agentflow_studio_development_retro_2026_05_29.md`
- `docs/retrospectives/memory_architecture_next_loop_2026_05_29.md`
- `docs/maintenance/AFS-MAINTENANCE-RESET-001.md`

## Acceptance Criteria

- [ ] Current dirty files are classified into coherent groups: Local Alpha 0.4,
      provider adapters, memory demo, Web, docs/retro, and ignored evidence.
- [ ] Every numbered memory-advantage demo module is marked `promote`,
      `archive`, `keep temporarily`, or `remove later` with a condition.
- [ ] `TASK_TRACKER.md` is repaired or split so it can be edited safely and
      acts as a live tracker instead of a history dump.
- [ ] `DEVLOG.md` has a reduction plan and no new long narrative entries.
- [ ] No secrets, provider keys, local media, generated artifacts, or private
      Company content enter Git.
- [ ] The next implementation lanes are blocked until this reset records an
      integration plan.

## Verification Commands

```powershell
git status --short
git diff --check
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests/test_agentflow_roadmap_docs.py -q
git status --short --ignored data/processed data/raw data/models
```

## Expected Artifacts

- Maintenance classification note.
- Updated `TASK_TRACKER.md` and task brief index.
- Archive split or explicit archive plan.

## Remote Provider Policy

- [x] No remote provider needed.
- [ ] Remote LLM needed. Requires `AFS_ALLOW_REMOTE_LLM=true`.
- [ ] Remote ASR needed. Requires `AFS_ALLOW_REMOTE_ASR=true`.
- [ ] Remote image needed. Requires `AFS_ALLOW_REMOTE_IMAGE=true`.
- [ ] Remote video generation needed. Requires an explicit task-specific gate.
- [ ] External download needed. Requires explicit source and artifact policy.

## Evidence Path

```text
docs/maintenance/AFS-MAINTENANCE-RESET-001.md
```

## Return Format

1. Status: `DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or `BLOCKED`.
2. Changed files.
3. Verification commands and results.
4. Classification table and archive/promote/remove decisions.
5. Risks and unfinished work.
6. Whether the worktree should be closed, preserved, or continued.
