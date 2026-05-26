# AFS-POSTER-LIVE-001 Task Brief

## Task

Prepare or run the gated PosterFlow live image smoke.

## Goal

Close the current Alpha blocker when local image-provider environment variables
are available, or produce a precise live-smoke checklist when they are not.

## Non-goals

- Do not ask for provider secrets in chat.
- Do not commit provider keys, signed URLs, generated media, or runtime run
  directories.
- Do not change default provider behavior.
- Do not add remote video generation.
- Do not claim creative quality validation from a smoke run.

## Owner Role

Provider Adapter Agent + Security / Secret Audit Agent.

## Branch / Worktree

```text
Branch: codex/afs-poster-live-smoke
Worktree: C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-poster-live-smoke
Base branch: master
```

## Write Scope

- `docs/`
- `tests/test_posterflow_provider.py` if a provider safety regression appears.
- `TASK_TRACKER.md`
- `DEVLOG.md`

## Do Not Touch

- Provider secret files.
- `.env`, `.dev.vars`, `configs/models.yaml`.
- `data/processed/` generated runtime artifacts for commit.
- Web UI implementation.
- Durable memory/runtime code.

## Input Docs

- `AGENTS.md`
- `docs/company_operating_model.md`
- `TASK_TRACKER.md`
- `docs/alpha_readiness_report.md`
- `docs/handoff/AFS-PROD-001.md`

## Acceptance Criteria

- [ ] Environment readiness is checked without printing secrets.
- [ ] If live env is missing, a checklist explains exact local-only variables
      and commands to run later.
- [ ] If live env is present, run PosterFlow live smoke only with
      `NARRATOCUT_ALLOW_REMOTE_IMAGE=true`.
- [ ] Inspect/review results and artifact paths are recorded without committing
      generated images or run directories.
- [ ] A no-secret scan confirms no key, token, cookie, signed URL, or generated
      media was staged.

## Verification Commands

```powershell
python -m apps.cli.main alpha-smoke --json
python -m pytest tests/test_posterflow_provider.py tests/test_posterflow_workflow.py tests/test_posterflow_quality.py
git diff --check
```

Optional live smoke, only if local environment is already configured:

```powershell
python -m apps.cli.main run-workflow --workflow workflows/posterflow_memory_demo.yaml --input examples/posterflow/poster_brief.example.json --output data/processed/poster_runs/cyber_xianxia_001/live_001
python -m apps.cli.main inspect-run --run-dir data/processed/poster_runs/cyber_xianxia_001/live_001
python -m apps.cli.main review-run --run-dir data/processed/poster_runs/cyber_xianxia_001/live_001
```

## Expected Artifacts

- Live-smoke checklist or local run evidence note.
- Updated Alpha blocker status if evidence changes.
- Secret/artifact hygiene note.

## Remote Provider Policy

- [ ] No remote provider needed.
- [ ] Remote LLM needed. Requires `NARRATOCUT_ALLOW_REMOTE_LLM=true`.
- [ ] Remote ASR needed. Requires `NARRATOCUT_ALLOW_REMOTE_ASR=true`.
- [x] Remote image may be needed. Requires `NARRATOCUT_ALLOW_REMOTE_IMAGE=true`.
- [ ] Remote video generation needed. Requires an explicit task-specific gate.
- [ ] External download needed. Requires explicit source and artifact policy.

## Evidence Path

```text
docs/handoff/AFS-POSTER-LIVE-001.md
```

## Return Format

1. Status: `DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or `BLOCKED`.
2. Changed files.
3. Verification commands and results.
4. Evidence or artifact paths.
5. Risks and unfinished work.
6. Memory candidates for `Company/` or project docs.
7. Whether the subagent or worktree should be closed, preserved, or continued.
