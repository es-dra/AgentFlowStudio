# Production Memory Architecture

Status: first generic implementation slice for `AFS-PRODUCTION-MEMORY-LOOP-001`.

## Positioning

AgentFlow Studio is currently positioned as a memory-driven AI content
production workbench. This slice implements the first generic production-memory
loop without binding the product to a single project, provider, or demo module.

The technical layer can still be described internally as context assembly from
verified production evidence, human feedback, and project memory. The product
surface should say Production Memory Architecture instead of treating that
internal layer as the main narrative.

## Operator Loop

```text
project_input
  -> artifact_ledger
  -> feedback_events
  -> memory_candidates
  -> promotion_decisions
  -> context_bundle
  -> pass_readiness
  -> next_pass_bundle
  -> next_context_handoff
  -> next_task_packet
  -> next_pass_result_scaffold
  -> explicit next_pass_result input
  -> next_pass_review
  -> explicit next_pass_promotion_decision
  -> next_pass_reviewed_feedback_overlay
  -> session_report
  -> company_kb_feedback_candidate_packet
  -> operator_loop_run_manifest
  -> operator_feedback_event
  -> operator_feedback_candidate_packet
  -> explicit operator_feedback_candidate_promotion_decision
  -> operator_feedback_candidate_reviewed_context_overlay
  -> operator_manifest_check
  -> operator_handoff_packet
  -> operator_run_package
  -> operator_run_package_check
```

The committed example lives at:

```text
examples/agentflow/production_memory_loop.example.json
```

The required root identifiers are:

```json
{
  "kind": "agentflow_production_memory_loop",
  "schema_version": "production-memory-loop/v1"
}
```

## Source Records

- `project_input`: sanitized operator goal and initial source refs.
- `artifact_ledger`: reviewed artifacts and their next-context eligibility.
- `feedback_events`: operator or reviewer feedback tied to source artifacts.
- `memory_candidates`: candidate memory statements derived from evidence.
- `promotion_decisions`: explicit review decisions for memory candidates.

## Derived Artifacts

- `context_bundle`: lists both `included_refs` and `blocked_refs`.
- `pass_readiness`: states whether a no-provider next pass can be prepared.
- `next_pass_bundle`: no-provider planning artifact that uses only
  `context_bundle.included_refs` and keeps blocked refs out of the next pass.
- `next_context_handoff`: no-provider operator handoff for the next AI task.
  It lists next-context refs separately from blocked refs, includes a bounded
  task prompt, and repeats non-claim boundaries for the next operator.
- `next_task_packet`: no-provider task entry packet built from a ready
  next-context handoff. It exposes only allowed context refs to the next AI
  task, keeps blocked refs visible but excluded, and repeats the non-claim
  boundaries.
- `next_pass_result_scaffold`: no-provider local envelope for an
  operator-supplied next-pass result. It can prefill allowed context refs from
  a ready next-task packet, but it does not execute a model, generate content,
  capture feedback, or claim acceptance.
- `next_pass_review`: no-provider review artifact for an explicitly supplied
  next-pass result. It checks that result outputs used only
  `allowed_context_refs`, records blocked or unknown refs, and derives
  candidate-only feedback plus pending promotion-decision templates.
- `next_pass_promotion_decision`: explicit operator decision for one
  next-pass feedback candidate. It is still no-provider, writes no long-term
  memory, writes no Company KB, and does not claim human acceptance.
- `next_pass_reviewed_feedback_overlay`: no-provider audit artifact that shows
  whether the explicitly reviewed next-pass feedback candidate was included in
  or blocked from the next derived context bundle.
- `session_report`: read-only operator audit artifact that summarizes the run,
  included refs, blocked refs, optional feedback capture, optional promotion
  decision, next operator action, and non-claim boundaries.
- `company_kb_feedback_candidate_packet`: candidate-only project-to-Company
  feedback packet generated from a session report. It is not a Company KB
  write, not durable memory, and not a promotion decision.
- `operator_loop_run_manifest`: an auditable no-provider orchestration manifest
  that records all operator-loop nodes, generated artifact refs, controls, and
  non-claim boundaries for one local run.
