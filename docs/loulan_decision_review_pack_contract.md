# Loulan Decision Review Pack Contract

`agentflow_loulan_decision_review_pack` turns a Loulan human review pack and a
decision file into an operator-facing gap report before context projection.

It is not an approval record. It keeps:

- `provider_calls_started: false`
- `writes_long_term_memory: false`
- `human_acceptance_recorded: false`

## Inputs

- `agentflow_loulan_human_review_pack`
- `agentflow_loulan_promotion_decisions`

The command reads the review pack's required decision refs and the supplied
decision slots. It does not scan Loulan directories, call providers, copy media,
write Company memory, or infer approval from draft review material.

## Outputs

- `loulan_decision_review_pack.json`
- `loulan_decision_review_pack.md`

Each decision card reports whether a required slot is missing, still pending,
invalid, or ready for context projection. Ready means the slot has an explicit
human decision, evidence refs, and a decision value allowed for that target
type. It does not mean product acceptance or business validation.

## Blocking Semantics

The pack status is blocked when any required decision is missing, invalid, or
pending human input. This gives a reviewer a bounded fill list before running
`loulan-context-bundle`.

## Boundaries

The pack must not include private absolute paths, generated media refs,
provider credentials, signed URLs, or bearer headers. Relative refs to review
cards and evidence handles are allowed for traceability.

The pack can say that decisions are ready for context projection, but it cannot
claim human acceptance, provider smoke success, business validation, or durable
Memory runtime promotion.

See
[`../examples/agentflow/loulan_decision_review_pack.example.json`](../examples/agentflow/loulan_decision_review_pack.example.json).
