# AFS-PROD-LOOP-001 - Local Alpha 0.4 Scenario Package

## Task

Define the executable Local Alpha 0.4 product-loop scenario before opening
implementation worktrees.

## Goal

Turn `docs/local_alpha_0_4_product_loop_goals.md` into one concrete scenario
package: local input policy, runbook, acceptance checklist, evidence map,
blocked-state rules, tracker state, and integration order.

## Non-goals

- Do not implement Web UI, Memory runtime, provider, workflow, or CLI changes.
- Do not call remote providers.
- Do not create implementation worktrees from this brief unless the task is
  explicitly expanded.
- Do not copy private Company strategy, retrospectives, provider config, local
  media, customer details, or secrets into the repository.

## Owner Role

Orchestrator + Product Lead

## Branch / Worktree

```text
Branch: codex/afs-prod-loop-brief
Worktree: C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-prod-loop-brief
Base branch: master
```

## Write Scope

Files or directories this task may edit:

- `TASK_TRACKER.md`
- `docs/local_alpha_0_4_product_loop_goals.md`
- `docs/local_alpha_0_4_scenario_package.md`
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
- `narratocut/`
- `narratostudio/`
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
- `docs/local_alpha_0_3_validation_goals.md`
- `docs/local_alpha_0_4_product_loop_goals.md`
- `docs/local_alpha_0_2_acceptance.md`
- `docs/golden_sample_v0_1_0.md`

## Acceptance Criteria

- [ ] `docs/local_alpha_0_4_scenario_package.md` exists and names one concrete
      local product scenario.
- [ ] The scenario package lists required local ignored inputs, expected
      outputs, run commands, acceptance checklist, blocked-state handling, and
      non-claims.
- [ ] `TASK_TRACKER.md` records the Local Alpha 0.4 queue, dependencies, and
      integration order.
- [ ] `docs/company_operating_model.md` and `docs/agent_operating_roster.md`
      name Local Alpha 0.4 as the current product push.
- [ ] `docs/task_briefs/README.md` lists the 0.4 briefs and keeps completed
      0.3 briefs historical.
- [ ] No runtime code, generated artifact, provider config, local media, or
      Company-private content is changed.

## Verification Commands

```powershell
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests/test_agentflow_roadmap_docs.py
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main alpha-smoke --json
git diff --check
```

## Expected Artifacts

- `docs/local_alpha_0_4_scenario_package.md`
- Updated 0.4 queue state in `TASK_TRACKER.md`
- Updated operating-model, roster, docs index, task brief index, and DEVLOG

## Remote Provider Policy

Mark every capability explicitly.

- [x] No remote provider needed.
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
docs/local_alpha_0_4_scenario_package.md
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
