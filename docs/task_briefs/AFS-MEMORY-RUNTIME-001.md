# AFS-MEMORY-RUNTIME-001 - Memory Promotion And Context Reuse Contract

## Task

Strengthen the Memory OS candidate-promotion and next-round context reuse
contract for Local Alpha 0.3.

## Goal

Make the evidence chain from feedback event to memory candidate, explicit
promotion decision, context bundle, and next-round prompt auditable without
adding durable memory writes.

## Non-goals

- Do not add a database, vector store, RAG service, prefix-cache service, or
  hosted memory service.
- Do not write durable long-term memory.
- Do not add autonomous agent routing or skill runtime behavior.
- Do not call remote providers.
- Do not claim product validation or creative quality validation.

## Owner Role

Memory / Evidence Steward

## Branch / Worktree

```text
Branch: codex/afs-memory-runtime-contract
Worktree: C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-memory-runtime-contract
Base branch: master
```

## Write Scope

Files or directories this task may edit:

- `agentflow/memory/`
- `agentflow/harness/` only for evidence-summary or validator integration
- `agentflow_production/posterflow/`
- `agentflow_studio/harness/posterflow_quality*.py`
- `workflows/posterflow_memory_demo.yaml`
- `examples/agentflow/`
- `tests/test_agentflow_asset_memory_validator.py`
- `tests/test_contract_examples.py`
- `tests/test_posterflow_workflow.py`
- `tests/test_posterflow_quality.py`
- `docs/agentflow_memory_contract.md`
- Memory/Context docs under `docs/`
- `TASK_TRACKER.md`
- `DEVLOG.md`
- `docs/handoff/AFS-MEMORY-RUNTIME-001.md`

## Do Not Touch

Files, directories, branches, artifacts, or local state this task must not
modify:

- Web UI implementation except read-only docs references
- provider implementation unless a safety regression is found
- `.env`, `.dev.vars`, or `configs/models.yaml`
- generated images or runtime run directories for commit
- private Company knowledge base unless separately requested

## Input Docs

- `AGENTS.md`
- `docs/company_operating_model.md`
- `TASK_TRACKER.md`
- `docs/agent_operating_roster.md`
- `docs/local_alpha_0_3_validation_goals.md`
- `docs/agentflow_memory_contract.md`
- `docs/agentflow_artifact_map.md`
- `docs/handoff/AFS-MEMORY-DEMO-001.md`

## Acceptance Criteria

- [ ] Feedback source, derived signal, memory candidate, promotion decision,
      preference profile, context bundle, and next-round prompt have explicit
      roles in docs or contracts.
- [ ] Promotion decisions remain side-effect-free and reject durable-memory
      claim fields.
- [ ] Context bundle or next-round prompt references accepted evidence in an
      inspectable way.
- [ ] Review or quality checks fail when candidate-to-promotion or
      promotion-to-context references are broken.
- [ ] All applicable artifacts keep `writes_long_term_memory: false` or an
      equivalent no-durable-write boundary.
- [ ] No remote provider call is required for tests.

## Verification Commands

```powershell
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests/test_agentflow_asset_memory_validator.py tests/test_contract_examples.py tests/test_posterflow_workflow.py tests/test_posterflow_quality.py tests/test_posterflow_provider.py
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main alpha-smoke --json
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m compileall agentflow\memory agentflow\harness agentflow_production\posterflow agentflow_studio\harness
git diff --check
```

## Expected Artifacts

- Contract or validator diff.
- Focused tests for broken evidence-chain references.
- `docs/handoff/AFS-MEMORY-RUNTIME-001.md`.
- Tracker and DEVLOG updates.

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
docs/handoff/AFS-MEMORY-RUNTIME-001.md
```

## Return Format

1. Status: `DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or `BLOCKED`.
2. Changed files.
3. Verification commands and results.
4. Evidence or artifact paths.
5. Risks and unfinished work.
6. Memory candidates for `Company/` or project docs.
7. Whether the subagent or worktree should be closed, preserved, or continued.
