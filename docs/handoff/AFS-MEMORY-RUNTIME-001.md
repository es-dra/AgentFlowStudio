# AFS-MEMORY-RUNTIME-001 Handoff

Date: 2026-05-27
Branch: `codex/afs-memory-runtime-contract`
Worktree: `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-memory-runtime-contract`

## Scope

Strengthened the PosterFlow feedback-to-context evidence chain for Local Alpha
0.3 without adding durable memory writes, databases, RAG, vector stores,
prefix-cache services, hosted memory services, or remote provider behavior.

The audited chain is now:

```text
raw feedback
-> derived feedback signal
-> candidate memory
-> explicit promotion decision
-> preference profile
-> context bundle / assembly trace
-> next-round prompt
-> round-2 prompt pack / comparison report
```

## Changed

- Added promotion decision refs to `poster_preference_profile.json`,
  `context_bundle.json`, `context_assembly_trace.json`, `next_round_prompt.json`,
  round-2 prompt context usage, and `poster_round_comparison.json`.
- Added quality checks that fail when memory review events no longer match the
  decision artifact, context loses promotion decision refs, next-round prompt
  loses promotion decision refs, or round-2 evidence-chain reuse loses promotion
  decision refs.
- Added contract/example checks requiring promotion decisions to preserve
  candidate evidence and declaring context reuse as no-durable-write.
- Updated memory/artifact docs with explicit role boundaries for raw feedback,
  derived signal, candidate memory, promotion decision, preference profile,
  context bundle, and next-round prompt.

## Boundary

This remains a side-effect-free contract and demo-artifact path.

- `writes_long_term_memory` remains `false` on promotion, profile, context,
  trace, next prompt, comparison, and quality feedback surfaces.
- No remote provider calls are required by tests.
- No Web UI, provider config, `.env`, `.dev.vars`, `configs/models.yaml`,
  generated media, runtime runs, `TASK_TRACKER.md`, `DEVLOG.md`, or private
  Company knowledge base files were edited.

## Verification

```powershell
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests/test_agentflow_asset_memory_validator.py tests/test_contract_examples.py tests/test_posterflow_workflow.py tests/test_posterflow_quality.py tests/test_posterflow_provider.py
# 65 passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main alpha-smoke --json
# exited 0; status is blocked because remote image provider env is unset; writes_runtime_artifacts is false

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m compileall agentflow\memory agentflow\harness narratostudio\posterflow narratocut\harness
# passed

git diff --check
# passed with Windows line-ending warnings only
```

## Risks

- The PosterFlow review gate is stricter now. Any future artifact producer that
  omits promotion decision refs in profile, context, next prompt, or comparison
  will fail review until it is updated.
- The context bundle is still deterministic artifact assembly, not a measured
  context-selection quality system.