- `operator_feedback_event`: evidence-only feedback captured against a selected
  operator-loop manifest node. It is not human acceptance, not memory, not a
  memory candidate, and not a promotion decision.
- `operator_feedback_candidate_packet`: candidate-only packet drafted from an
  evidence-only operator feedback event. It includes one memory candidate and a
  pending promotion decision template, but it writes no long-term memory, writes
  no Company KB, and does not make the candidate promoted memory.
- `operator_feedback_candidate_promotion_decision`: explicit operator decision
  for one operator feedback memory candidate. Promoted or merged decisions make
  the candidate eligible for a later next-context overlay, while rejected,
  expired, and blocked decisions keep reuse blocked. The decision itself still
  writes no long-term memory, writes no Company KB, does not execute a next
  pass, and does not claim human acceptance.
- `operator_feedback_candidate_reviewed_context_overlay`: no-provider audit
  artifact that shows whether an explicitly reviewed operator feedback
  candidate was included in or blocked from a derived context bundle. It writes
  no long-term memory, writes no Company KB, does not execute a next pass, and
  does not claim human acceptance.
- `operator_manifest_check`: read-only machine check for the operator-loop
  manifest's generated artifact refs, node states, controls, and no-provider
  write boundaries.
- `operator_handoff_packet`: no-provider handoff artifact for the next operator
  or agent. It requires an explicit manifest check before readiness and records
  blocked items plus the next operator action.
- `operator_run_package`: final no-provider run package for unattended
  handoff. It indexes the operator manifest, manifest check, handoff packet,
  handoff Markdown, and manifest output refs. It is an entry artifact for the
  next operator, not a new memory store, provider validation, or acceptance
  record.
- `operator_run_package_check`: read-only handoff consistency check for a
  selected run package. It verifies package item refs and no-provider/write
  boundaries at handoff time without following refs into workflow execution.
  The operator-loop writer can emit both the machine JSON and an operator-
  readable Markdown report.

All derived artifacts declare:

```json
{
  "provider_calls_started": false,
  "writes_long_term_memory": false
}
```

## Invariants

- Feedback is source evidence, not memory.
- A memory candidate is not promoted memory.
- A memory candidate enters next context only through an explicit promotion
  decision of `promoted` or `merged`.
- Rejected, pending, blocked, and expired refs are blocked from next context.
- Missing refs fail validation.
- No-provider mode does not require remote provider access.
- The context bundle always lists included refs and blocked refs separately.
- The next pass bundle is planned-only and must not execute a provider call.
- The next task packet consumes a handoff only; it does not execute a next pass.
- A next-pass result scaffold is only a local envelope. It is not generated
  content, not next-pass execution, and it does not auto-create feedback.
- The next pass review consumes explicit result records only; it does not
  execute the task and blocks any use of blocked or unknown context refs.
- Next-pass review feedback candidates are not promoted memory; they require
  explicit promotion decisions before reuse.
- A pending next-pass promotion template cannot be used as a reviewed decision.
- Promoted or merged next-pass feedback can enter a derived next context only
  after an explicit next-pass promotion decision.
- Rejected, expired, or blocked next-pass feedback remains visible in
  `blocked_refs` when requested for follow-up context.
- Operator feedback about a loop node remains evidence-only until a later
  explicit memory-candidate and promotion path is created.
- Operator feedback candidate packets are still candidate-only. Their pending
  promotion templates cannot enter next context as reviewed decisions.
- A rejected operator feedback decision can produce only a blocked candidate,
  never a reusable next-context ref.
- Operator feedback candidate reuse requires an explicit
  `operator_feedback_candidate_promotion_decision`; the pending template is
  never sufficient.
- Blocked operator feedback candidates cannot be promoted or merged. They can
  only receive a rejected, expired, or blocked decision.
- Promoted or merged operator feedback candidates can enter a derived context
  bundle only through the reviewed no-provider overlay command.
- Rejected, expired, or blocked operator feedback candidate decisions remain
  visible in `blocked_refs` when requested for follow-up context.
- Operator handoff readiness requires an explicit operator manifest check.
- Operator run packages cannot make a blocked handoff ready; they must preserve
  the manifest, check, and handoff blocker chain.
