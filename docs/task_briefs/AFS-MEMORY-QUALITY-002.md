# AFS-MEMORY-QUALITY-002 - Evidence Reuse Quality Loop

## Task

Evaluate the Local Alpha 0.4 evidence-to-memory-to-context reuse path.

## Goal

Show whether accepted operator feedback and review/package evidence are
traceably reused in a second pass. Measure traceability first; record human
preference only as a labeled validation signal.

## Non-goals

- Do not add a database, vector store, RAG service, prefix-cache service, or
  hosted memory service.
- Do not write durable long-term memory.
- Do not add autonomous agent routing or skill runtime behavior.
- Do not call remote providers.
- Do not claim quality improvement without comparison evidence.
- Do not change Web UI behavior except read-only documentation references.

## Owner Role

Memory / Evidence Steward

## Branch / Worktree

```text
Branch: codex/afs-memory-quality-loop
Worktree: C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-memory-quality-loop
Base branch: master
```

## Write Scope

Files or directories this task may edit:

- `agentflow/memory/`
- `agentflow/harness/` only for evidence-summary or validator integration
- `narratostudio/posterflow/`
- `narratocut/harness/posterflow_quality*.py`
- `examples/agentflow/`
- `tests/test_agentflow_asset_memory_validator.py`
- `tests/test_contract_examples.py`
- `tests/test_posterflow_workflow.py`
- `tests/test_posterflow_quality.py`
- `docs/agentflow_memory_contract.md`
- Memory/Context docs under `docs/`
- `docs/handoff/AFS-MEMORY-QUALITY-002.md`
- `TASK_TRACKER.md`
- `DEVLOG.md`

## Do Not Touch

Files, directories, branches, artifacts, or local state this task must not
modify:

- Web UI implementation
- provider implementation unless a safety regression is found
- `.env`, `.dev.vars`, or `configs/models.yaml`
- generated images or runtime run directories for commit
- private Company knowledge base unless separately requested

## Input Docs

- `AGENTS.md`
- `docs/company_operating_model.md`
- `TASK_TRACKER.md`
- `docs/agent_operating_roster.md`
- `docs/local_alpha_0_4_product_loop_goals.md`
- `docs/local_alpha_0_4_scenario_package.md` if already created
- `docs/agentflow_memory_contract.md`
- `docs/handoff/AFS-MEMORY-RUNTIME-001.md`
- `docs/handoff/AFS-RUN-PACKAGE-001.md` if already created

## Acceptance Criteria

- [ ] Feedback source, review/package evidence, memory candidate, promotion
      decision, context bundle, and second-pass prompt have explicit roles.
- [ ] The second-pass context trace references accepted evidence or records an
      actionable blocker when the evidence is absent.
- [ ] Checks fail when source feedback, promotion decision, or context refs are
      broken.
- [ ] Human acceptance and comparison notes are labeled separately from
      structure/runtime verification.
- [ ] All applicable artifacts keep `writes_long_term_memory: false` or an
      equivalent no-durable-write boundary.
- [ ] No remote provider call is required for tests.

## Verification Commands

```powershell
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests/test_agentflow_asset_memory_validator.py tests/test_contract_examples.py tests/test_posterflow_workflow.py tests/test_posterflow_quality.py tests/test_posterflow_provider.py
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main alpha-smoke --json
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m compileall agentflow\memory agentflow\harness narratostudio\posterflow narratocut\harness
git diff --check
```

## Expected Artifacts

- Contract, validator, example, or report diff.
- Focused tests for broken evidence-chain references.
- `docs/handoff/AFS-MEMORY-QUALITY-002.md`.
- Tracker and DEVLOG updates.

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
docs/handoff/AFS-MEMORY-QUALITY-002.md
```

## Return Format

1. Status: `DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or `BLOCKED`.
2. Changed files.
3. Verification commands and results.
4. Evidence or artifact paths.
5. Risks and unfinished work.
6. Memory candidates for `Company/` or project docs.
7. Whether the subagent or worktree should be closed, preserved, or continued.

