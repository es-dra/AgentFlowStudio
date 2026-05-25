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
- Do not copy confidential company strategy, private retrospectives, real costs,
  provider secrets, customer details, or unpublished business assumptions from
  `Company/` into this repository.
- For multi-line development, keep the main checkout stable and use isolated
  `codex/*` worktrees with explicit write scopes, verification commands, and
  integration order.
- Agent/subagent work must use bounded tasks: goal, non-goals, write scope,
  acceptance criteria, verification, remote-provider policy, and return format.
- Do not migrate code from `D:\Projects\AVP` unless the user explicitly asks.
- Do not commit secrets, provider keys, signed URLs, cookies, tokens, or private credentials.
- Do not commit large media files or generated runtime artifacts.
- Do not call remote LLMs unless `NARRATOCUT_ALLOW_REMOTE_LLM=true`.
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
