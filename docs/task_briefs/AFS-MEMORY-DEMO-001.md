# AFS-MEMORY-DEMO-001 Task Brief

## Task

Harden the two-round Memory OS demonstration.

## Goal

Make the PosterFlow two-round loop more convincing as an evidence-backed
context reuse demo while keeping the boundary clear: it is not durable memory,
RAG, a vector store, or an AgentFlow runtime.

## Non-goals

- Do not add a database, vector store, hosted memory service, or durable memory
  write path.
- Do not call remote providers by default.
- Do not change MiniMax provider behavior.
- Do not claim creative quality validation or business validation.

## Owner Role

Memory / Evidence Steward.

## Branch / Worktree

```text
Branch: codex/afs-memory-demo-hardening
Worktree: C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-memory-demo-hardening
Base branch: master
```

## Write Scope

- `agentflow_production/posterflow/`
- `agentflow_studio/harness/posterflow_quality*.py`
- `workflows/posterflow_memory_demo.yaml`
- `tests/test_posterflow_workflow.py`
- `tests/test_posterflow_quality.py`
- `tests/test_posterflow_provider.py`
- Memory/PosterFlow docs under `docs/`
- `TASK_TRACKER.md` and `DEVLOG.md`

## Do Not Touch

- Web UI implementation except read-only references in docs.
- `apps/cli/` unless a test exposes a broken command path.
- Provider secrets or local config files.
- Generated image artifacts.
- Company knowledge base unless separately requested.

## Input Docs

- `AGENTS.md`
- `docs/company_operating_model.md`
- `TASK_TRACKER.md`
- `docs/alpha_readiness_report.md`
- `docs/agentflow_memory_contract.md`
- `docs/agentflow_artifact_map.md`

## Acceptance Criteria

- [ ] The demo clearly shows round 1 evidence, candidate memory, review
      decision, context bundle, round 2 reuse, and comparison output.
- [ ] Inspect/review catches broken memory/context reuse references.
- [ ] Reports distinguish raw feedback, derived signals, candidate memory,
      promotion decision, preference profile, and context bundle.
- [ ] All outputs continue to state `writes_long_term_memory: false` where
      applicable.
- [ ] No remote provider call is required for tests.

## Verification Commands

```powershell
python -m pytest tests/test_posterflow_workflow.py tests/test_posterflow_quality.py tests/test_posterflow_provider.py
python -m apps.cli.main alpha-smoke --json
git diff --check
```

## Expected Artifacts

- Hardened PosterFlow demo outputs or docs.
- Focused tests covering the improved evidence chain.
- Updated tracker and DEVLOG entry.

## Remote Provider Policy

- [x] No remote provider needed.
- [ ] Remote LLM needed. Requires `AFS_ALLOW_REMOTE_LLM=true`.
- [ ] Remote ASR needed. Requires `AFS_ALLOW_REMOTE_ASR=true`.
- [ ] Remote image needed. Requires `AFS_ALLOW_REMOTE_IMAGE=true`.
- [ ] Remote video generation needed. Requires an explicit task-specific gate.
- [ ] External download needed. Requires explicit source and artifact policy.

## Evidence Path

```text
docs/handoff/AFS-MEMORY-DEMO-001.md
```

## Return Format

1. Status: `DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or `BLOCKED`.
2. Changed files.
3. Verification commands and results.
4. Evidence or artifact paths.
5. Risks and unfinished work.
6. Memory candidates for `Company/` or project docs.
7. Whether the subagent or worktree should be closed, preserved, or continued.
