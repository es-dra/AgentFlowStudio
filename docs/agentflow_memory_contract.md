# AgentFlow Memory Contract

AgentFlow Memory is the future platform layer that turns repeated execution and
feedback into reusable project knowledge.

Phase 15.4 deepens the signal contracts. It still does not implement a memory
runtime, vector store, database, or automatic preference update.

## Contract Chain

The intended chain is:

```text
raw feedback event
-> derived feedback signal
-> memory candidate
-> promotion decision
-> accepted / rejected / merged / expired memory
-> preference profile
-> context bundle
-> next-round prompt
```

Each step must keep evidence references so future agents can explain why a
preference or rule exists.

Phase 15.13 adds intermediate asset language on top of this chain:

```text
memory candidate
-> promotion decision
-> reusable asset profile
-> asset reuse decision
```

A candidate memory is not a reusable asset. A reusable asset profile must point
back to source intermediate assets and an explicit promotion decision.

## Raw Feedback Event

Raw feedback events are append-only records from a user, agent reviewer, or
external system.

`feedback.jsonl` remains the source of truth for raw feedback. A derived log
must not replace it.

Minimum fields:

- `schema_version`: currently `0.1.0` for AgentFlow examples.
- `feedback_id`: stable event id.
- `source`: human, agent, or external system.
- `target_type`: artifact, clip, candidate, package, run, handoff, or prompt.
- `target_id`: target identifier.
- `decision`: accepted, rejected, needs_revision, note, or published.
- `reason_tags`: machine-readable reason tags.
- `user_note`: optional human note.
- `created_at`: ISO timestamp.

See [`../examples/agentflow/feedback_event.example.jsonl`](../examples/agentflow/feedback_event.example.jsonl).

## Derived Feedback Signal

`feedback_signal_log.json` is a derived artifact for the current run.

It may summarize:

- relevant feedback event ids
- interpreted preference signals
- affected artifacts
- confidence level
- suggested follow-up

It must not be used as the primary feedback store. `feedback.jsonl` remains the
source of truth even when a derived signal is easier for an Agent to read.

Role boundary:

- Raw feedback is source evidence.
- Derived feedback signal is an interpretation for one run.
- A derived signal must point back to raw feedback and must not replace it.

## Memory Candidate

`memory_candidates.json` is a candidate store.

A memory candidate may include:

- `candidate_id`
- `promotion_status`
- `memory_type`
- `statement`
- `evidence_refs`
- `confidence`
- `suggested_promotion_condition`

For the current MVP, `promotion_status` must remain `candidate`.

Candidate memory is not accepted memory. Agents may use candidates as review
inputs, but must not treat them as durable preferences or project facts without
an explicit promotion decision.

See [`../examples/agentflow/memory_candidate.example.json`](../examples/agentflow/memory_candidate.example.json).

## Promotion Decision

A promotion decision is explicit and reviewable. Current decision statuses:

- `promoted`
- `rejected`
- `merged`
- `expired`

Every promotion decision must point to exactly one source candidate through
`source_candidate_id` and must keep `evidence_refs`. Those refs are not
optional bookkeeping: they are the reason a later Agent can audit why the
candidate was promoted, rejected, merged into another preference, or expired.
The current validator also requires the decision evidence to preserve the
candidate evidence refs.

The current examples use `promotion_mode: human_reviewed` and
`writes_long_term_memory: false` to avoid implying that this repository now owns
a long-term memory store.

`promoted` means "reviewed and allowed to feed a downstream review artifact",
not "written into durable Memory runtime". `merged` should be used when the
candidate is absorbed into another reviewed rule or profile. `expired` should
be used when the candidate is no longer actionable, stale, or superseded by
newer evidence.

See [`../examples/agentflow/memory_promotion_decision.example.json`](../examples/agentflow/memory_promotion_decision.example.json).

## Preference Profile

`poster_preference_profile.json` is a demo-only review artifact that turns
accepted memory candidates into prompt-facing preferences.

It must include:

- `source_memory_candidates`: accepted candidate ids.
- `source_promotion_decisions`: explicit promotion or review decision ids.
- `writes_long_term_memory: false`.

A preference profile is not durable memory. It is a bounded context input for a
future prompt, and must remain auditably linked to the review decision that
allowed candidate reuse.

## Context Bundle

