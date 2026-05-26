# Agent Task Brief Template

Use this template before opening a parallel worktree or assigning a subagent.
It is the AgentFlow Studio execution-facing projection of the Company task
brief. Keep private Company strategy and secrets out of this file.

## Task

## Goal

## Non-goals

## Owner Role

Choose one primary role from `docs/agent_operating_roster.md`.

## Branch / Worktree

```text
Branch:
Worktree:
Base branch:
```

## Write Scope

Files or directories this task may edit:

- TODO

## Do Not Touch

Files, directories, branches, artifacts, or local state this task must not
modify:

- TODO

## Input Docs

- `AGENTS.md`
- `docs/company_operating_model.md`
- `TASK_TRACKER.md`

Add task-specific docs below:

- TODO

## Acceptance Criteria

- [ ] TODO

## Verification Commands

```powershell

```

## Expected Artifacts

- TODO

## Remote Provider Policy

Mark every capability explicitly.

- [ ] No remote provider needed.
- [ ] Remote LLM needed. Requires `NARRATOCUT_ALLOW_REMOTE_LLM=true`.
- [ ] Remote ASR needed. Requires `NARRATOCUT_ALLOW_REMOTE_ASR=true`.
- [ ] Remote image needed. Requires `NARRATOCUT_ALLOW_REMOTE_IMAGE=true`.
- [ ] Remote video generation needed. Requires an explicit task-specific gate.
- [ ] External download needed. Requires explicit source and artifact policy.

Secrets, keys, signed URLs, cookies, and private credentials must stay local and
must not be committed.

## Evidence Path

Where the worker should write or reference evidence:

```text

```

## Return Format

1. Status: `DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or `BLOCKED`.
2. Changed files.
3. Verification commands and results.
4. Evidence or artifact paths.
5. Risks and unfinished work.
6. Memory candidates for `Company/` or project docs.
7. Whether the subagent or worktree should be closed, preserved, or continued.
