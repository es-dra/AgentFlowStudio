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

`agentflow.memory.agentflow_production_assets.build_agentflow_production_asset_memory_contract_set`
is the AgentFlow Production smoke adapter. It maps existing run payloads into the same
contract set for validation only. It does not read run directories, write
profiles, execute durable candidate promotion, or make the resulting profile
durable.

`agentflow.memory.agentflow_production_assets.validate_agentflow_production_asset_feedback_sources`
validates the AgentFlow Production source payloads before that mapping. It keeps
`memory_candidates.json` candidate-only, verifies `feedback_signal_log.json` is
derived from `feedback.jsonl`, requires local deterministic cost-quality
evidence, and checks that `production_handoff.json` still references the prompt
pack artifact.

`agentflow.memory.agentflow_production_review.review_agentflow_production_asset_feedback_loop`
composes the source validation, AgentFlow Production smoke adapter, and AgentFlow
asset/memory contract-set validation into one review artifact. If source
validation fails, it marks the asset/memory step `not_run` instead of building
contracts from broken source semantics.

`agentflow.harness.agentflow_production_review.validate_agentflow_production_asset_feedback_review`
validates that composed review artifact as a harness-level gate. It checks the
review-only boundary, embedded validation status consistency, failed-source
skip behavior, and private path/secret hygiene without re-running workflows.

## AgentFlow Production Asset Examples

AgentFlow Production should treat these as likely intermediate asset kinds:

- character reference
- style constraint
- prompt attempt
- generation result summary
- acceptance or rejection reason
- cost-quality evidence

These assets help the system learn which creative rules, prompts, and execution
strategies converge toward the user's preferred production style.

The Phase 15.21 smoke loop uses current AgentFlow Production artifacts as evidence:

- `production_handoff.json`
- `memory_candidates.json`
- `feedback_signal_log.json`
- `cost_quality_trace.json`

The resulting reusable profile is still a contract payload requiring human
review. It is not a persisted asset store entry.

Phase 15.22 adds a source validation step before mapping these artifacts. This
keeps the smoke adapter from hiding broken source semantics behind a successful
asset/memory contract-set validation.

Phase 15.23 adds a composed review surface over the same in-memory payloads. It
is meant for Agent-readable review and gating, not persistence or runtime
execution.

Phase 15.24 adds the harness validator for that review artifact. The validator
inspects an already-built review artifact only; it does not rebuild contracts
or make the review durable.

Phase 15.25 adds a decision-only gate over that validation artifact. Passing the
gate only allows later dry-run reuse planning or human review; it does not
promote memory, persist reusable assets, or execute workflows.

Phase 15.26 adds that dry-run reuse planning surface. It turns a passed gate and
existing review artifact into `agentflow_production_asset_reuse_dry_run_plan`
so a later Agent can see candidate reuse actions before any execution path is
opened.

Phase 15.27 adds a read-only review surface for the whole dry-run reuse chain.
It checks that the review, validation, gate, and dry-run plan refer to the same
handoff/run, preserve side-effect boundaries, and remain ready or blocked
without executing reuse.

Phase 15.28 adds a reusable in-memory fixture builder for that same chain. It
does not define a new artifact type; it only composes the existing review,
validation, gate, dry-run plan, and reuse review payloads for repeatable tests.

Phase 15.29 adds `audit_agentflow_production_asset_reuse_chain_fixture` as a narrow
smoke audit over that fixture-built chain. It verifies expected chain keys,
artifact types, ready/blocked status shapes, and side-effect boundaries. It
does not create a contract artifact or execute reuse.

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
