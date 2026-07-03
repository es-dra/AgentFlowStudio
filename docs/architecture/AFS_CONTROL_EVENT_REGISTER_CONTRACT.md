# AFS Control Event Register Contract

This contract is a repo-local adapter for active and pending-control lane
tracking. It uses append-only JSONL events and reconstructs a deterministic
control register for evaluator review.

## Scope

- Artifact types: `agentflow_control_event`, `agentflow_control_register`.
- Input format: append-only JSONL, one `agentflow_control_event` object per
  line.
- Output format: materialized `agentflow_control_register` with active and
  pending-control lanes.
- Current migration posture: active/pending-control first batch only, no full
  historical replay.
- Worker-final ingest posture: bounded repo-local spec/test slice only. It
  records final-delivery evidence as control events and does not implement an
  archive daemon, source sync, or runtime worker. The current redispatch route
  basis is `readback_accepted_reaffirm_parallel_architecture_redispatch`.

## Required Invariants

- Implementation lanes need at least one non-empty durable implementation
  artifact handle.
- Claim-state changes are first-class `claim_state_changed` events.
- Non-claims are separate `non_claim_recorded` events and remain explicit
  `false` boundaries.
- Archive policy is evaluated before archive execution.
- Archive execution is blocked until ACK delivery is confirmed when
  `archive_after_ack_delivery_confirmed=true`.
- Role surfaces are fixed for dispatcher, CTO disposition, implementation
  worker, and evaluator surfaces as applicable.
- Evidence sources must declare a safe source classification.
- No-ACK state is preserved in the register and blocks archive execution.
- Worker-final ingest uses `worker_final_ingested` events with canonical
  `event_id`, `top_down_dispatch_id`, and `bottom_up_feedback_id` fields.
- Worker-final recovery sources are bounded to
  `direct_thread_delivery`, `local_final_only`, `legacy_bridge`,
  `pendingWorktreeId`, and `worker_final_read`.
- Worker-final duplicate handling is idempotent for exact repeated
  TD/BU/event-id records and rejects conflicting duplicate TD/BU finals.
- Worker-final materialization fails closed when the final event is missing its
  `payload.worker_final_ingest` contract object.

## Worker-Final Ingest Contract

`worker_final_ingested` events carry `payload.worker_final_ingest`:

- `ingest_contract`: `repo_local_control_event_worker_final_ingest_v0.1`
- `canonical_event_id`, `top_down_dispatch_id`, `bottom_up_feedback_id`
- `source_thread_id`, `close_state`, `safe_summary`
- `recovery_sources[]` with `source_type`, `source_ref`, `safe_summary`
- `idempotency.dedupe_strategy`: `td_bu_event_ids`
- `ack` fields preserving `ack_state=no_ack` until delivery is confirmed
- `archive_policy` with `archive_after_ack_delivery_confirmed=true`
- close states are bounded to
  `control_event_bus_worker_final_ingest_redispatch_completed` and
  `control_event_bus_worker_final_ingest_redispatch_blocked_exact_reason`

Archive execution remains blocked while `ack_delivery_confirmed=false`.
Worker-final ingest records ordering requirements but does not archive threads.

## Non-Goals

- No thread archive automation.
- No destructive migration or full historical replay.
- No Runtime Service, Studio, provider, OpenAPI, deploy, or server mutation.
- No source sync or worker-runtime implementation.
- No provider smoke, generated-media QA, human acceptance, business validation,
  Company OS projection, durable-memory promotion, or COS active-rule claim.