- Operator run packages are final run indexes only. They do not execute a
  provider call, write Company KB, write durable memory, promote candidates, or
  claim human acceptance.
- Operator run package checks cannot make a package ready by themselves; they
  can only confirm or block the package as a handoff entry artifact.

## CLI Surface

```powershell
python -m apps.cli.main production-memory-loop-validate examples/agentflow/production_memory_loop.example.json
python -m apps.cli.main production-memory-loop-run-no-provider examples/agentflow/production_memory_loop.example.json --output data/processed/runs/production_memory_loop/no_provider
python -m apps.cli.main production-memory-loop-draft-feedback examples/agentflow/production_memory_loop.example.json --target-ref artifact:approved_storyboard:v1 --decision accepted --summary "Carry the reviewed storyboard structure into the next pass." --created-at 2026-06-02T00:00:00+08:00 --output data/processed/runs/production_memory_loop/feedback_capture
python -m apps.cli.main production-memory-loop-review-promotion data/processed/runs/production_memory_loop/feedback_capture/production_memory_feedback_capture.json --decision promoted --rationale "Candidate is traceable to reviewed feedback." --decided-at 2026-06-02T00:05:00+08:00 --output data/processed/runs/production_memory_loop/promotion_decision
python -m apps.cli.main production-memory-loop-run-reviewed-feedback-no-provider examples/agentflow/production_memory_loop.example.json --feedback-capture data/processed/runs/production_memory_loop/feedback_capture/production_memory_feedback_capture.json --promotion-decision data/processed/runs/production_memory_loop/promotion_decision/promotion_decision.json --output data/processed/runs/production_memory_loop/reviewed_feedback
python -m apps.cli.main production-memory-loop-run-operator-no-provider examples/agentflow/production_memory_loop.example.json --generated-at 2026-06-02T01:00:00+08:00 --source-kb-status restructuring_or_unknown --output data/processed/runs/production_memory_loop/operator_loop
python -m apps.cli.main production-memory-loop-run-operator-no-provider examples/agentflow/production_memory_loop.example.json --generated-at 2026-06-02T12:00:00+08:00 --source-kb-status restructuring_or_unknown --draft-next-pass-result --output data/processed/runs/production_memory_loop/operator_loop_with_result_scaffold
python -m apps.cli.main production-memory-loop-run-operator-no-provider examples/agentflow/production_memory_loop.example.json --generated-at 2026-06-02T04:00:00+08:00 --source-kb-status restructuring_or_unknown --next-pass-result next_pass_result.json --output data/processed/runs/production_memory_loop/operator_loop_with_review
python -m apps.cli.main production-memory-loop-next-context-handoff data/processed/runs/production_memory_loop/no_provider/production_memory_loop_run.json --generated-at 2026-06-02T01:40:00+08:00 --output data/processed/runs/production_memory_loop/next_context_handoff
python -m apps.cli.main production-memory-loop-next-task-packet data/processed/runs/production_memory_loop/next_context_handoff/next_context_handoff.json --generated-at 2026-06-02T03:12:00+08:00 --output data/processed/runs/production_memory_loop/next_task_packet
python -m apps.cli.main production-memory-loop-draft-next-pass-result-no-provider data/processed/runs/production_memory_loop/next_task_packet/next_task_packet.json --generated-at 2026-06-02T11:00:00+08:00 --output-ref next-pass:artifact:operator-draft-001 --title "Second pass operator draft" --summary "Operator-supplied scaffold for the second pass." --output data/processed/runs/production_memory_loop/next_pass_result
python -m apps.cli.main production-memory-loop-review-next-pass data/processed/runs/production_memory_loop/next_task_packet/next_task_packet.json next_pass_result.json --reviewed-at 2026-06-02T03:30:00+08:00 --output data/processed/runs/production_memory_loop/next_pass_review
python -m apps.cli.main production-memory-loop-review-next-pass-promotion data/processed/runs/production_memory_loop/next_pass_review/next_pass_review.json --candidate-id memory-candidate-feedback-next-pass-001 --decision promoted --rationale "Traceable next-pass feedback selected by the operator." --decided-at 2026-06-02T05:10:00+08:00 --output data/processed/runs/production_memory_loop/next_pass_promotion_decision
python -m apps.cli.main production-memory-loop-run-next-pass-reviewed-feedback-no-provider examples/agentflow/production_memory_loop.example.json --next-pass-review data/processed/runs/production_memory_loop/next_pass_review/next_pass_review.json --promotion-decision data/processed/runs/production_memory_loop/next_pass_promotion_decision/next_pass_promotion_decision.json --output data/processed/runs/production_memory_loop/next_pass_reviewed_feedback
python -m apps.cli.main production-memory-loop-session-report data/processed/runs/production_memory_loop/reviewed_feedback/production_memory_loop_run.json --feedback-capture data/processed/runs/production_memory_loop/feedback_capture/production_memory_feedback_capture.json --promotion-decision data/processed/runs/production_memory_loop/promotion_decision/promotion_decision.json --generated-at 2026-06-02T00:10:00+08:00 --output data/processed/runs/production_memory_loop/session_report
python -m apps.cli.main production-memory-loop-company-kb-candidates data/processed/runs/production_memory_loop/session_report/production_memory_session_report.json --generated-at 2026-06-02T00:20:00+08:00 --source-kb-status restructuring_or_unknown --output data/processed/runs/production_memory_loop/company_kb_candidates
python -m apps.cli.main production-memory-loop-capture-operator-feedback data/processed/runs/production_memory_loop/operator_loop/production_memory_operator_loop_run.json --target-node company_kb_feedback_candidate_packet --decision accepted --summary "Operator reviewed the candidate packet shape for the next loop." --reviewed-at 2026-06-02T07:10:00+08:00 --output data/processed/runs/production_memory_loop/operator_feedback
python -m apps.cli.main production-memory-loop-draft-operator-feedback-candidate data/processed/runs/production_memory_loop/operator_feedback/operator_feedback_event.json --generated-at 2026-06-02T08:20:00+08:00 --output data/processed/runs/production_memory_loop/operator_feedback_candidate
python -m apps.cli.main production-memory-loop-review-operator-feedback-candidate data/processed/runs/production_memory_loop/operator_feedback_candidate/operator_feedback_candidate_packet.json --decision promoted --rationale "Traceable operator feedback selected for the next context overlay." --decided-at 2026-06-02T08:30:00+08:00 --output data/processed/runs/production_memory_loop/operator_feedback_candidate_promotion
python -m apps.cli.main production-memory-loop-run-operator-feedback-candidate-reviewed-no-provider examples/agentflow/production_memory_loop.example.json --candidate-packet data/processed/runs/production_memory_loop/operator_feedback_candidate/operator_feedback_candidate_packet.json --promotion-decision data/processed/runs/production_memory_loop/operator_feedback_candidate_promotion/operator_feedback_candidate_promotion_decision.json --output data/processed/runs/production_memory_loop/operator_feedback_candidate_reviewed
python -m apps.cli.main production-memory-loop-run-operator-no-provider examples/agentflow/production_memory_loop.example.json --generated-at 2026-06-02T18:10:00+08:00 --source-kb-status restructuring_or_unknown --draft-next-pass-result --write-run-package --write-run-package-check --output data/processed/runs/production_memory_loop/operator_run_package_smoke
python -m apps.cli.main production-memory-loop-check-operator-run-package data/processed/runs/production_memory_loop/operator_run_package_smoke/operator_run_package/operator_run_package.json --output data/processed/runs/production_memory_loop/operator_run_package_smoke/operator_run_package_check/operator_run_package_check.json
```

