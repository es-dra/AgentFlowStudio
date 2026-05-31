# Loulan Human Review Pack Contract

`agentflow_loulan_human_review_pack` prepares Loulan B01 review material for a
human promotion or rejection pass.

It is a review surface, not an approval record. It must keep:

- `provider_calls_started: false`
- `writes_long_term_memory: false`
- `human_acceptance_recorded: false`

## Inputs

- `agentflow_loulan_memory_package`
- `agentflow_loulan_api_workbench_plan`
- explicit Loulan project root used only to read manifest-declared review
  evidence
- block id such as `B01`

The command reads known manifest and review files. It does not restructure the
Loulan asset project, scan arbitrary directories, call providers, copy media,
or write Company memory.

## Outputs

- `loulan_human_review_pack.json`
- `shot_review_cards.json`
- `promotion_decision_drafts.json`
- `feedback_event_draft.json`
- `loulan_human_review_pack.md`

Shot cards contain candidate ids, sha256 values, relative evidence refs,
blocking reasons, and allowed review decisions. Asset cards surface candidate,
approved/promoted, and rejected memory refs separately.

Promotion decision drafts are templates only. The allowed decisions are
`promoted`, `merged`, `rejected`, and `expired`, but the draft status remains
`pending_human_review` until a person makes the decision.

## Boundaries

The pack must not include private absolute paths, generated video refs,
provider credentials, signed URLs, or bearer headers. Relative refs to review
cards and local evidence manifests are allowed as traceability handles.

The pack can say a next pass is blocked or ready for human review, but it cannot
claim human acceptance, provider smoke success, business validation, or durable
Memory runtime promotion.

See
[`../examples/agentflow/loulan_human_review_pack.example.json`](../examples/agentflow/loulan_human_review_pack.example.json).
