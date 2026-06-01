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
  -> explicit next_pass_result input
  -> next_pass_review
  -> session_report
  -> company_kb_feedback_candidate_packet
  -> operator_loop_run_manifest
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
- `next_pass_review`: no-provider review artifact for an explicitly supplied
  next-pass result. It checks that result outputs used only
  `allowed_context_refs`, records blocked or unknown refs, and derives
  candidate-only feedback plus pending promotion-decision templates.
- `session_report`: read-only operator audit artifact that summarizes the run,
  included refs, blocked refs, optional feedback capture, optional promotion
  decision, next operator action, and non-claim boundaries.
- `company_kb_feedback_candidate_packet`: candidate-only project-to-Company
  feedback packet generated from a session report. It is not a Company KB
  write, not durable memory, and not a promotion decision.
- `operator_loop_run_manifest`: an auditable no-provider orchestration manifest
  that records all operator-loop nodes, generated artifact refs, controls, and
  non-claim boundaries for one local run.

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
- The next pass review consumes explicit result records only; it does not
  execute the task and blocks any use of blocked or unknown context refs.
- Next-pass review feedback candidates are not promoted memory; they require
  explicit promotion decisions before reuse.

## CLI Surface

```powershell
python -m apps.cli.main production-memory-loop-validate examples/agentflow/production_memory_loop.example.json
python -m apps.cli.main production-memory-loop-run-no-provider examples/agentflow/production_memory_loop.example.json --output data/processed/runs/production_memory_loop/no_provider
python -m apps.cli.main production-memory-loop-draft-feedback examples/agentflow/production_memory_loop.example.json --target-ref artifact:approved_storyboard:v1 --decision accepted --summary "Carry the reviewed storyboard structure into the next pass." --created-at 2026-06-02T00:00:00+08:00 --output data/processed/runs/production_memory_loop/feedback_capture
python -m apps.cli.main production-memory-loop-review-promotion data/processed/runs/production_memory_loop/feedback_capture/production_memory_feedback_capture.json --decision promoted --rationale "Candidate is traceable to reviewed feedback." --decided-at 2026-06-02T00:05:00+08:00 --output data/processed/runs/production_memory_loop/promotion_decision
python -m apps.cli.main production-memory-loop-run-reviewed-feedback-no-provider examples/agentflow/production_memory_loop.example.json --feedback-capture data/processed/runs/production_memory_loop/feedback_capture/production_memory_feedback_capture.json --promotion-decision data/processed/runs/production_memory_loop/promotion_decision/promotion_decision.json --output data/processed/runs/production_memory_loop/reviewed_feedback
python -m apps.cli.main production-memory-loop-run-operator-no-provider examples/agentflow/production_memory_loop.example.json --generated-at 2026-06-02T01:00:00+08:00 --source-kb-status restructuring_or_unknown --output data/processed/runs/production_memory_loop/operator_loop
python -m apps.cli.main production-memory-loop-next-context-handoff data/processed/runs/production_memory_loop/no_provider/production_memory_loop_run.json --generated-at 2026-06-02T01:40:00+08:00 --output data/processed/runs/production_memory_loop/next_context_handoff
python -m apps.cli.main production-memory-loop-next-task-packet data/processed/runs/production_memory_loop/next_context_handoff/next_context_handoff.json --generated-at 2026-06-02T03:12:00+08:00 --output data/processed/runs/production_memory_loop/next_task_packet
python -m apps.cli.main production-memory-loop-review-next-pass data/processed/runs/production_memory_loop/next_task_packet/next_task_packet.json next_pass_result.json --reviewed-at 2026-06-02T03:30:00+08:00 --output data/processed/runs/production_memory_loop/next_pass_review
python -m apps.cli.main production-memory-loop-session-report data/processed/runs/production_memory_loop/reviewed_feedback/production_memory_loop_run.json --feedback-capture data/processed/runs/production_memory_loop/feedback_capture/production_memory_feedback_capture.json --promotion-decision data/processed/runs/production_memory_loop/promotion_decision/promotion_decision.json --generated-at 2026-06-02T00:10:00+08:00 --output data/processed/runs/production_memory_loop/session_report
python -m apps.cli.main production-memory-loop-company-kb-candidates data/processed/runs/production_memory_loop/session_report/production_memory_session_report.json --generated-at 2026-06-02T00:20:00+08:00 --source-kb-status restructuring_or_unknown --output data/processed/runs/production_memory_loop/company_kb_candidates
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

The next pass review command reads a selected `next_task_packet.json` and an
explicit operator-supplied next-pass result JSON. It writes:

- `next_pass_review.json`
- `next_pass_review.md`

The next-pass result input must be a local JSON record with
`kind: agentflow_production_memory_next_pass_result`. It lists output artifacts
and their `used_context_refs`. The review blocks blocked/unknown context refs,
keeps feedback candidates candidate-only, and emits only pending promotion
templates.

The Company KB feedback candidate command writes:

- `company_kb_feedback_candidate_packet.json`
- `company_kb_feedback_candidate_packet.md`

The operator-loop command writes the existing no-provider run, session report,
next context handoff, next task packet, Company KB candidate packet, and:

- `production_memory_operator_loop_run.json`

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
- `agentflow_production_memory_next_context_handoff`
- `agentflow_production_memory_next_task_packet`

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

Next-context handoff artifacts render as a read-only task handoff canvas with
included refs, blocked refs, no-provider controls, and non-claim boundaries for
the next AI pass. They do not execute that pass, follow refs, call providers,
write Company KB, or promote durable memory.

Next-task packet artifacts render as a read-only task entry canvas with allowed
context refs, blocked refs, no-provider controls, and non-claim boundaries. They
do not execute the next task, follow refs, call providers, write Company KB, or
promote durable memory.

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