These commands validate the loop, run no-provider context assembly, and draft
operator feedback capture artifacts locally. The reviewed feedback commands
turn a draft capture into an explicit promotion decision, then derive a
no-provider loop overlay for the next context bundle. The run command writes:

- `production_memory_loop_run.json`
- `context_bundle.json`
- `pass_readiness.json`
- `next_pass_bundle.json`

The feedback draft command writes:

- `production_memory_feedback_capture.json`
- `feedback_event.json`
- `memory_candidate.json`
- `promotion_decision_template.json`

The promotion decision template stays `pending`; it is not promoted memory.

The reviewed promotion command writes:

- `promotion_decision.json`

The reviewed feedback run command writes:

- `derived_production_memory_loop.json`
- `production_memory_loop_run.json`
- `context_bundle.json`
- `pass_readiness.json`
- `next_pass_bundle.json`

The session report command writes:

- `production_memory_session_report.json`
- `production_memory_session_report.md`

The next context handoff command writes:

- `next_context_handoff.json`
- `next_context_handoff.md`

The next task packet command writes:

- `next_task_packet.json`
- `next_task_packet.md`

The next-pass result scaffold command writes:

- `next_pass_result.json`
- `next_pass_result.md`

The scaffold reads a ready `next_task_packet.json`, includes only
`allowed_context_refs` by default, and rejects blocked or unknown refs if the
operator supplies an explicit `--used-context-ref` subset. It keeps
`feedback_events` empty until feedback is explicitly captured after review.

