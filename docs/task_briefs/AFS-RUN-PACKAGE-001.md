# AFS-RUN-PACKAGE-001 - Local Product Runtime Package

## Task

Run or harden the Local Alpha 0.4 scenario through a local reviewable package
path.

## Goal

Produce one local runtime package evidence set for the 0.4 scenario, or record
an actionable blocked state when required local ignored inputs are missing.

## Non-goals

- Do not call remote LLM, ASR, image, or video providers.
- Do not commit generated media, runtime artifacts, model cache, local input
  bundles, provider config, or secrets.
- Do not change Web UI behavior.
- Do not add durable Memory runtime, RAG, database, Router runtime, or skill
  runtime.
- Do not claim mature editorial quality or business validation.

## Owner Role

Workflow Engineer + Harness / QA Reviewer

## Branch / Worktree

```text
Branch: codex/afs-run-package-loop
Worktree: C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-run-package-loop
Base branch: master
```

## Write Scope

Files or directories this task may edit:

- `docs/local_alpha_0_4_scenario_package.md` only for narrow runbook updates
- `docs/handoff/AFS-RUN-PACKAGE-001.md`
- `docs/alpha_readiness_report.md` only if status evidence changes
- `tests/test_video_to_finished_package_local_asr_workflow.py`
- workflow or harness tests directly required by a discovered blocker
- `TASK_TRACKER.md`
- `DEVLOG.md`

## Do Not Touch

Files, directories, branches, artifacts, or local state this task must not
modify:

- `apps/web/`
- `agentflow/memory/` durable-memory claims or runtime surfaces
- provider implementation unless a local safety regression is found
- `.env`, `.dev.vars`, `configs/models.yaml`, or provider secret files
- generated runtime artifacts under `data/processed/` for commit
- local media under `data/raw/` for commit
- private Company knowledge base unless separately requested

## Input Docs

- `AGENTS.md`
- `docs/company_operating_model.md`
- `TASK_TRACKER.md`
- `docs/agent_operating_roster.md`
- `docs/local_alpha_0_4_product_loop_goals.md`
- `docs/local_alpha_0_4_scenario_package.md`
- `docs/golden_sample_v0_1_0.md`
- `docs/product_acceptance_phase14_6_delivery_readiness.md`

## Acceptance Criteria

- [ ] Required local inputs are checked without committing local media or
      private input bundles.
- [ ] If inputs exist, the selected local workflow runs to terminal status and
      writes inspect, review, and package-report evidence.
- [ ] If inputs are missing, the handoff records `BLOCKED` with exact missing
      paths and next local setup commands.
- [ ] Generated runtime artifacts and media remain ignored and unstaged.
- [ ] Review evidence separates runtime verification from human acceptance and
      business validation.
- [ ] Focused tests cover any runbook, workflow, or harness behavior changed by
      this lane.

## Verification Commands

```powershell
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main alpha-smoke --json
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests/test_video_to_finished_package_local_asr_workflow.py tests/test_alpha_smoke_cli.py
git status --short
git diff --check
```

Optional local runtime commands, only when required ignored inputs exist:

```powershell
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main run-workflow --workflow workflows/video_to_finished_package_local_asr.yaml --input <ignored_input_bundle> --output data/processed/runs/local_alpha_0_4_product_loop
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main inspect-run --run-dir data/processed/runs/local_alpha_0_4_product_loop
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main review-run --run-dir data/processed/runs/local_alpha_0_4_product_loop
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main package-report --run-dir data/processed/runs/local_alpha_0_4_product_loop
```

## Expected Artifacts

- `docs/handoff/AFS-RUN-PACKAGE-001.md`
- Runtime evidence paths under ignored `data/processed/` when inputs exist
- Tracker and DEVLOG updates

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
docs/handoff/AFS-RUN-PACKAGE-001.md
data/processed/runs/local_alpha_0_4_product_loop
```

## Return Format

1. Status: `DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or `BLOCKED`.
2. Changed files.
3. Verification commands and results.
4. Evidence or artifact paths.
5. Risks and unfinished work.
6. Memory candidates for `Company/` or project docs.
7. Whether the subagent or worktree should be closed, preserved, or continued.

