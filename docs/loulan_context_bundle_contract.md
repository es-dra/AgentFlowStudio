# Loulan Context Bundle Projection Contract

`agentflow_loulan_context_bundle_projection` turns explicit Loulan human
decision records into a next-pass context bundle draft.

It does not make review decisions. If a required decision is missing, invalid,
or not marked as decided by a human, the projection blocks.

## Inputs

- `agentflow_loulan_human_review_pack`
- `agentflow_loulan_promotion_decisions`

The decisions artifact must target the review pack id and keep
`writes_long_term_memory: false`.

## Decision Semantics

Shot decisions:

- `approve_anchor`: include the shot as a next-pass anchor.
- `reject`: block the shot from next-pass reuse.
- `request_repair`: block the shot and carry it as a repair target.

Asset memory decisions:

- `promoted` or `merged`: include the memory ref in the next context bundle.
- `rejected` or `expired`: block the memory ref from reuse.

All decisions must use `decided_by: human` and include `evidence_refs`.

## Outputs

- `loulan_context_bundle_projection.json`
- `context_bundle.json`
- `next_prompt_draft.json`
- `decision_audit.json`
- `loulan_context_bundle_projection.md`

The projection may be `ready`, `partial_ready`, or blocked. A `partial_ready`
projection means some refs can be reused, while rejected or repair-requested
refs remain blocked.

## Boundaries

The projection is a side-effect-free context artifact. It must not call
providers, copy media, persist secrets, write Company memory, or claim product
acceptance, business validation, provider smoke, or durable Memory runtime.

See
[`../examples/agentflow/loulan_context_bundle_projection.example.json`](../examples/agentflow/loulan_context_bundle_projection.example.json).