The next pass review command reads a selected `next_task_packet.json` and an
explicit operator-supplied next-pass result JSON. It writes:

- `next_pass_review.json`
- `next_pass_review.md`

The next-pass result input must be a local JSON record with
`kind: agentflow_production_memory_next_pass_result`. It lists output artifacts
and their `used_context_refs`. The review blocks blocked/unknown context refs,
keeps feedback candidates candidate-only, and emits only pending promotion
templates.

The next-pass promotion decision command writes:

- `next_pass_promotion_decision.json`

The next-pass reviewed feedback run command writes:

- `derived_production_memory_loop.json`
- `production_memory_loop_run.json`
- `context_bundle.json`
- `pass_readiness.json`
- `next_pass_bundle.json`
- `next_pass_promotion_overlay.json`

The next-pass promotion decision must be explicit. A pending template from
`next_pass_review.json` is rejected by the overlay command. Promoted or merged
decisions allow the derived candidate to enter the next context bundle; rejected,
expired, or blocked decisions keep it visible as a blocked ref.

The Company KB feedback candidate command writes:

- `company_kb_feedback_candidate_packet.json`
- `company_kb_feedback_candidate_packet.md`

The operator feedback capture command writes:

- `operator_feedback_event.json`
- `operator_feedback_event.md`

The operator feedback candidate command writes:

- `operator_feedback_candidate_packet.json`
- `memory_candidate.json`
- `promotion_decision_template.json`
- `operator_feedback_candidate_packet.md`

The operator feedback candidate promotion command writes:

- `operator_feedback_candidate_promotion_decision.json`
- `operator_feedback_candidate_promotion_decision.md`

The operator feedback candidate reviewed run command writes:

- `derived_production_memory_loop.json`
- `production_memory_loop_run.json`
- `context_bundle.json`
- `pass_readiness.json`
- `next_pass_bundle.json`
- `operator_feedback_candidate_promotion_overlay.json`

The operator-loop command writes the existing no-provider run, session report,
next context handoff, next task packet, Company KB candidate packet, and:

- `production_memory_operator_loop_run.json`

If `--draft-next-pass-result` is supplied, the operator-loop command also
creates a local next-pass result scaffold from the generated next-task packet
and writes:

- `next_pass_result/next_pass_result.json`
- `next_pass_result/next_pass_result.md`

This option prepares an operator-completion envelope only. It does not execute
the next pass, call a provider, generate content, create feedback, review the
result, or promote memory.

If `--next-pass-result` is supplied, the operator-loop command also reviews
that explicit result JSON against the generated next-task packet and writes:

- `next_pass_review/next_pass_review.json`
- `next_pass_review/next_pass_review.md`

The option is local-only and does not execute the next pass.

The source loop and draft feedback capture are not mutated. A promoted or
merged reviewed decision may include the new candidate in the next context; a
rejected, blocked, or expired decision keeps it in `blocked_refs`.

The session report is an audit surface for the operator. It does not approve
content, promote company memory, or validate provider output.

The next context handoff is a task handoff for a future AI pass. It does not
execute that pass, follow refs, call a provider, claim human acceptance, or
convert candidates into durable memory.

