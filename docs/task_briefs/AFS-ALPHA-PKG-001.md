# AFS-ALPHA-PKG-001 Task Brief

## Task

Create the Local Alpha 0.2 acceptance package.

## Goal

Turn existing engineering evidence into a coherent local Alpha acceptance flow
that a future agent or human can rerun and review without reopening old branch
history.

## Non-goals

- Do not add runtime code unless a tiny docs-linked command fix is required.
- Do not call remote providers.
- Do not claim human acceptance or business validation.
- Do not copy private Company strategy into the repository.

## Owner Role

Orchestrator + Release Integrator.

## Branch / Worktree

```text
Branch: codex/afs-alpha-package
Worktree: C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-alpha-package
Base branch: master
```

## Write Scope

- `docs/`
- `TASK_TRACKER.md`
- `DEVLOG.md`

## Do Not Touch

- Runtime Python modules unless the docs reveal a broken command reference.
- `apps/web/`
- Provider configuration files.
- `data/processed/`, `data/raw/`, or generated media artifacts.
- `D:\Learning materials\Learning_notes\10-Startup` unless separately requested.

## Input Docs

- `AGENTS.md`
- `docs/company_operating_model.md`
- `TASK_TRACKER.md`
- `docs/alpha_readiness_report.md`
- `docs/README.md`
- `apps/web/README.md`

## Acceptance Criteria

- [ ] A Local Alpha 0.2 acceptance package doc exists under `docs/`.
- [ ] The package defines current demoable capabilities, blockers, non-claims,
      rerun commands, and acceptance checklist.
- [ ] The package links the Web workbench, AgentFlow Production, AgentFlow Studio, and
      PosterFlow evidence paths.
- [ ] `TASK_TRACKER.md` records the lane status and evidence.
- [ ] No confidential Company content or provider secrets are copied.

## Verification Commands

```powershell
python -m apps.cli.main alpha-smoke --json
python -m pytest tests/test_agentflow_roadmap_docs.py
git diff --check
```

## Expected Artifacts

- Local Alpha 0.2 acceptance doc.
- Updated tracker and DEVLOG entry.

## Remote Provider Policy

- [x] No remote provider needed.
- [ ] Remote LLM needed. Requires `AFS_ALLOW_REMOTE_LLM=true`.
- [ ] Remote ASR needed. Requires `AFS_ALLOW_REMOTE_ASR=true`.
- [ ] Remote image needed. Requires `AFS_ALLOW_REMOTE_IMAGE=true`.
- [ ] Remote video generation needed. Requires an explicit task-specific gate.
- [ ] External download needed. Requires explicit source and artifact policy.

## Evidence Path

```text
docs/local_alpha_0_2_acceptance.md
```

## Return Format

1. Status: `DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or `BLOCKED`.
2. Changed files.
3. Verification commands and results.
4. Evidence or artifact paths.
5. Risks and unfinished work.
6. Memory candidates for `10-Startup` or project docs.
7. Whether the subagent or worktree should be closed, preserved, or continued.
