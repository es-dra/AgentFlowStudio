# AgentFlow Contract Validation

AgentFlow contract validation is the static audit gate for committed
AgentFlow examples and documentation links.

Phase 15.7 defines only a local example audit report and test coverage. It does
not implement a runtime validator, registry service, Router runtime, skill
runtime, Memory runtime, database, or cross-module execution.

## Purpose

The audit gate should catch contract drift before runtime work depends on the
contracts.

It checks that:

- registry entries point to committed examples and docs
- examples can be parsed as JSON or JSONL
- AgentFlow examples use `schema_version: 0.1.0`
- registry `artifact_type` values match example `artifact_type` values
- examples do not contain private paths, secrets, generated media, or local run
  outputs
- Router decisions remain decision-only
- memory candidates remain candidate-only
- derived feedback and cost-quality traces do not become stronger claims than
  their contracts allow

## Audit Report

`agentflow_contract_audit_report` is a static report artifact.

Minimum fields:

- `schema_version`: currently `0.1.0`.
- `artifact_type`: `agentflow_contract_audit_report`.
- `audit_id`: stable audit id.
- `audit_scope`: `static_contract_examples`.
- `source_registry`: registry example path.
- `runtime_status`: `not_implemented`.
- `does_not_execute`: must be `true`.
- `overall_status`: `passed`, `warning`, or `failed`.
- `audited_contracts`: per-contract path and schema results.
- `boundary_checks`: semantic boundary checks.
- `validated_runtime_capabilities`: must remain empty for this phase.

See
[`../examples/agentflow/contract_audit_report.example.json`](../examples/agentflow/contract_audit_report.example.json).

For PR-level review readiness, use
[`agentflow_pr_review_checklist.md`](agentflow_pr_review_checklist.md).

## Boundary

This audit gate is evidence for committed examples only. It must not be treated
as proof that AgentFlow has a runtime router, skill executor, memory store, or
workflow orchestrator.

Future runtime validation may build on this shape, but it should be introduced
as a separate phase with explicit execution semantics and failure modes.
