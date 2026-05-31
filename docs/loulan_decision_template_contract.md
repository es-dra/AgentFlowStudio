# Loulan Decision Template Contract

`agentflow_loulan_promotion_decisions` templates turn a Loulan human review pack
into fillable decision slots for shots and candidate asset memory.

The template is not an approval record. Every generated decision starts as
`pending_human_review`, with empty `decided_by`, empty `evidence_refs`, and:

- `provider_calls_started: false`
- `writes_long_term_memory: false`
- `human_acceptance_recorded: false`

## Inputs

- `agentflow_loulan_human_review_pack`

The command reads the review pack's `next_pass_readiness.required_decisions`,
shot review cards, and asset review cards. It does not scan Loulan directories,
call providers, copy media, or write Company memory.

## Outputs

- `loulan_decisions.template.json`
- `loulan_decisions.template.md`

The JSON output may be copied into a real decisions file only after a person
fills `decision`, sets `decided_by: human`, adds `evidence_refs`, and records a
bounded review note.

## Blocking Semantics

If this unfilled template is passed into `loulan-context-bundle`, the projection
must block because the decisions are not human decisions. This prevents pending
review material from being reused as approved context.

## Boundaries

The template must not claim human acceptance, provider smoke, business
validation, durable Memory runtime, or long-term memory promotion.

See
[`../examples/agentflow/loulan_promotion_decisions_template.example.json`](../examples/agentflow/loulan_promotion_decisions_template.example.json).
