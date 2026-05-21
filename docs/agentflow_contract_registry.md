# AgentFlow Contract Registry

The AgentFlow contract registry is a local-first discovery index for current
contract examples and their documentation.

Phase 15.6 defines only the registry example and validation expectations. It
does not implement a registry service, Router runtime, skill runtime, Memory
runtime, database, permission engine, or cross-module execution.

## Purpose

The registry should help an Agent answer:

- Which AgentFlow contract examples exist?
- Which `artifact_type` does each example declare?
- Which document explains the contract?
- Which validation rules protect the contract boundary?
- Does this registry execute anything?

For Phase 15.6, the answer to the last question must be no.

## Registry Artifact

`agentflow_contract_registry` records the current contract discovery surface.

Minimum fields:

- `schema_version`: currently `0.1.0`.
- `artifact_type`: `agentflow_contract_registry`.
- `registry_id`: stable id for this registry draft.
- `registry_scope`: `contract_discovery`.
- `runtime_status`: `not_implemented`.
- `does_not_execute`: must be `true`.
- `contracts`: list of known AgentFlow contract surfaces.
- `validation_rules`: local validation rules for examples and boundaries.

See
[`../examples/agentflow/contract_registry.example.json`](../examples/agentflow/contract_registry.example.json).

## Contract Entries

Each registry entry should include:

- `artifact_type`: machine-facing artifact type.
- `example_path`: committed minimal example path.
- `doc_path`: documentation path for the contract.
- `contract_surface`: concise contract role.

The registry should index contracts that already exist in this repository. It
should not invent future runtime artifacts just to fill out a platform map.

## Validation Boundary

Current validation should stay lightweight:

- examples parse as JSON or JSONL
- examples declare `schema_version: 0.1.0`
- registry `artifact_type` values match the pointed examples
- examples avoid private paths, secrets, generated media, and local run outputs
- Router decisions remain decision-only
- memory candidates remain candidate-only

This is validation of committed contract examples. It is not runtime validation
for workflow execution.

## Non-Goals

The registry must not:

- execute workflows
- call local or remote providers
- select or invoke skills
- write memory
- publish content
- replace `inspect-run` or `review-run`
- become a database-backed registry service
