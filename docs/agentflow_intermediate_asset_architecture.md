# AgentFlow Intermediate Asset Architecture

Phase 15.13 defines the architecture language for reusable intermediate
assets. It does not implement Memory runtime, does not implement Router runtime,
does not implement skill runtime, does not implement a database, and does not
execute workflows.

## Core Chain

The intended learning loop is:

```text
Agent action -> artifact -> feedback signal -> memory candidate -> promotion decision -> reusable asset
```

An intermediate asset is not a chat transcript, temporary UI state, or durable
long-term memory. It is a structured, reviewable asset candidate that keeps
source and evidence references so a later Agent can understand why it exists.

## Contract Surfaces

`agentflow_intermediate_asset` records a reusable candidate produced during a
run. It must include source artifact references, evidence references, and
`reuse_status: candidate`.

`agentflow_reusable_asset_profile` records an asset that has been explicitly
promoted for reuse. It must reference the source intermediate assets and a
promotion decision. A reusable profile is still a contract artifact, not an
automatic global preference store.

`agentflow_asset_reuse_decision` records why an Agent chose to reuse one asset
profile and reject another for a target task. It must be decision-only and must
not execute the task.

The implementation entry point for asset/memory contract validation is
`agentflow.memory.assets.validate_asset_memory_contract_set`. It validates an
in-memory artifact set and returns `agentflow_asset_memory_validation`; it does
not execute workflows, promote memory, create asset profiles, or write durable
state.

`agentflow.memory.narratostudio_assets.build_narratostudio_asset_memory_contract_set`
is the NarratoStudio smoke adapter. It maps existing run payloads into the same
contract set for validation only. It does not read run directories, write
profiles, execute durable candidate promotion, or make the resulting profile
durable.

## NarratoStudio Asset Examples

NarratoStudio should treat these as likely intermediate asset kinds:

- character reference
- style constraint
- prompt attempt
- generation result summary
- acceptance or rejection reason
- cost-quality evidence

These assets help the system learn which creative rules, prompts, and execution
strategies converge toward the user's preferred production style.

The Phase 15.21 smoke loop uses current NarratoStudio artifacts as evidence:

- `production_handoff.json`
- `memory_candidates.json`
- `feedback_signal_log.json`
- `cost_quality_trace.json`

The resulting reusable profile is still a contract payload requiring human
review. It is not a persisted asset store entry.

## Boundaries

This phase is still contract-layer work:

- no Memory runtime
- no vector store, database, cache service, or file repository service
- no Router runtime
- no skill runtime
- no workflow changes
- does not execute workflows
- no CLI changes
- no remote provider calls
- no long-term memory writes

Candidate memory must not be treated as accepted memory. A reusable asset
profile must not become an active preference unless it references an explicit
promotion decision.