The next task packet is the handoff-consumption surface for a future AI task.
It does not run that task, call a provider, write memory, write Company KB, or
turn candidates into promoted memory.

The next pass review is the intake surface after a future AI task has produced
explicit result records. It does not run the task, call a provider, write memory,
write Company KB, claim acceptance, or promote any candidate.

The next-pass promotion overlay is the explicit-decision surface after result
intake. It converts reviewed next-pass feedback into normal source records for a
derived no-provider loop, but it still does not write durable memory, write
Company KB, call providers, or claim acceptance.

The operator feedback event is the explicit feedback surface after an operator
inspects a manifest node. Even when its decision is `accepted`, it records only
`status: evidence_only` with `feedback_is_memory: false`,
`creates_memory_candidate: false`, `creates_promotion_decision: false`, and
`human_acceptance: not_claimed`.

The operator feedback candidate packet is the explicit bridge from feedback
evidence to a candidate-only memory review packet. It may draft a candidate for
later operator review, but it keeps `candidate_is_promoted_memory: false` and
emits only a `pending` promotion decision template.

The operator feedback candidate promotion decision is the explicit review
surface for that candidate packet. It records the source packet, source
feedback event, source pending template, candidate id, decision, rationale,
reviewer role, and whether future candidate reuse is allowed. It does not write
durable memory, write Company KB, execute a next pass, or claim human
acceptance. A promoted or merged decision is only eligibility for a later
next-context overlay, not a Company memory promotion.

The operator feedback candidate reviewed run is the explicit-decision overlay
surface after operator feedback candidate review. It converts the reviewed
candidate packet into normal source records for a derived no-provider loop:
operator-node evidence, reviewed feedback event, memory candidate, explicit
promotion decision, and a requested candidate ref. Promoted or merged decisions
can include the candidate in the next context bundle; rejected, expired, or
blocked decisions keep it visible as a blocked ref. The command still does not
write durable memory, write Company KB, call providers, execute a next pass, or
claim acceptance.

When `--write-run-package-check` is supplied together with
`--write-run-package`, the operator-loop command also writes:

- `operator_run_package_check/operator_run_package_check.json`
- `operator_run_package_check/operator_run_package_check.md`

This is a post-package handoff check. It is not added to the operator manifest
or the run package itself, which avoids self-referential check chains. It
confirms or blocks the final package as a next-operator entry artifact only; it
does not call providers, execute workflows, write durable memory, write Company
KB, or claim human acceptance. The Markdown report is a readable presentation
of the same check result and boundaries; it is not a separate approval record.

The Company KB feedback candidate packet is a source-to-candidate bridge for
the local Company knowledge-base workflow. It records reusable lessons as
candidate items with `requires_human_review: true`,
`writes_company_kb: false`, and `promotion_status: candidate_only`, so it can
survive source-KB restructuring without silently becoming company memory.

The default output path is ignored runtime space. Generated run artifacts should
not be committed.

## Web Scope

The Web slice is a read-only generic production-memory canvas / ledger view. It
reads only explicitly selected JSON artifacts in browser memory.

The Web workbench recognizes both:

- `agentflow_production_memory_loop`
- `agentflow_production_memory_session_report`
- `agentflow_company_kb_feedback_candidate_packet`
- `agentflow_production_memory_operator_loop_run`
- `agentflow_production_memory_operator_manifest_check`
- `agentflow_production_memory_operator_handoff_packet`
- `agentflow_production_memory_operator_run_package`
- `agentflow_production_memory_operator_run_package_check`
- `agentflow_production_memory_next_context_handoff`
- `agentflow_production_memory_next_task_packet`
- `agentflow_production_memory_next_pass_result`
- `agentflow_production_memory_next_pass_review`
- `agentflow_production_memory_next_pass_promotion_decision`
- `agentflow_production_memory_next_pass_promotion_overlay`
- `agentflow_production_memory_operator_feedback_event`
- `agentflow_production_memory_operator_feedback_candidate_packet`

Session reports render as an operator audit canvas with included refs, blocked
refs, next operator action, and non-claim boundaries.

