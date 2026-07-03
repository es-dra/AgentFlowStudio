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

## Non-Goals

- No thread archive automation.
- No destructive migration or full historical replay.
- No Runtime Service, Studio, provider, OpenAPI, deploy, or server mutation.
- No provider smoke, generated-media QA, human acceptance, business validation,
  Company OS projection, durable-memory promotion, or COS active-rule claim.
