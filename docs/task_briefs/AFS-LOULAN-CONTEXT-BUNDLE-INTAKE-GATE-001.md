# AFS-LOULAN-CONTEXT-BUNDLE-INTAKE-GATE-001 - Context Bundle Intake Gate

## Task

Let `loulan-context-bundle` consume an optional
`agentflow_loulan_decision_intake_report` as a hard pre-context gate.

## Goal

Close the gap between decision intake validation and context projection. When
an operator supplies an intake report, context artifacts should be written only
when that report is ready and matches the submitted decisions.

## Non-goals

- Do not fill or approve Loulan human decisions.
- Do not infer approval from an intake report.
- Do not call image, video, ASR, LLM, or external providers.
- Do not scan Loulan directories or write Company memory.
- Do not require databases, RAG, vector stores, or durable Memory runtime.

## Owner Role

Memory / Evidence Steward + Workflow Engineer + QA Reviewer

## Task Difficulty / Dispatch Mode

```text
Mode: Standard
Why this mode: The slice changes one CLI/protocol boundary with deterministic
tests and no provider/runtime side effects.
Subagent needed: no
Close condition: blocked/stale intake reports stop projection, ready reports
leave gate evidence, docs/tracker/handoff are updated, verification passes.
```

## Write Scope

- `agentflow/memory/loulan_context_bundle.py`
- `apps/cli/loulan_context_bundle_command.py`
- `tests/test_loulan_context_bundle.py`
- `docs/loulan_context_bundle_contract.md`
- `docs/loulan_decision_intake_contract.md`
- `examples/agentflow/loulan_context_bundle_projection.example.json`
- `examples/agentflow/contract_registry.example.json`
- `examples/agentflow/contract_audit_report.example.json`
- `TASK_TRACKER.md`, `DEVLOG.md`, and handoff docs

## Acceptance Criteria

- [x] `build_loulan_context_bundle_projection` accepts an optional decision
      intake report.
- [x] Supplied blocked intake reports raise before context artifacts are built.
- [x] Supplied ready intake reports leave `decision_intake_gate` evidence.
- [x] Supplied stale intake reports fail when their rows do not match the
      submitted decisions.
- [x] CLI exposes `--decision-intake-report`.
- [x] CLI exits without writing context artifacts when the supplied intake
      report is blocked.
- [x] No provider calls, durable memory writes, approval inference, or Company
      knowledge-base writes are added.

## Verification Commands

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_loulan_context_bundle.py -q
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_loulan_decision_intake.py tests\test_loulan_decision_worksheet.py tests\test_loulan_decision_review_pack.py tests\test_loulan_decision_template.py tests\test_loulan_context_bundle.py tests\test_contract_examples.py tests\test_agentflow_contract_audit.py tests\test_cli_command_registry_boundaries.py -q
.\.venv\Scripts\python.exe -B -m apps.cli.main loulan-context-bundle --help
```

## Remote Provider Policy

- [x] No remote provider needed.

## Evidence Path

```text
docs/handoff/AFS-LOULAN-CONTEXT-BUNDLE-INTAKE-GATE-001.md
```
