# Loulan Decision Worksheet Contract

`agentflow_loulan_decision_worksheet` turns a Loulan decision review pack into a
copy-only manual fill surface.

It is not an approval record. It keeps:

- `provider_calls_started: false`
- `writes_long_term_memory: false`
- `human_acceptance_recorded: false`

## Input

- `agentflow_loulan_decision_review_pack`

The command reads explicit decision cards from the review pack. It does not
scan Loulan directories, call providers, copy media, write Company memory, or
infer approval from ready rows.

## Outputs

- `loulan_decision_worksheet.json`
- `loulan_decision_worksheet.md`

Each worksheet row mirrors a decision card and provides empty fill fields:

- `decision_to_fill`
- `decided_by_to_fill`
- `evidence_refs_to_fill`
- `review_note_to_fill`
- `copy_target_json`

`copy_target_json` intentionally keeps `decision`, `decided_by`,
`evidence_refs`, and `review_note` empty so the worksheet cannot become a
silent approval.

## Blocking Semantics

`worksheet_status` is `awaiting_manual_decisions` when any row is pending,
missing, or invalid. If every row is already ready for context projection, the
worksheet can become `ready_for_manual_transfer`, but it still does not claim
human acceptance, business validation, provider smoke, or durable memory.

## Boundaries

The worksheet must not include private absolute paths, generated media refs,
provider credentials, signed URLs, or bearer headers. Relative evidence handles
are allowed so a reviewer can find the source material.

See
[`../examples/agentflow/loulan_decision_worksheet.example.json`](../examples/agentflow/loulan_decision_worksheet.example.json).
