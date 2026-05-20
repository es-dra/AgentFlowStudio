# AgentFlow Memory Contract

AgentFlow Memory is the future platform layer that turns repeated execution and
feedback into reusable project knowledge.

Phase 15.2 only defines the contract boundaries. It does not implement a
memory runtime, vector store, database, or automatic preference update.

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

It must not be used as the primary feedback store.

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

## Promotion Decision

A future promotion decision should be explicit and reviewable. Suggested
statuses:

- `promoted`
- `rejected`
- `merged`
- `expired`

Automatic promotion is out of scope for the current repository phase.
