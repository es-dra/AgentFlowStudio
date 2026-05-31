# Loulan B01 Decision Import Contract

`loulan-b01-decision-import` imports explicit local B01 shot review decisions
into the existing `agentflow_loulan_promotion_decisions` file shape.

This command is a bridge, not an approval engine. It only transfers human-filled
shot decisions from the Loulan project decision template into AFS required
decision slots that already exist in a Loulan human review pack.

## Inputs

- `agentflow_loulan_human_review_pack`
- `loulan_b01_human_review_decision_template`

The local B01 file must keep:

- `block_id: B01`
- `provider_calls_started: false`
- `writes_long_term_memory: false`
- `human_acceptance_recorded: false`

## Output

- `loulan_b01_decisions.imported.json`
- `loulan_b01_decisions.imported.md`

The JSON output keeps the artifact type
`agentflow_loulan_promotion_decisions` so downstream decision review, worksheet,
intake, context bundle, and API preview gates can reuse the same structural
contract.

## Import Rules

- Only local `decision_items` with a matching `shot:{target_shot_id}` required
  decision slot are imported.
- Empty or `pending_human_review` local decisions stay pending.
- Supported B01 shot decisions are `approve_anchor`, `request_repair`, and
  `reject`.
- `request_repair` requires a non-empty `repair_note`.
- Ready imported decisions must include relative evidence refs from
  `candidate_ref` and/or `registry_memory_ref`.
- Local absolute paths, provider URLs, signed URLs, tokens, and media video refs
  are rejected by the shared Loulan safety guard.

## Boundaries

The import does not call providers, generate media, copy media, write Company
memory, write durable Memory runtime state, or record product acceptance.

A partially imported file remains blocked by `loulan-decision-intake` until all
required decisions have explicit human-filled values, evidence refs, and review
notes.
