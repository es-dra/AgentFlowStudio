# AFS-MEMORY-DEMO-001 Handoff

Date: 2026-05-27
Branch: `codex/afs-memory-demo-hardening`
Worktree: `C:\Users\chenzy\.config\superpowers\worktrees\AgentFlowStudio\afs-memory-demo-hardening`

## Scope

Hardened the PosterFlow two-round Memory OS demo by making the evidence path
explicit in `poster_round_comparison.json` and `poster_two_round_report.md`.

The strengthened path is:

```text
round 1 evidence
-> candidate memory
-> review decision
-> context bundle
-> round 2 reuse
-> comparison output
```

## Changed

- Added `evidence_chain` to `poster_round_comparison.json`.
- Rendered the evidence chain in `poster_two_round_report.md`.
- Added quality checks that fail when the comparison loses the review decision,
  context bundle reference, required stages, or `writes_long_term_memory: false`
  boundary.
- Added focused tests for the evidence-chain artifact and broken review
  decision reference.

## Boundary

This remains demo evidence only. It does not add durable Memory runtime, RAG,
vector store, database, provider behavior, Web UI behavior, or automatic memory
promotion.

## Verification

```powershell
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m pytest tests/test_posterflow_workflow.py tests/test_posterflow_quality.py tests/test_posterflow_provider.py
# 23 passed

D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main alpha-smoke --json
# exited 0; status is blocked because remote image provider env is unset

git diff --check
# passed with Windows line-ending warnings only
```

## Evidence Paths

- `poster_round_comparison.json`
- `poster_two_round_report.md`
- `quality_report.json`
- `review_report.json`
- `docs/handoff/AFS-MEMORY-DEMO-001.md`
