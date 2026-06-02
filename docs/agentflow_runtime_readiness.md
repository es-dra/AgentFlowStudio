# AgentFlow Runtime Readiness

Phase 15.10 is a readiness spike for future AgentFlow runtime work.

It defines the gates that must be satisfied before starting Router, skill, or
Memory runtime implementation.

- It does not implement Router runtime.
- It does not implement skill runtime.
- It does not implement Memory runtime.
- It does not execute workflows.

## Purpose

AgentFlow Studio should not move from contract-layer work into runtime work just
because the contracts exist. Runtime work should start only when the contracts
are stable enough for execution to produce reusable, reviewable, and reversible
artifacts.

The readiness decision should answer:

- Which runtime surface is being proposed?
- Which artifacts will it read and write?
- Which review gates will reject unsafe or invalid output?
- Which human decision remains required?
- Which memory or feedback signal may be created, and which may not?
- How will cost, quality, and failure be traced?

## Runtime Surfaces

Future runtime work must be split into separate phases:

- Router runtime: chooses a skill or workflow plan, but must not silently
  execute side effects.
- skill runtime: invokes one skill under explicit input, output, and quality
  boundaries.
- Memory runtime: promotes, merges, rejects, expires, or retrieves durable
  memory only after explicit promotion logic exists.

Do not combine these surfaces in the first runtime PR.

## Required Gates

### contract gate

- The input and output artifact types are documented.
- Every committed example uses `schema_version: 0.1.0` or an intentional newer
  version.
- The artifact is indexed or intentionally excluded from the contract registry.
- The PR review checklist has been applied.

### artifact gate

- Runtime output must be written as structured artifacts, not only logs or UI
  state.
- Each artifact must have stable IDs or references to its source artifacts.
- Generated artifacts must be inspectable without a live service.
- Markdown reports are human review surfaces, not strong contract sources.

### review gate

- The runtime surface has an inspect or review path before merge.
- Failure states are represented as artifacts or explicit status values.
- Rejected candidates keep rejection reasons.
- Human approval points are recorded as decisions, not implicit chat context.

### feedback and memory gate

- `feedback.jsonl` remains the source of truth for raw feedback events.
- `feedback_signal_log` is a derived interpretation, not a feedback entry point.
- candidate memory remains candidate memory until a promotion decision exists.
- Promotion decisions must distinguish promoted, rejected, merged, and expired
  outcomes before durable memory is written.

### cost-quality gate

- `cost_quality_trace` records provider, execution mode, inputs, outputs, and
  quality proxy signals.
- Zero-cost local deterministic execution must stay distinguishable from remote
  provider execution.
- Runtime work must not claim model quality maturity from contract tests alone.

### operations gate

- The runtime can be run locally without secrets unless the PR explicitly
  documents a guarded provider path.
- Remote provider calls stay behind explicit environment gates.
- No private paths, generated media, tokens, cookies, or signed URLs are
  committed.
- Rollback means deleting or ignoring artifacts, not mutating hidden state.

## Do Not Start Runtime Work If

Do not start runtime work if:

- `schema_version` handling is ambiguous.
- A router decision is treated as execution.
- candidate memory is treated as durable memory.
- `feedback_signal_log` is treated as the feedback source of truth.
- `cost_quality_trace` is treated as a quality guarantee.
- The proposed change needs a database before file-based artifacts are stable.
- The PR cannot state which human decision remains in the loop.

## First Eligible Runtime Slice

The first eligible runtime slice should be a small local execution path that
reads existing contracts, writes explicit artifacts, and can be inspected by
existing or narrowly extended review tooling.

Preferred first candidates:

- Router dry-run decision validation
- skill invocation/result replay from committed examples
- memory promotion decision validator

Phase 15.11 starts with Router dry-run decision validation. This is still not
Router runtime because it reads an existing decision artifact and validates its
contract boundaries without selecting, executing, or mutating anything.

Phase 15.12 continues with skill invocation/result replay validation. This is
still not skill runtime because it compares existing plan/result artifacts
without invoking a skill, executing a workflow, or writing runtime state.

Not preferred as the first slice:

- hosted API
- database-backed memory
- remote provider orchestration
- Web UI-driven runtime
- multi-module execution across AgentFlow Production and AgentFlow Studio
