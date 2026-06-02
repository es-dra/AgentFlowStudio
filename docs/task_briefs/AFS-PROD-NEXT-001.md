# AFS-PROD-NEXT-001 - Local Alpha 0.3 Task Briefs

## Task

Define the executable Local Alpha 0.3 product queue before opening new
parallel worktrees.

## Goal

Turn `docs/local_alpha_0_3_validation_goals.md` into fresh task briefs,
acceptance matrix, tracker state, and integration order for the next parallel
development queue.

## Non-goals

- Do not implement Web UI, Memory runtime, provider, workflow, or CLI changes.
- Do not call remote providers.
- Do not create implementation worktrees from this brief unless the task is
  explicitly expanded.
- Do not copy private Company strategy, retrospectives, provider config, or
  secrets into the repository.

## Owner Role

Orchestrator + Product Lead

## Branch / Worktree

```text
Branch: codex/afs-product-next-briefs
Worktree: C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-product-next-briefs
Base branch: master
```

## Write Scope

Files or directories this task may edit:

- `TASK_TRACKER.md`
- `docs/local_alpha_0_3_validation_goals.md`
- `docs/company_operating_model.md`
- `docs/agent_operating_roster.md`
- `docs/task_briefs/`
- `docs/README.md`
- `DEVLOG.md`

## Do Not Touch

Files, directories, branches, artifacts, or local state this task must not
modify:

- `apps/`
- `agentflow/`
- `agentflow_studio/`
- `agentflow_production/`
- `workflows/`
- `examples/`
- `data/processed/`
- provider env files or local secrets
- generated media or runtime artifacts

## Input Docs

- `AGENTS.md`
- `docs/company_operating_model.md`
- `TASK_TRACKER.md`
- `docs/agent_operating_roster.md`
- `docs/agent_task_brief_template.md`
- `docs/local_alpha_0_2_acceptance.md`
- `docs/local_alpha_0_3_validation_goals.md`

## Acceptance Criteria

- [ ] `TASK_TRACKER.md` names Local Alpha 0.3 as the current planning slice.
- [ ] Fresh task briefs exist for the next implementation lanes.
- [ ] Each brief has write scope, do-not-touch list, acceptance criteria,
      verification commands, provider policy, evidence path, and return format.
- [ ] `docs/company_operating_model.md` and `docs/agent_operating_roster.md`
      no longer advertise completed Local Alpha 0.2 lanes as ready to open.
- [ ] The docs index links the Local Alpha 0.3 validation goals.
- [ ] No runtime code, generated artifact, provider config, or Company-private
      content is changed.

## Verification Commands

```powershell
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests/test_agentflow_roadmap_docs.py
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main alpha-smoke --json
git diff --check
```

## Expected Artifacts

- Local Alpha 0.3 task briefs under `docs/task_briefs/`
- Updated queue state in `TASK_TRACKER.md`
- Updated operating-model and roster docs
- DEVLOG entry

## Remote Provider Policy

Mark every capability explicitly.

- [x] No remote provider needed.
- [ ] Remote LLM needed. Requires `AFS_ALLOW_REMOTE_LLM=true`.
- [ ] Remote ASR needed. Requires `AFS_ALLOW_REMOTE_ASR=true`.
- [ ] Remote image needed. Requires `AFS_ALLOW_REMOTE_IMAGE=true`.
- [ ] Remote video generation needed. Requires an explicit task-specific gate.
- [ ] External download needed. Requires explicit source and artifact policy.

Secrets, keys, signed URLs, cookies, and private credentials must stay local and
must not be committed.

## Evidence Path

Where the worker should write or reference evidence:

```text
docs/local_alpha_0_3_validation_goals.md
TASK_TRACKER.md
DEVLOG.md
```

## Return Format

1. Status: `DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or `BLOCKED`.
2. Changed files.
3. Verification commands and results.
4. Evidence or artifact paths.
5. Risks and unfinished work.
6. Memory candidates for `Company/` or project docs.
7. Whether the subagent or worktree should be closed, preserved, or continued.
