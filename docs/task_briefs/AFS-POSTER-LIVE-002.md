# AFS-POSTER-LIVE-002 - PosterFlow Live Image Smoke Boundary

## Task

Run or explicitly keep blocked the Local Alpha 0.3 PosterFlow live image smoke.

## Goal

Make the live image-provider boundary clear: either produce local ignored
live-smoke evidence under the image gate, or record that the lane remains
blocked because local provider env is absent.

## Non-goals

- Do not ask for provider secrets in chat.
- Do not commit provider keys, signed URLs, cookies, generated images,
  generated media, or runtime run directories.
- Do not change default provider behavior.
- Do not add remote video generation.
- Do not claim creative quality validation from a smoke run.
- Do not add durable Memory runtime.

## Owner Role

Provider Adapter Agent + Security / Secret Audit Agent

## Branch / Worktree

```text
Branch: codex/afs-poster-live-002
Worktree: C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-poster-live-002
Base branch: master
```

## Write Scope

Files or directories this task may edit:

- `docs/handoff/AFS-POSTER-LIVE-002.md`
- `docs/alpha_readiness_report.md` if status changes
- `docs/local_alpha_0_3_validation_goals.md` only if acceptance wording needs
  a narrow correction
- `tests/test_posterflow_provider.py` only if a provider safety regression is
  found
- `TASK_TRACKER.md`
- `DEVLOG.md`

## Do Not Touch

Files, directories, branches, artifacts, or local state this task must not
modify:

- provider secret files
- `.env`, `.dev.vars`, or `configs/models.yaml`
- generated runtime artifacts under `data/processed/` for commit
- generated images or media for commit
- Web UI implementation
- durable memory/runtime code
- private Company knowledge base unless separately requested

## Input Docs

- `AGENTS.md`
- `docs/company_operating_model.md`
- `TASK_TRACKER.md`
- `docs/agent_operating_roster.md`
- `docs/local_alpha_0_3_validation_goals.md`
- `docs/alpha_readiness_report.md`
- `docs/handoff/AFS-POSTER-LIVE-001.md`

## Acceptance Criteria

- [ ] Environment readiness is checked without printing secrets.
- [ ] If live env is missing, handoff records blocked status and exact local
      setup variables without secret values.
- [ ] If live env is present, PosterFlow live smoke runs only with
      `AFS_ALLOW_REMOTE_IMAGE=true`.
- [ ] Inspect/review output and artifact paths are recorded without committing
      generated images or run directories.
- [ ] A no-secret and no-generated-artifact staged-file review is recorded.
- [ ] `alpha-smoke --json` accurately reports pass or blocked state.

## Verification Commands

```powershell
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main alpha-smoke --json
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests/test_posterflow_provider.py tests/test_posterflow_workflow.py tests/test_posterflow_quality.py
git diff --check
```

Optional live smoke, only if local environment is already configured:

```powershell
$env:AFS_ALLOW_REMOTE_IMAGE="true"
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main run-workflow --workflow workflows/posterflow_memory_demo.yaml --input examples/posterflow/poster_brief.example.json --output data/processed/poster_runs/cyber_xianxia_001/live_002
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main inspect-run --run-dir data/processed/poster_runs/cyber_xianxia_001/live_002
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main review-run --run-dir data/processed/poster_runs/cyber_xianxia_001/live_002
```

## Expected Artifacts

- `docs/handoff/AFS-POSTER-LIVE-002.md`.
- Alpha readiness status update only if evidence changes.
- Secret/artifact hygiene note.

## Remote Provider Policy

Mark every capability explicitly.

- [ ] No remote provider needed.
- [ ] Remote LLM needed. Requires `AFS_ALLOW_REMOTE_LLM=true`.
- [ ] Remote ASR needed. Requires `AFS_ALLOW_REMOTE_ASR=true`.
- [x] Remote image may be needed. Requires `AFS_ALLOW_REMOTE_IMAGE=true`.
- [ ] Remote video generation needed. Requires an explicit task-specific gate.
- [ ] External download needed. Requires explicit source and artifact policy.

Secrets, keys, signed URLs, cookies, and private credentials must stay local and
must not be committed.

## Evidence Path

Where the worker should write or reference evidence:

```text
docs/handoff/AFS-POSTER-LIVE-002.md
```

## Return Format

1. Status: `DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or `BLOCKED`.
2. Changed files.
3. Verification commands and results.
4. Evidence or artifact paths.
5. Risks and unfinished work.
6. Memory candidates for `Company/` or project docs.
7. Whether the subagent or worktree should be closed, preserved, or continued.