`context_bundle.json` packages prompt-facing context layers for the next round.

For the PosterFlow memory demo it records:

- hot context: project prefix and prompt rules.
- warm context: preference profile, memory refs, and promotion decision refs.
- cold context: retrieval disabled with `not_configured` status.
- policy context: quality profile and provider gate boundary.

The bundle must reference the profile, raw candidate source, memory review, and
promotion decisions. `context_assembly_trace.json` must point to the bundle,
reuse the cache key, and keep `writes_long_term_memory: false`.

This is not RAG, a prefix-cache service, or a Memory runtime. It is a
side-effect-free context artifact.

## Next-Round Prompt

`next_round_prompt.json` is the prompt handoff for the next local run.

It must reference:

- `project_prefix_path`
- `preference_profile_path`
- `context_bundle_path`
- `memory_refs`
- `promotion_decision_refs`
- `cache_key`

It must keep `writes_long_term_memory: false`. A next-round prompt may reuse
accepted evidence, but it must not claim that a durable project preference was
written.

## Evidence Reuse Quality Review

`agentflow_memory_evidence_reuse_review` validates whether a run's evidence can
be traced into the next context pass.

For Local Alpha 0.4 it checks this chain:

```text
runtime evidence
-> operator feedback source
-> memory candidate
-> promotion decision
-> context bundle
-> second-pass prompt
```

This review is traceability-first. It may say that the evidence chain is
structurally complete, but it must not claim human acceptance, business
validation, or quality improvement unless separate comparison evidence exists.

Required boundaries:

- `runtime_status: not_implemented`
- `does_not_execute: true`
- `writes_long_term_memory: false`
- no private local paths, generated media paths, provider credentials, or
  signed URLs
- machine verification, human acceptance, business validation, and quality
  improvement claims remain separate labels

See [`../examples/agentflow/memory_evidence_reuse_review.example.json`](../examples/agentflow/memory_evidence_reuse_review.example.json).

## Memory Video Pipeline Protocol

`agentflow_memory_video_pipeline_protocol` is the first generic protocol file
for the memory-advantage video demo path.

It replaces one-off numbered demo modules as the planning surface for:

```text
project brief
+ source assets
+ provider route
+ baseline lane
+ memory-backed lane
+ reviewed memory cards
+ storyboard checkpoints
+ review rubric
+ claim boundaries
-> no-call request/review/run plan
```

Required boundaries:

- provider calls are not started during plan generation;
- generated media remains under ignored local run directories;
- baseline and memory-backed lanes must share the same task, source assets,
  provider route, duration, and script;
- the intended difference between lanes is memory context only;
- only `promoted` or `merged` memory cards may enter context;
- memory cards must keep `writes_long_term_memory: false`;
- human acceptance, business validation, quality-improvement claims, and
  durable Memory runtime remain separate labels.

CLI boundary:

- `memory-video-pipeline-*` commands are the visible product-facing CLI surface
  for this path;
- numbered memory-advantage demo commands are legacy evidence/operator entries,
  not the planning surface for new work;
- direct provider smoke commands remain gated compatibility tools and should
  not be used to imply product validation.

See
[`../examples/agentflow/memory_video_pipeline_protocol.example.json`](../examples/agentflow/memory_video_pipeline_protocol.example.json).

`agentflow_memory_video_pipeline_review` is the matching side-effect-free
review artifact for existing run evidence. It consumes the protocol plus an
explicit artifact manifest of I2V manifest paths.

Required boundaries:

- review generation must not scan run directories automatically;
- review generation must not start provider calls;
- every expected lane must be present for each listed run;
- provider URLs, signed URLs, data URLs, bearer headers, provider key fragments,
  and absolute local media paths must not be persisted;
- review output may record status, hashes, byte counts, lane repeat counts,
  storyboard checkpoints, and review rubric;
- cross-run stability fields are inputs for human visual review, not a machine
  quality verdict.

`agentflow_memory_video_pipeline_human_observation` records bounded human
visual notes on top of a review artifact.

Required boundaries:

- observation generation must not start provider calls;
- observation output must not copy generated media paths, provider URLs,
  signed URLs, credentials, or local absolute paths;
- observations must cover the review fields declared by the source review;
- supported verdicts are bounded labels such as `memory_backed_stronger`,
  `baseline_stronger`, `mixed`, and `no_clear_difference`;
