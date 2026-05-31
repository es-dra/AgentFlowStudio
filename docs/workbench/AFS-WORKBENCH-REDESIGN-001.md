# AFS-WORKBENCH-REDESIGN-001

Status: docs-only design for the next AgentFlow Studio memory production
workbench.

This is a design artifact, not Web implementation. It does not call providers,
write durable Memory runtime, scan local directories, or validate product
quality.

## Primary Operator Workflow

The workbench is for one local operator running a memory-backed production loop:

```text
Project
-> Assets
-> Memory Loaded
-> Baseline Run
-> Memory-backed Run
-> Review
-> Feedback
-> Next Pass
```

The first implementation should be a guided production workspace, not a generic
dashboard. It should make the next action obvious and keep old artifact
inspection behind the current loop.

## First Screen

The first screen should show one project package at a time.

Required top-level regions:

| Region | Purpose | Primary evidence |
|---|---|---|
| Project | Show brief, storyboard, target format, and provider route | protocol summary |
| Assets | Show selected source keyframes and reviewed asset cards | protocol source assets and memory cards |
| Memory Loaded | Show eligible memory selected for this pass | context bundle / request projection |
| Baseline Run | Show stateless lane status and outputs | lane plan and review refs |
| Memory-backed Run | Show memory lane status and outputs | lane plan and review refs |
| Review | Show lane parity, storyboard adherence, and visual notes | review and observation artifacts |
| Feedback | Show draft feedback event and next candidate | feedback-event draft |
| Next Pass | Show what can be reused or blocked next | promotion decision / context bundle draft |

The first screen should not start with contract inventory, raw file lists, or a
system health dashboard. Those are secondary inspection tools.

## State Model

The workbench state should be explicit and visible:

- no plan: no protocol package has been loaded or drafted;
- planned: protocol and no-call request plan exist;
- generating: at least one lane is running or waiting for provider output;
- review ready: both expected lanes have reviewable artifacts;
- feedback captured: an `agentflow_feedback_event` draft exists;
- memory candidate drafted: feedback has produced a candidate memory draft;
- promotion decision ready: a human can promote, merge, reject, or expire the
  candidate;
- blocked: required inputs, provider gate, artifact parity, or review evidence
  is missing.

State transitions must be evidence-driven. A green machine check cannot upgrade
the state to human acceptance or business validation.

## Memory Provenance Display

The workbench must make memory reuse inspectable.

For every loaded memory item, show:

- what memory was loaded;
- why it was eligible;
- source evidence refs;
- promotion status;
- which prompt/request projection it produced;
- what feedback will change next time.

Rejected or expired memory must be shown as blocked, not silently omitted when
the operator is investigating a failure.

## Interaction Pattern

Primary actions:

- load or draft protocol package;
- run no-call package generation;
- start gated image or video execution only when the operator explicitly enables
  the relevant capability;
- open side-by-side review;
- capture feedback;
- draft memory candidate;
- prepare next pass.

Secondary actions:

- inspect raw JSON;
- copy feedback JSON;
- open package report;
- view bridge health;
- view provider gate status.

Buttons should be tied to one visible state transition. Avoid ambiguous actions
such as "improve", "optimize", or "auto-fix" until the underlying contract
exists.

## Local-Only Boundaries

The workbench remains a local operator surface:

- no SaaS;
- no auth, accounts, uploads, cloud sync, cookies, or collaboration service;
- no browser persistence, including no localStorage and no IndexedDB;
- no provider calls unless a capability-specific gate is explicitly enabled;
- no automatic directory scanning;
- no manifest path auto-read for media;
- no durable Memory runtime;
- no private Company knowledge write;
- no generated media committed to Git.

Review Mode may keep explicit file selection. Production Mode may talk to the
local bridge only on `127.0.0.1`.

## Data Flow

The design should map to the current package contract:

```text
agentflow_memory_video_pipeline_protocol
-> memory-video-pipeline-package
-> agentflow_memory_video_pipeline_package
-> feedback-event draft
-> memory candidate draft
-> promotion decision
-> next context bundle
```

The first UI implementation can read already generated package artifacts before
it supports live provider execution.

## What The Workbench Should Not Claim

The workbench may show:

- structure verification;
- runtime verification;
- provider smoke status;
- bounded human visual observation;
- feedback captured;
- memory candidate drafted.

The workbench must not relabel those as:

- human product acceptance;
- business validation;
- durable Memory runtime;
- final creative quality proof.

## Verification Plan Before Implementation

Before Web implementation starts, add tests or smoke checks for:

- design document discoverability from docs index and task brief index;
- no provider calls in the design lane;
- desktop viewport layout for the first screen;
- narrow viewport layout with no overlapping text;
- state labels for no plan, planned, generating, review ready, feedback
  captured, memory candidate drafted, promotion decision ready, and blocked;
- memory provenance panel showing what loaded, why eligible, request
  projection, and feedback effect;
- explicit local-only language and no browser persistence;
- generated media and provider secrets not appearing in committed examples.

Browser verification should use the in-app browser after implementation. This
design lane does not start a dev server.

## Implementation Queue

1. Add a Web design fixture for an existing
   `agentflow_memory_video_pipeline_package`.
2. Build a static first-screen view from that fixture without provider calls.
3. Add state pills and disabled/enabled action rules.
4. Add memory provenance panel.
5. Add side-by-side review shell.
6. Add feedback-event draft display and copy action.
7. Add a next-pass panel for candidate and promotion decision drafts.

Provider execution buttons should stay disabled until the local bridge route
and capability gate are both explicit.
