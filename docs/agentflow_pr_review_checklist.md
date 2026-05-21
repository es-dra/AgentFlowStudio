# AgentFlow PR Review Checklist

Phase 15.8 defines the AgentFlow contract PR review checklist. It is a
human-readable review gate for AgentFlow contract-layer changes.

This checklist does not implement runtime validation, does not execute workflows,
and does not replace `inspect-run` or `review-run`.

## When To Use

Use this checklist for PRs that change AgentFlow platform contract docs,
examples, or tests, especially:

- `docs/agentflow_*.md`
- `docs/*_contract.md`
- `examples/agentflow/*`
- `tests/test_contract_examples.py`
- `tests/test_agentflow_contract_audit.py`

It can also be used as an Agent preflight checklist before opening a PR.

## Scope Boundary

The checklist verifies review readiness for static contract work only.

It must not be treated as proof that the repository has:

- Router runtime
- skill runtime
- Memory runtime
- runtime validation service
- registry service
- database-backed contract storage
- cross-module execution
- hosted API or Web UI

## Required Review Questions

Contract identity:

- Does every new example declare `schema_version: 0.1.0`?
- Does every example use a stable `artifact_type`?
- Is the artifact name already listed in the registry or intentionally out of
  registry scope?
- Does the linked doc explain the contract role without inventing runtime
  behavior?

Semantic boundaries:

- Is a router decision still only a decision record?
- Is a memory candidate still only a candidate until a promotion decision?
- Is a feedback signal clearly derived from feedback events?
- Is a cost-quality trace execution evidence rather than a quality guarantee?
- Are `feedback.jsonl` and derived feedback artifacts kept separate?

Repository hygiene:

- Are there no private paths, secrets, tokens, cookies, signed URLs, generated
  media, or local run outputs in examples?
- Are docs linked from `docs/README.md` when they should be discoverable?
- Is `DEVLOG.md` updated with scope and verification evidence?
- Are unrelated Web UI, CLI, workflow, runtime, or generated data changes
  excluded?

## Verification Gate

Run these commands before claiming the PR is ready:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_contract_examples.py
.venv\Scripts\python.exe -m pytest tests/test_agentflow_contract_audit.py
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m compileall apps narratocut narratostudio tests
git diff --check
.venv\Scripts\python.exe -m apps.cli.main --help
.venv\Scripts\python.exe -m apps.cli.main version
```

If a command cannot run, the PR description must say why and describe the
remaining risk.

## PR Description Requirements

Every AgentFlow contract PR should include:

- summary of changed contracts
- contract notes for any new or changed artifact semantics
- explicit out-of-scope list
- verification commands and actual results
- known limitations or residual risks

For docs-only contract work, the out-of-scope list should be more explicit than
the feature list. This keeps reviewers focused on whether the contract boundary
is clean, not whether future runtime behavior has already been implemented.
