# AFS-LOULAN-API-INTAKE-GATE-001 - API Intake Gate

## Task

Make `loulan-api-workbench-plan` validate and summarize the
`decision_intake_gate` embedded in supplied Loulan context projections.

## Goal

Prevent a dry-run provider request preview from consuming a context projection
that claims a blocked supplied decision-intake gate, and preserve gate evidence
inside the API workbench plan.

## Non-goals

- Do not require an intake report for legacy or direct decision projections.
- Do not infer approval from `not_supplied`.
- Do not call image, video, ASR, LLM, or external providers.
- Do not write generated media, provider secrets, Company memory, or durable
  Memory runtime state.

## Owner Role

Provider Adapter Agent + Memory / Evidence Steward + QA Reviewer

## Task Difficulty / Dispatch Mode

```text
Mode: Standard
Why this mode: Deterministic validation boundary across one API helper and
focused tests.
Subagent needed: no
Close condition: supplied blocked intake gates are rejected, accepted gates are
summarized, docs/tracker are updated, and verification passes.
```

## Write Scope

- `agentflow/memory/loulan_api_context.py`
- `tests/test_loulan_api_workbench.py`
- `docs/loulan_api_workbench_contract.md`
- `examples/agentflow/contract_registry.example.json`
- `examples/agentflow/contract_audit_report.example.json`
- `TASK_TRACKER.md`, `DEVLOG.md`, and handoff docs

## Acceptance Criteria

- [x] API workbench plan includes `context_projection.decision_intake_gate`
      when a projection is supplied.
- [x] `not_supplied` projections remain compatible and are not treated as
      approval.
- [x] `ready_for_context_bundle` gates with `context_bundle_command_ready:
      true` are accepted.
- [x] Blocked supplied gates are rejected before request preview is built.
- [x] No provider calls, media writes, secrets, approval inference, or durable
      memory writes are added.

## Verification Commands

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_loulan_api_workbench.py -q
```

## Remote Provider Policy

- [x] No remote provider needed.

## Evidence Path

```text
docs/handoff/AFS-LOULAN-API-INTAKE-GATE-001.md
```
