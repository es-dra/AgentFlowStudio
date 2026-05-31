# AFS-POST-DEMO-PRODUCTIZATION-ROADMAP

Status: post-demo productization roadmap derived from Local Alpha 0.4 and the
MiniMax/Kling memory-advantage experiments.

This document is a handoff plan. It is not product acceptance, business
validation, or proof that durable Memory runtime is implemented.

## Current Position

AgentFlow Studio has enough evidence to move from ad hoc demo exploration into
a productization loop.

Working evidence:

- Local Alpha 0.4 can run one real local package from local media and scripts.
- Web operator review can point at the Local Alpha 0.4 run.
- Memory evidence reuse can be structurally reviewed without writing durable
  memory.
- MiniMax image generation and Kling I2V can support a local image/video demo
  route when provider gates are explicitly enabled.
- RECORDING-016 produced the current strongest memory-advantage signal:
  repeated same-keyframe, same-task, same-model, same-duration I2V runs where
  the baseline varied more and the memory-backed lane was more stable.

Not yet claimed:

- final human product acceptance;
- business validation;
- durable Memory runtime;
- fully productized workbench;
- fully automated memory extraction from every user feedback loop.

## Product Goal

The next product milestone should make one complete memory-backed production
loop real:

```text
brief
-> reference assets
-> selected memory cards
-> baseline run
-> memory-backed run
-> side-by-side review
-> feedback capture
-> memory candidate
-> promotion decision
-> next context bundle
```

The goal is not to prove that every generated video is better. The goal is to
show that reviewed production evidence can become reusable context, reducing
repeat-generation drift and making iteration cheaper.

## Three User-Level Objectives

### 1. Architecture Completeness

Target:

```text
script / storyboard
-> asset memory
-> keyframe generation
-> I2V generation
-> review
-> feedback
-> reuse
```

Next implementation direction:

- Stop creating new numbered demo modules.
- Promote the protocol-driven memory video pipeline into the main demo route.
- Keep provider adapters separate from workflow contracts.
- Keep review and observation artifacts separate from product acceptance.
- Add a retirement decision for each existing demo module: promote, archive, or
  delete after replacement.

Evidence needed:

- one protocol file drives baseline and memory-backed lanes;
- lane parity is checked before provider calls;
- output review includes identity, wardrobe, scene anchor, motion, occlusion,
  feedback, and cross-run stability fields;
- generated media stays ignored.

### 2. Image / Video Demo That Can Run

Target:

```text
fixed character reference
-> MiniMax I2I keyframes
-> Kling I2V storyboards
-> repeated comparison
-> presentation package
```

Current best route:

- MiniMax for image / image-to-image.
- Kling for image-to-video.
- DeepSeek and other LLM providers later for analysis, memory compilation, and
  prompt projection, behind explicit LLM gates.

Near-term demo rule:

- baseline receives the same source assets, script, provider route, model, and
  duration;
- memory-backed receives the same inputs plus eligible character, scene, and
  feedback memory;
- the comparison should emphasize repeatability, asset retention, and feedback
  reuse, not a single lucky image.

Evidence needed:

- two or more runs per lane when budget allows;
- protocol files saved under ignored runtime paths;
- side-by-side videos and contact sheets generated under ignored runtime paths;
- observation recorded as bounded visual evidence;
- Slidev or run-sheet material references generated media without committing
  it.

### 3. Workbench That Is Usable

Target first screen:

```text
Project
Assets
Memory Loaded
Baseline Run
Memory-backed Run
Review
Feedback
Next Pass
```

The workbench should not be a generic dashboard. It should guide one operator
through the memory-backed production loop.

Required states:

- no plan;
- planned;
- generating;
- review ready;
- feedback captured;
- memory candidate drafted;
- promotion decision ready;
- blocked.

Memory visibility:

- what memory was loaded;
- why it was eligible;
- which prompt/request projection it produced;
- what changed versus baseline;
- what feedback was captured;
- what will be reused next time.

Evidence needed before Web implementation:

- approved workbench design brief under `docs/workbench/`;
- desktop and narrow viewport smoke plan;
- local-only and non-persistent behavior documented;
- no automatic local directory scanning;
- no provider calls from the design lane.

## Memory And Knowledge-Base Feedback Loop

The local Company knowledge base remains the source of truth for company-level
operating knowledge. This repo should only hold execution-facing projections
needed by AgentFlow Studio development.

Near-term rule:

- capture candidate learnings in project docs and handoffs;
- do not write private Company knowledge automatically;
- do not copy confidential company strategy, costs, provider secrets, customer
  details, or unpublished business assumptions into this repo;
- after review, the user may decide which learnings should be promoted into the
  local Company knowledge base.

What should be captured:

- provider behavior that affects future runs;
- repeatability evidence;
- prompt-projection rules that came from reviewed assets;
- human feedback that can become a small reusable patch;
- failed assumptions that should block future reuse.

## Provider Gateway Direction

The current local secret/config approach is acceptable for the demo phase if
the repo keeps strict boundaries:

- no provider keys in Git;
- no signed URLs or bearer tokens in artifacts;
- capability gates remain separate for LLM, image, video, ASR, and download.

The later company gateway remains compatible with the current plan. It should
be introduced after the local production loop is cleaner.

Gateway responsibilities later:

- credential management;
- provider routing;
- async task tracking;
- quota and cost tracking;
- retries and provider-specific recovery;
- redacted logs;
- artifact download policy.

## Parallel Queue

Recommended order:

| Lane | Purpose | Entry Condition | Output |
|---|---|---|---|
| AFS-MEMORY-PIPELINE-MVP-001 | Replace bespoke demo scripts with one protocol-driven runner | Current no-call/review/presentation slices are stable enough to continue | protocol runner, review output, feedback-event draft |
| AFS-WORKBENCH-REDESIGN-001 | Design the operator surface around the production loop | Product loop vocabulary is fixed | workbench design doc and UI state model |
| AFS-ACCEPTANCE-FEEDBACK-001 | Capture human review separately from machine tests | Selected demo artifacts are ready | factual feedback artifact and reuse candidates |
| AFS-MEMORY-REVIEW-CLI-001 | Expose memory reuse review as read-only CLI | Evidence reuse validator remains stable | no-write review command |
| AFS-WEB-EVIDENCE-SUMMARY-001 | Show review summary in Web without memory promotion | Workbench design chooses the display model | passed/failed/not-reviewed UI |
| Provider Gateway Spike | Centralize provider calls later | Local pipeline is cleaner and demo route is stable | gateway contract and migration plan |

## Stop Conditions

Do not proceed to the next stage if:

- baseline and memory-backed lanes do not share source assets, model, duration,
  and script;
- generated media or provider secrets would enter Git;
- rejected or expired memory would enter context;
- tests or provider smoke are being used as human acceptance;
- a new numbered demo module is being added instead of the protocol runner;
- Web implementation starts before the workbench design names the operator
  workflow and states.

## Next Action

Continue with `AFS-MEMORY-PIPELINE-MVP-001`:

1. Promote the current protocol/review/observation/presentation slices into one
   end-to-end no-call product command.
2. Add an explicit feedback-event draft artifact.
3. Keep optional MiniMax/Kling execution behind existing image/video gates.
4. Use RECORDING-016 as presentation evidence, not as a permanent product path.

Then start `AFS-WORKBENCH-REDESIGN-001` as a docs-only design lane before
touching Web implementation.
