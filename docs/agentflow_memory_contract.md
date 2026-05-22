# AgentFlow Memory Contract

AgentFlow Memory is the future platform layer that turns repeated execution and
feedback into reusable project knowledge.

Phase 15.4 deepens the signal contracts. It still does not implement a memory
runtime, vector store, database, or automatic preference update.

## Contract Chain

The intended chain is:

```text
raw feedback event
-> derived feedback signal
-> memory candidate
-> promotion decision
-> accepted / rejected / merged / expired memory
```

Each step must keep evidence references so future agents can explain why a
preference or rule exists.

Phase 15.13 adds intermediate asset language on top of this chain:

```text
memory candidate
-> promotion decision
-> reusable asset profile
-> asset reuse decision
```

A candidate memory is not a reusable asset. A reusable asset profile must point
back to source intermediate assets and an explicit promotion decision.

## Raw Feedback Event

Raw feedback events are append-only records from a user, agent reviewer, or
external system.

`feedback.jsonl` remains the source of truth for raw feedback. A derived log
must not replace it.

Minimum fields:

- `schema_version`: currently `0.1.0` for AgentFlow examples.
- `feedback_id`: stable event id.
- `source`: human, agent, or external system.
- `target_type`: artifact, clip, candidate, package, run, handoff, or prompt.
- `target_id`: target identifier.
- `decision`: accepted, rejected, needs_revision, note, or published.
- `reason_tags`: machine-readable reason tags.
- `user_note`: optional human note.
- `created_at`: ISO timestamp.

See [`../examples/agentflow/feedback_event.example.jsonl`](../examples/agentflow/feedback_event.example.jsonl).

## Derived Feedback Signal

`feedback_signal_log.json` is a derived artifact for the current run.

It may summarize:

- relevant feedback event ids
- interpreted preference signals
- affected artifacts
- confidence level
- suggested follow-up

It must not be used as the primary feedback store. `feedback.jsonl` remains the
source of truth even when a derived signal is easier for an Agent to read.

## Memory Candidate

`memory_candidates.json` is a candidate store.

A memory candidate may include:

- `candidate_id`
- `promotion_status`
- `memory_type`
- `statement`
- `evidence_refs`
- `confidence`
- `suggested_promotion_condition`

For the current MVP, `promotion_status` must remain `candidate`.

Candidate memory is not accepted memory. Agents may use candidates as review
inputs, but must not treat them as durable preferences or project facts without
an explicit promotion decision.

See [`../examples/agentflow/memory_candidate.example.json`](../examples/agentflow/memory_candidate.example.json).

## Promotion Decision

A promotion decision is explicit and reviewable. Current decision statuses:

- `promoted`
- `rejected`
- `merged`
- `expired`

The current examples use `promotion_mode: human_reviewed` and
`writes_long_term_memory: false` to avoid implying that this repository now owns
a long-term memory store.

See [`../examples/agentflow/memory_promotion_decision.example.json`](../examples/agentflow/memory_promotion_decision.example.json).

## Reusable Asset Profile

`agentflow_reusable_asset_profile` records a promoted, evidence-backed asset
that may be considered in a future task.

Minimum fields:

- `schema_version`: currently `0.1.0`.
- `artifact_type`: `agentflow_reusable_asset_profile`.
- `asset_profile_id`: stable profile id.
- `source_intermediate_asset_ids`: source candidate assets.
- `promotion_decision_ref`: explicit promotion decision reference.
- `reuse_policy`: allowed modules, task types, and review requirements.
- `active_status`: active, inactive, or superseded.

Reusable asset profiles are not automatic long-term preference writes. They are
reviewable assets that future Agents may consider through an asset reuse
decision.

See [`../examples/agentflow/reusable_asset_profile.example.json`](../examples/agentflow/reusable_asset_profile.example.json).

## Asset Reuse Decision

`agentflow_asset_reuse_decision` records why an Agent selected or rejected
reusable assets for a target task. It is decision-only and must not execute a
workflow or invoke a skill.

See [`../examples/agentflow/asset_reuse_decision.example.json`](../examples/agentflow/asset_reuse_decision.example.json).

`agentflow.memory.assets.validate_asset_memory_contract_set` validates the
current asset and memory contract chain as an in-memory artifact set. It is a
contract validator, not Memory runtime: it does not promote candidates, write
long-term memory, create reusable profiles, or execute asset reuse decisions.

## Cost-Quality Signal

`cost_quality_trace.json` records execution strategy evidence, not a guarantee
of creative quality.

For local deterministic MVP runs, it should identify:

- `provider`: `local_deterministic`
- `execution_mode`: `local_deterministic`
- input and output artifact refs
- quality proxy metrics
- estimated cost, usually `0`

Future model-backed runs may extend provider, model, latency, token, retry, and
cost fields, but those fields should remain trace evidence for strategy review,
not a substitute for human acceptance.
