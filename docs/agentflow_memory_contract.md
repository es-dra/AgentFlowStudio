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
