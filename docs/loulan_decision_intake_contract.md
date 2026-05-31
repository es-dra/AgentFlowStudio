# Loulan Decision Intake Report Contract

`agentflow_loulan_decision_intake_report` validates a manually filled Loulan
decision file against a decision worksheet before context bundle projection.

It is not an approval record. It keeps:

- `provider_calls_started: false`
- `writes_long_term_memory: false`
- `human_acceptance_recorded: false`

## Inputs

- `agentflow_loulan_decision_worksheet`
- `agentflow_loulan_promotion_decisions`

The command checks that the decisions file matches the worksheet's required
targets, uses allowed decision values, was filled by a human, includes evidence
refs, and includes a review note. It does not scan Loulan directories, call
providers, write Company memory, or run context projection.

## Outputs

- `loulan_decision_intake_report.json`
- `loulan_decision_intake_report.md`

The report classifies each required row as:

- `ready_for_context_bundle`
- `pending_manual_decision`
- `invalid_decision`

`context_bundle_command_ready` becomes true only when every worksheet row has a
valid manual decision and there are no unexpected decision refs.

## Blocking Semantics

The report blocks when decisions are missing, pending, invalid, or unexpected.
Ready means the decision file is structurally fit for `loulan-context-bundle`;
it does not mean human acceptance, business validation, provider smoke, or
durable Memory runtime promotion.

`loulan-context-bundle` can consume the report with
`--decision-intake-report`. When supplied, the report must be ready and must
match the submitted decisions; otherwise context projection stops before
writing artifacts.

## Boundaries

The report must not include private absolute paths, generated media refs,
provider credentials, signed URLs, or bearer headers. Relative evidence handles
are allowed for traceability.

See
[`../examples/agentflow/loulan_decision_intake_report.example.json`](../examples/agentflow/loulan_decision_intake_report.example.json).
