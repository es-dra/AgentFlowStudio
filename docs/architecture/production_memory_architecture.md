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
  -> session_report
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
- `session_report`: read-only operator audit artifact that summarizes the run,
  included refs, blocked refs, optional feedback capture, optional promotion
  decision, next operator action, and non-claim boundaries.

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

## CLI Surface

```powershell
python -m apps.cli.main production-memory-loop-validate examples/agentflow/production_memory_loop.example.json
python -m apps.cli.main production-memory-loop-run-no-provider examples/agentflow/production_memory_loop.example.json --output data/processed/runs/production_memory_loop/no_provider
python -m apps.cli.main production-memory-loop-draft-feedback examples/agentflow/production_memory_loop.example.json --target-ref artifact:approved_storyboard:v1 --decision accepted --summary "Carry the reviewed storyboard structure into the next pass." --created-at 2026-06-02T00:00:00+08:00 --output data/processed/runs/production_memory_loop/feedback_capture
python -m apps.cli.main production-memory-loop-review-promotion data/processed/runs/production_memory_loop/feedback_capture/production_memory_feedback_capture.json --decision promoted --rationale "Candidate is traceable to reviewed feedback." --decided-at 2026-06-02T00:05:00+08:00 --output data/processed/runs/production_memory_loop/promotion_decision
python -m apps.cli.main production-memory-loop-run-reviewed-feedback-no-provider examples/agentflow/production_memory_loop.example.json --feedback-capture data/processed/runs/production_memory_loop/feedback_capture/production_memory_feedback_capture.json --promotion-decision data/processed/runs/production_memory_loop/promotion_decision/promotion_decision.json --output data/processed/runs/production_memory_loop/reviewed_feedback
python -m apps.cli.main production-memory-loop-session-report data/processed/runs/production_memory_loop/reviewed_feedback/production_memory_loop_run.json --feedback-capture data/processed/runs/production_memory_loop/feedback_capture/production_memory_feedback_capture.json --promotion-decision data/processed/runs/production_memory_loop/promotion_decision/promotion_decision.json --generated-at 2026-06-02T00:10:00+08:00 --output data/processed/runs/production_memory_loop/session_report
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

The source loop and draft feedback capture are not mutated. A promoted or
merged reviewed decision may include the new candidate in the next context; a
rejected, blocked, or expired decision keeps it in `blocked_refs`.

The session report is an audit surface for the operator. It does not approve
content, promote company memory, or validate provider output.

The default output path is ignored runtime space. Generated run artifacts should
not be committed.

## Web Scope

The Web slice is a read-only generic production-memory canvas / ledger view. It
reads only explicitly selected JSON artifacts in browser memory.

The Web workbench recognizes both:

- `agentflow_production_memory_loop`
- `agentflow_production_memory_session_report`

Session reports render as an operator audit canvas with included refs, blocked
refs, next operator action, and non-claim boundaries.

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