Company KB feedback candidate packets render as a read-only candidate review
canvas with candidate items, explicit non-promotions, source KB restructuring
status, human-review requirements, and write-disabled boundaries. They remain
candidate-only transport artifacts and do not write Company KB or durable
memory.

Operator-loop manifests render as a read-only chain canvas with operator nodes,
generated artifact refs, Company KB feedback candidate boundaries, provider
controls, and non-claim boundaries. They are review manifests only; they do not
follow artifact refs, execute workflows, or promote memory.

Operator manifest check artifacts render as a read-only machine-check canvas
with checked refs, missing refs, failed nodes, failed controls, no-provider
controls, and non-claim boundaries. They do not follow refs, execute workflows,
call providers, write Company KB, or promote durable memory.

Operator handoff packet artifacts render as a read-only handoff canvas with
artifact refs, blocked items, manifest-check status, the recorded next operator
action, no-provider controls, and non-claim boundaries. They do not follow refs,
execute workflows, call providers, write Company KB, or promote durable memory.

Operator run package artifacts render as a read-only final-run canvas with the
manifest status, manifest-check status, handoff status, package items, blocked
items, no-provider controls, and non-claim boundaries. They are entry artifacts
for the next operator only; they do not follow refs, execute workflows, call
providers, write Company KB, claim provider success, or promote durable memory.

Operator run package check artifacts render as a read-only handoff check canvas
with the package check status, checked package items, missing or blocked refs,
failed controls, no-provider controls, and non-claim boundaries. They confirm
or block the package as a next-operator entry artifact only; they do not follow
refs from the browser, execute workflows, call providers, write Company KB,
claim provider success, or promote durable memory.

When an operator-loop manifest includes `next_pass_promotion`, the Web canvas
also surfaces a Next pass promotion card, lane, controls, inspector facts, and
next-pass action. This is a read-only view of the explicit decision and derived
overlay effect, not a promotion action or workflow execution.

When an operator-loop manifest includes `operator_feedback_candidate_promotion`,
the Web canvas surfaces an Operator feedback candidate promotion card, lane,
controls, inspector facts, and next-pass action. This is also only a read-only
view of the explicit decision and reviewed context overlay effect. It does not
promote durable memory, write Company KB, follow refs, call providers, or
execute the next pass.

Next-context handoff artifacts render as a read-only task handoff canvas with
included refs, blocked refs, no-provider controls, and non-claim boundaries for
the next AI pass. They do not execute that pass, follow refs, call providers,
write Company KB, or promote durable memory.

Next-task packet artifacts render as a read-only task entry canvas with allowed
context refs, blocked refs, no-provider controls, and non-claim boundaries. They
do not execute the next task, follow refs, call providers, write Company KB, or
promote durable memory.

Next-pass result scaffold artifacts render as a read-only result envelope canvas
with output artifacts, used context refs, empty or explicit feedback events,
no-provider controls, and non-claim boundaries. They do not execute a next pass,
follow refs, call providers, write Company KB, create feedback, or promote
durable memory.

Next-pass review artifacts render as a read-only result-intake canvas with used
allowed refs, blocked or unknown refs, candidate-only feedback, pending
promotion templates, no-provider controls, and non-claim boundaries. They do
not execute a next pass, follow refs, call providers, write Company KB, or
promote durable memory.

Next-pass promotion decision and overlay artifacts render as a read-only
decision-effect canvas with the explicit decision, candidate id, follow-up
context effect, no-provider controls, and non-claim boundaries. They do not
execute a next pass, follow refs, call providers, write Company KB, or write
durable memory.

Operator feedback event artifacts render as a read-only feedback evidence
canvas with the target manifest node, operator decision, evidence-only status,
memory-boundary controls, and non-claim boundaries. They do not create memory
candidates, create promotion decisions, claim human acceptance, execute
workflows, write Company KB, or write durable memory.

Operator feedback candidate packet artifacts render as a read-only candidate
review canvas with the source feedback event, memory candidate, pending
promotion template, no-provider controls, and non-claim boundaries. They do not
promote memory, execute workflow actions, follow refs, write Company KB, or
write durable memory.

It does not:

- scan directories;
- persist browser state;
- execute workflows;
- call providers;
- add a project-specific inspector.