- a visual observation is not human product acceptance, business validation, or
  definitive quality-improvement proof.

`agentflow_memory_video_pipeline_presentation_package` is the presentation-facing
summary built from the protocol, review, and observation artifacts.

Required boundaries:

- package generation must not start provider calls;
- package output must not copy generated media, provider URLs, signed URLs,
  credentials, data URLs, or local absolute paths;
- the package may summarize the user task, lane parity, storyboard checkpoints,
  memory cards, observation table, and claim boundaries;
- Slidev insert text may be Chinese-facing, but tests must validate the actual
  UTF-8 content rather than relying on PowerShell console rendering;
- a presentation package is competition material evidence, not human product
  acceptance, business validation, final creative-quality proof, or durable
  Memory runtime.

`agentflow_memory_video_pipeline_package` is the no-call product package summary
that links the current protocol-driven chain:

```text
plan
-> review
-> observation
-> presentation package
-> feedback-event draft
```

Required boundaries:

- package generation must not start provider calls;
- package output must not write durable Memory runtime;
- the feedback event remains a draft until a human explicitly persists it to
  the feedback source of truth;
- the package must not copy generated media, provider URLs, signed URLs,
  credentials, data URLs, or local absolute paths;
- the package is a workflow/review artifact, not human product acceptance or
  business validation.

## Loulan Memory Package

`agentflow_loulan_memory_package` is the first real-project pilot package for
the Memory Production Architecture. It lets AgentFlow Studio read an explicit
Loulan asset/evidence project as a no-call production-memory package.

Required boundaries:

- package generation reads explicit local manifests only, does not restructure
  Loulan, and does not start image, video, LLM, ASR, or download calls;
- package output must not contain absolute paths, generated media refs,
  provider credentials, bearer headers, signed URLs, or data URLs;
- `candidate`, `rejected`, `expired`, and missing-hash assets are blocked;
- `approved`, `promoted`, or `merged` assets may become eligible refs, but still
  require a reviewable promotion decision before durable memory use;
- unsafe built-in image routes must be blocked until the API workbench and
  provider ledger exist;
- the Web projection is read-only/copy-only, not a scanner, executor, Company
  memory writer, or provider UI;
- structure verification, runtime verification, human acceptance, provider
  smoke, business validation, and durable Memory runtime remain separate
  labels.

See [`../examples/agentflow/loulan_memory_package.example.json`](../examples/agentflow/loulan_memory_package.example.json).

## Reusable Asset Profile

`agentflow_reusable_asset_profile` records a promoted, evidence-backed asset
that may be considered in a future task.

Minimum fields:

- `schema_version`: currently `0.1.0`.
- `artifact_type`: `agentflow_reusable_asset_profile`.
- `asset_profile_id`: stable profile id.
- `source_intermediate_asset_ids`: source candidate assets.
- `promotion_decision_ref`: explicit promotion decision reference.
- `reuse_policy`: allowed modules, task types, and review requirements.
- `active_status`: active, inactive, or superseded.

Reusable asset profiles are not automatic long-term preference writes. They are
reviewable assets that future Agents may consider through an asset reuse
decision.

See [`../examples/agentflow/reusable_asset_profile.example.json`](../examples/agentflow/reusable_asset_profile.example.json).

## Asset Reuse Decision

`agentflow_asset_reuse_decision` records why an Agent selected or rejected
reusable assets for a target task. It is decision-only and must not execute a
workflow or invoke a skill.

See [`../examples/agentflow/asset_reuse_decision.example.json`](../examples/agentflow/asset_reuse_decision.example.json).

`agentflow.memory.assets.validate_asset_memory_contract_set` validates the
current asset and memory contract chain as an in-memory artifact set. It is a
contract validator, not Memory runtime: it does not promote candidates, write
long-term memory, create reusable profiles, or execute asset reuse decisions.

## Cost-Quality Signal

`cost_quality_trace.json` records execution strategy evidence, not a guarantee
of creative quality.

For local deterministic MVP runs, it should identify:

- `provider`: `local_deterministic`
- `execution_mode`: `local_deterministic`
- input and output artifact refs
- quality proxy metrics
- estimated cost, usually `0`

Future model-backed runs may extend provider, model, latency, token, retry, and
cost fields, but those fields should remain trace evidence for strategy review,
not a substitute for human acceptance.
