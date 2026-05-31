# AFS-MEMORY-ADVANTAGE-DEMO-014

Date: 2026-05-29

Status: 15-second desert occlusion-and-front-face-recovery I2V comparison
completed. This is stronger competition-facing case material than DEMO-013,
but it is still not final human acceptance or business validation.

## Goal

Use the accepted DEMO-012 memory-assisted desert keyframe as a fixed opening
frame and test a harder continuity question:

```text
Can the same character survive sand occlusion, side movement, camera arc, and
return to a same-angle front-facing identity check?
```

The intended proof target is character and scene continuity under motion, not
random prompt retakes.

## Route

```text
source keyframe: DEMO-012 memory_assisted/desert_wind_walk keyframe
provider: Kling I2V
model: kling-v3
duration requested: 15 seconds
duration observed: 15.041667 seconds
transport: curl
lanes: baseline, memory_assisted
```

Fairness contract:

- same source keyframe;
- same provider, model, mode, duration, and transport;
- same occlusion/recovery storyboard timing;
- baseline prompt uses normal professional continuity instructions;
- memory-assisted prompt adds explicit visual memory locks, scene physics
  locks, and final same-person recovery checks.

## Runtime Outputs

Ignored runtime root:

```text
data/processed/runs/memory_advantage_demo_014/desert_occlusion_recovery_i2v
```

Key artifacts:

- `baseline/video_candidates/candidate_001.mp4`
- `baseline/kling_i2v_smoke_manifest.json`
- `baseline/kling_i2v_task_state.json`
- `memory_assisted/video_candidates/candidate_001.mp4`
- `memory_assisted/kling_i2v_smoke_manifest.json`
- `memory_assisted/kling_i2v_task_state.json`
- `comparison_videos/desert_occlusion_15s_baseline_vs_memory.mp4`
- `review_frames/desert_occlusion_15s_contact_sheet.jpg`
- `desert_occlusion_15s_review.json`

## Recovery Fix

Before this completed run, the first DEMO-014 baseline attempts exposed a
provider-tooling reliability issue:

- Kling create could succeed, but a later curl GET polling failure surfaced only
  as a generic `CurlError`.
- The local client previously wrote the safe manifest only after successful
  video download, so a poll failure after create lost the provider task id.
- That made a recoverable provider task look like an unrecoverable failure.

The client now writes a safe task-state file immediately after task creation and
updates it on success or polling/download failure. The state file includes only
safe recovery fields such as service id, API family, model, task id, task
status, timestamps, source image byte count/hash, and artifact policy. It does
not persist provider URLs, Authorization headers, JWTs, keys, data URLs, or the
local source-image path.

Focused recovery tests cover:

- curl polling failure preserves a safe task state;
- stderr is sanitized and does not expose keys or signed URLs;
- resume from task state can poll, download, and write the final manifest.

## Media QA

Both source videos:

```text
codec: H.264
resolution: 1080x1920
duration: 15.041667 seconds
frame rate: 24 fps
frame count: 361
```

Side-by-side comparison video:

```text
codec: H.264
resolution: 1080x960
duration: 15.041667 seconds
frame rate: 24 fps
frame count: 361
```

## Technical Visual Review

This run is more useful than DEMO-013 because the final check is explicitly
same-angle front-face recovery after occlusion.

Frame-level observations:

- `0s`: both lanes start from the same keyframe and are therefore comparable.
- `3s`: both lanes enter the sand gust; occlusion is visible in both.
- `6s`: baseline loses face evidence through crop/occlusion and emphasizes the
  walking body; memory-assisted recovers a readable side face and hair
  silhouette sooner.
- `9s`: both lanes keep the white T-shirt, jeans, ponytail, and desert setting.
  Memory-assisted keeps the subject more readable during the side movement.
- `12s`: both lanes begin returning to front framing. Memory-assisted retains
  stronger scene anchor continuity with the tower and sand field.
- `14.8s`: both lanes recover to a clear front-facing woman. Memory-assisted is
  stronger on full body, outfit, tower, and scene continuity. Baseline still has
  a readable face, so this should be claimed as a visible case signal, not an
  automatic or definitive proof.

## Claim Boundary

Verified:

- the Kling I2V provider route completed for both lanes;
- safe task-state persistence and resume support are covered by focused tests;
- generated artifacts are under ignored `data/processed/*`;
- source videos and side-by-side video are valid MP4s with matching duration,
  frame rate, and frame count;
- local manifests and task-state files do not persist provider URLs, bearer
  headers, JWTs, provider keys, source data URLs, or local source-image paths.

Not claimed:

- final human acceptance;
- final creative-quality validation;
- business validation;
- durable Memory runtime behavior;
- statistically definitive memory-advantage proof.

## Next Step

Use DEMO-014 as the current best presentation case for the competition deck:

- show the side-by-side video plus the 0/3/6/9/12/14.8s contact sheet;
- explain the controlled variable: normal continuity prompt versus structured
  visual memory locks and recovery checks;
- present the claim as "memory-assisted prompting gives stronger continuity
  signals under occlusion and recovery" rather than "the system proves quality";
- collect human review notes before converting it into a formal roadshow claim.