## Non-Claims

This slice is structure and runtime verification only. It is not:

- human acceptance;
- business validation;
- durable Memory OS;
- provider success;
- automatic Company knowledge-base promotion.

## Operator Loop Promotion Overlay Integration

`production-memory-loop-run-operator-no-provider` can now optionally include the
explicit next-pass promotion decision layer in the same local operator run.
This is still a no-provider orchestration path. It does not execute the next
pass, call providers, write durable memory, write Company KB, or claim human
acceptance.

Additional command shape:

```powershell
python -m apps.cli.main production-memory-loop-run-operator-no-provider examples/agentflow/production_memory_loop.example.json --generated-at 2026-06-02T06:00:00+08:00 --source-kb-status restructuring_or_unknown --next-pass-result next_pass_result.json --next-pass-promotion-decision data/processed/runs/production_memory_loop/next_pass_promotion_decision/next_pass_promotion_decision.json --output data/processed/runs/production_memory_loop/operator_loop_with_promotion
```

The promotion decision option is valid only together with `--next-pass-result`,
because the decision must be validated against the generated
`next_pass_review`. When supplied, the operator-loop output includes:

- `next_pass_promotion_decision/next_pass_promotion_decision.json`
- `next_pass_reviewed_feedback/derived_production_memory_loop.json`
- `next_pass_reviewed_feedback/production_memory_loop_run.json`
- `next_pass_reviewed_feedback/context_bundle.json`
- `next_pass_reviewed_feedback/pass_readiness.json`
- `next_pass_reviewed_feedback/next_pass_bundle.json`
- `next_pass_reviewed_feedback/next_pass_promotion_overlay.json`

The operator manifest includes separate `next_pass_promotion_decision` and
`next_pass_promotion_overlay` nodes so an operator can audit the explicit
promotion decision separately from the derived follow-up context.

## Operator Loop Feedback Candidate Overlay Integration

`production-memory-loop-run-operator-no-provider` can also optionally include
an explicit operator feedback candidate packet and promotion decision in the
same local operator run. This connects the operator feedback loop back into the
generic production-memory operator manifest without creating durable memory or
writing Company KB.

Additional command shape:

```powershell
python -m apps.cli.main production-memory-loop-run-operator-no-provider examples/agentflow/production_memory_loop.example.json --generated-at 2026-06-02T10:40:00+08:00 --source-kb-status restructuring_or_unknown --operator-feedback-candidate-packet data/processed/runs/production_memory_loop/operator_feedback_candidate/operator_feedback_candidate_packet.json --operator-feedback-candidate-promotion-decision data/processed/runs/production_memory_loop/operator_feedback_candidate_promotion/operator_feedback_candidate_promotion_decision.json --output data/processed/runs/production_memory_loop/operator_loop_with_feedback_candidate_overlay
```

The operator feedback candidate packet and promotion decision must be supplied
together. A pending promotion template cannot drive this overlay. When supplied,
the operator-loop output includes:

- `operator_feedback_candidate_promotion_decision/operator_feedback_candidate_promotion_decision.json`
- `operator_feedback_candidate_promotion_decision/operator_feedback_candidate_promotion_decision.md`
- `operator_feedback_candidate_reviewed_feedback/derived_production_memory_loop.json`
- `operator_feedback_candidate_reviewed_feedback/production_memory_loop_run.json`
- `operator_feedback_candidate_reviewed_feedback/context_bundle.json`
- `operator_feedback_candidate_reviewed_feedback/pass_readiness.json`
- `operator_feedback_candidate_reviewed_feedback/next_pass_bundle.json`
- `operator_feedback_candidate_reviewed_feedback/operator_feedback_candidate_promotion_overlay.json`

The operator manifest includes separate
`operator_feedback_candidate_promotion_decision` and
`operator_feedback_candidate_promotion_overlay` nodes. The overlay can show that
a promoted or merged candidate entered the derived context bundle, or that a
rejected, expired, or blocked candidate stayed blocked. This remains a
no-provider, read-only evidence orchestration path: no next pass is executed,
no providers are called, no durable memory is written, no Company KB is written,
and no human acceptance or business validation is claimed.
