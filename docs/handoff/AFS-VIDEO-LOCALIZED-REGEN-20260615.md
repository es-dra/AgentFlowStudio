# AFS Video Localized Regeneration Requirement - 2026-06-15

Date: 2026-06-15
Owner roles: Product Framing, Studio Interaction Designer, Runtime/API Integrator, QA Gatekeeper
Status: experimental contract/UI skeleton implemented; provider-localized editing not implemented

## Why This Exists

The current Studio MVP can run a provider-gated image/keyframe path and a Kling
I2V path with explicit first frame, submit, poll, and safe preview. That proves
the runtime/browser/provider plumbing for video can work, but it does not yet
prove the product behavior the user actually wants:

When a generated video is already mostly accepted, the user wants to revise only
one targeted part through prompt edits, while preserving the rest of the clip as
much as possible.

Examples:

- Keep an accepted video, but adjust lighting at a specific frame or moment.
- Describe lighting precisely from the start and have it remain stable across
  regeneration.
- Keep the accepted scene, character, camera, and general timing, but change the
  way a character enters the frame.
- Regenerate from a prompt revision without unintentionally changing identity,
  wardrobe, background, camera language, duration, or unrelated motion.

## Current Problem Records

1. Stale Runtime route mismatch
   - Symptom: `keyframe-generations/preflight` returned 404 and generation got
     stuck when the service process was not restarted with the current code.
   - Current assessment: mitigated. Runtime client now attaches HTTP status and
     route metadata to errors and gives an explicit "Restart the 8790 Runtime
     Service from the current branch" message for missing generation preflight
     and video revision routes.

2. Multi-node fixed-asset detection inconsistency
   - Symptom: one keyframe node showed the "referenced but not connected /
     one-click connect" block, while another similar node did not.
   - Current assessment: partially mitigated. Generation preflight now fails
     closed in Studio when a fixed asset is label-matched by the prompt but not
     connected/injected/excluded, preventing a paid submit from silently skipping
     the intended carry path. Further browser QA is still needed across complex
     multi-node canvases.

3. Fixed-asset carry confirmation inconsistency
   - Symptom: one generation showed the "carried this run" confirmation, while
     another generation skipped it.
   - Current assessment: partially mitigated. Connected fixed assets still pass
     through the carry confirmation layer; label-matched but unconnected assets
     are blocked before submit instead of skipping confirmation.

4. Provider framing preference
   - Symptom: asking for a wide/full shot can still produce medium or close
     framing.
   - Current assessment: provider-quality issue, not a route failure. Needs
     shot-control fields, prompt wording, and human/AI scoring.

5. Video capability gap
   - Current Studio video node is I2V-oriented: explicit first frame -> Kling
     submit/poll/preview.
   - It is not yet a true localized video-editing workflow over an accepted
     base clip.

## Product Contract Needed

Add a first-class `video_revision` concept instead of treating each prompt edit
as an unrelated new video generation.

Proposed safe fields:

```text
base_video_artifact_id
base_video_job_id
base_lineage_root_job_id
parent_revision_job_id
revision_intent
editable_targets
locked_aspects
temporal_scope
reference_frames
preserve_policy
provider_capability_mode
result_comparison_summary
```

Field meanings:

- `base_video_artifact_id`: Runtime-safe reference to the accepted video.
- `base_lineage_root_job_id`: original accepted base video for a revision chain.
- `parent_revision_job_id`: immediate previous revision when revising a revision.
- `revision_intent`: what the user wants to change.
- `editable_targets`: lighting, character entrance, camera move, expression,
  prop movement, wardrobe, background, etc.
- `locked_aspects`: identity, outfit, environment, camera, duration, aspect
  ratio, tone, continuity, and any fixed visual assets that should not drift.
- `temporal_scope`: whole clip, time range, frame index, first half, entrance
  beat, ending beat, or named moment.
- `reference_frames`: Runtime image asset ids only; no local paths or provider
  URLs.
- `preserve_policy`: default to "preserve everything not explicitly changed".
- `provider_capability_mode`: `i2v_revision_attempt`, `v2v_edit`, `masked_edit`,
  or `unsupported`, depending on the actual provider.
- `result_comparison_summary`: safe QA summary of what changed and what drifted.

## UI Shape

For accepted video outputs:

- Add "use as base video" / "revise from this video" entrypoint.
- Show a revision panel with:
  - target change chips: lighting, entrance, camera, motion, expression, scene;
  - temporal scope: whole clip, moment, time range, frame anchor;
  - preserve list: character, outfit, background, camera, duration, style;
  - prompt box for the revision request;
  - pre-submit confirmation: "Change only X; preserve Y".
- After generation, show A/B comparison:
  - base video;
  - revised video;
  - user-visible drift notes;
  - accept revised / keep base / retry with stricter locks.

## Implemented Slice

Landed in this branch:

- Runtime model and routes:
  - `VideoRevisionRequest`
  - `POST /projects/{project_id}/video-revisions/preflight`
  - `POST /projects/{project_id}/video-revisions`
- The route is explicitly experimental and feature-flagged by
  `AFS_ENABLE_EXPERIMENTAL_VIDEO_REVISION`.
- The submit path writes `afs_video_revision_safe_manifest.v0.1` and returns a
  blocked safe response when the feature flag or video gate is closed.
- The route records best-effort preserve/change taxonomy, temporal scope,
  original base lineage, and `candidate_count=1`.
- Studio Runtime client exposes `preflightVideoRevision` and
  `generateVideoRevision`.
- Studio node menu can enable an experimental video revision draft from an
  accepted base video job.
- Studio submit preflight now blocks label-matched but unconnected fixed assets
  before paid image/video submit.

This slice does not call Kling for video revisions yet. It creates the contract,
UI state, safety manifest, and regression tests needed before a provider-specific
localized revision attempt is wired.

## Provider Reality Boundary

Prompt-only Kling I2V regeneration cannot be treated as guaranteed localized
video editing. Without provider support for video-to-video editing, masks,
temporal anchors, seeds, or frame-level controls, the result is a revision
attempt, not a deterministic patch.

MVP language should therefore be:

- Allowed: "create a revision attempt from an accepted base video, with explicit
  preserve/change instructions and comparison evidence."
- Not allowed yet: "guaranteed to change only one frame or one motion detail
  while every other pixel remains unchanged."

## Next Work Items

1. P1: browser-test fixed-asset detection and carry preflight consistency for
   complex multi-node image/video flows after the fail-closed guard.
2. P1: wire provider capability detection so the UI distinguishes I2V revision
   attempts from true V2V/masked editing if available later.
3. P1: add a richer Studio revision panel for accepted video -> revision prompt
   -> preserve/change confirmation. Current implementation is a node-menu draft
   skeleton.
4. P2: add video A/B comparison and QA scoring for target-change success,
   identity drift, background drift, motion drift, and temporal stability.

## Boundaries

- No provider call was made to create or verify this implementation slice.
- The implemented `video_revision` path does not yet call Kling or any other
  provider.
- No secret, signed URL, provider raw response, local private media path, or
  generated media byte is recorded here.
- This note is not human acceptance, business validation, or a claim that the
  localized video-editing product behavior already works.
