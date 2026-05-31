# AFS-LOULAN-API-INTAKE-GATE-CLI-001 - API Intake Gate CLI

## Task

Show Loulan API workbench context intake gate status in CLI output and the
Markdown report.

## Goal

Make `loulan-api-workbench-plan --context-projection` visibly report the
pre-context gate status to command-line operators, not only inside JSON.

## Non-goals

- Do not change request readiness logic.
- Do not require an intake report for legacy or direct projections.
- Do not infer approval from `not_supplied`.
- Do not call image, video, ASR, LLM, or external providers.
- Do not write durable Memory or Company knowledge-base content.

## Owner Role

Provider Adapter Agent + Memory / Evidence Steward + QA Reviewer

## Task Difficulty / Dispatch Mode

```text
Mode: Light
Why this mode: Output/report visibility only after the API gate contract exists.
Subagent needed: no
Close condition: CLI output and Markdown report include context intake gate
status; focused tests pass.
```

## Write Scope

- `agentflow/memory/loulan_api_workbench.py`
- `apps/cli/loulan_api_workbench_command.py`
- `tests/test_loulan_api_workbench.py`
- `TASK_TRACKER.md`, `DEVLOG.md`, and handoff docs

## Acceptance Criteria

- [x] CLI output includes `Context intake gate`.
- [x] Markdown report includes `Context intake gate`.
- [x] JSON plan still records `context_projection.decision_intake_gate`.
- [x] No provider calls, media writes, approval inference, or durable memory
      writes are added.

## Verification Commands

```powershell
.\.venv\Scripts\python.exe -B -m pytest --assert=plain tests\test_loulan_api_workbench.py -q
```

## Remote Provider Policy

- [x] No remote provider needed.

## Evidence Path

```text
docs/handoff/AFS-LOULAN-API-INTAKE-GATE-CLI-001.md
```
