# AGENTS.md

## Mission

AgentFlow Studio is an agent-native content production and distribution
workflow platform.

Current repository roles:

```text
agentflow/        platform contracts, harness, router, memory, and skills
narratostudio/    production-side structured content handoff
narratocut/       distribution-side short video packaging and review
```

Current NarratoCut MVP chain:

```text
subtitle/text -> hooks -> scripts -> clip_plans -> videos -> metadata
```

## Operating Rules

- Treat `D:\Learning materials\Learning_notes\Company` as the local company
  source-of-truth knowledge base. This repository should contain only the
  execution-facing projection needed for AgentFlow Studio development.
- Use the company AI-native workflow hierarchy when planning substantial work:
  Company source rules -> global workflow skills -> project `AGENTS.md` ->
  task tracker / branch handoff.
- At the start of every new development conversation in this repository,
  classify the task as `Light`, `Standard`, `Deep`, or `Strategic` before
  deciding whether to edit in-place, open a worktree, or dispatch subagents.
- For normal or substantial work, read `docs/company_operating_model.md` and
  `TASK_TRACKER.md` after this file. For parallel or delegated work, also read
  `docs/agent_operating_roster.md` and `docs/agent_task_brief_template.md`.
- Do not copy confidential company strategy, private retrospectives, real costs,
  provider secrets, customer details, or unpublished business assumptions from
  `Company/` into this repository.
- For multi-line development, keep the main checkout stable and use isolated
  `codex/*` worktrees with explicit write scopes, verification commands, and
  integration order.
- For substantial work, use `docs/agent_operating_roster.md` to choose the
  owner role and `docs/agent_task_brief_template.md` before spawning subagents
  or opening parallel worktrees.
- Keep project worktrees under
  `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\`.
  If a preserved branch still points to an old repository path, repair or move
  the worktree before continuing.
- Do not merge a preserved branch just because it is pushed. If it trails
  `master`, record the divergence and rebase or replay it on a fresh branch
  before integration.
- Agent/subagent work must use bounded tasks: goal, non-goals, write scope,
  acceptance criteria, verification, remote-provider policy, and return format.
- Treat subagents as ephemeral task workers, not permanent unattended staff.
  Close them after their artifact, review, or QA result has been collected.
  If the agent manager reports an old ID as `not found`, treat it as inactive
  history rather than an open execution lane.
- Start subagents dynamically only when they have an independent scope,
  verifiable artifact, and close condition. Do not keep idle, blocked, stale, or
  unverifiable subagents open as planning context.
- Remote-provider policy must name the capability being authorized: LLM, ASR,
  image, video, or external download. One provider gate does not imply another.
- Do not migrate code from `D:\Projects\AVP` unless the user explicitly asks.
- Do not commit secrets, provider keys, signed URLs, cookies, tokens, or private credentials.
- Do not commit large media files or generated runtime artifacts.
- Do not call remote LLMs unless `NARRATOCUT_ALLOW_REMOTE_LLM=true`.
- Do not call remote ASR unless `NARRATOCUT_ALLOW_REMOTE_ASR=true`.
- Do not call remote image providers unless `NARRATOCUT_ALLOW_REMOTE_IMAGE=true`.
- Prefer schema-first design for workflow inputs, outputs, and intermediate artifacts.
- New features should include focused tests or a clear reason when tests are deferred.
- Keep files focused. Ideal file length is 300 lines or less.
- Keep `workflow_engine` responsible for execution order.
- Keep `harness` responsible for task contracts, evidence, and gates.
- Distinguish structure verification, runtime verification, human acceptance,
  and business validation in reports and handoffs.
- Candidate memory, demo artifacts, and successful tests are evidence, not
  durable company memory or product validation until explicitly reviewed.

## Local Configuration

- Use Python 3.12 for local development. Do not switch the project to Python 3.13 until media, ASR, and model dependencies are verified.
- Commit only example configuration files.
- Use `configs/models.yaml` for local model settings; it is ignored by git.
- Keep `configs/models.example.yaml` as the committed template.
- Use `.env` or `.dev.vars` only locally; both are ignored.

## Verification

Before claiming a change is complete, run the relevant verification command. For Phase 0 bootstrap, use:

```powershell
python -m apps.cli.main --help
python -m apps.cli.main version
pytest
```

For current AI-native company workflow projection, also keep
`TASK_TRACKER.md` current for multi-session work and read
`docs/company_operating_model.md` before opening parallel workstreams.
