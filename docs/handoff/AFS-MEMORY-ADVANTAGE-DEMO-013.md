# AFS-MEMORY-ADVANTAGE-DEMO-013

Date: 2026-05-29

Status: 15-second desert long-take I2V pressure test completed with two Kling
I2V calls. This is a continuity diagnosis run, not final memory-advantage proof.

## Goal

Use the accepted DEMO-012 desert keyframe as a fixed starting frame and test
whether a longer continuous shot exposes clearer baseline versus
memory-assisted character-consistency differences.

The problem being tested is specific: the earlier 5-second clips were too short
to make the difference obvious. This run increases the continuity pressure by
adding a 15-second no-cut movement with walking, camera orbit, sand occlusion,
lighting transfer, and a final half-body look-back.

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
- same 15-second storyboard timing;
- only prompt difference is normal professional continuity prompting versus
  structured visual memory locks and checkpoints.

## Runtime Outputs

Ignored runtime root:

```text
data/processed/runs/memory_advantage_demo_013/desert_long_take_i2v
```

Key artifacts:

- `baseline/video_candidates/candidate_001.mp4`
- `memory_assisted/video_candidates/candidate_001.mp4`
- `comparison_videos/desert_15s_baseline_vs_memory.mp4`
- `review_frames/desert_15s_frame_contact_sheet.jpg`
- `desert_15s_review.json`

## Technical Visual Review

This run is useful because it exposes more drift opportunities than the
5-second clips. It is not a decisive memory-assisted win.

Frame-level findings:

- `0s`: both lanes start nearly identical because they use the same source
  keyframe.
- `5s`: memory-assisted keeps a more front-readable walking figure and stronger
  outfit visibility; baseline shifts into a profile view with less face
  evidence.
- `10s`: both lanes preserve the white T-shirt, jeans, and ponytail near the
  tower. Baseline has a clear side-walk composition; memory-assisted has a
  stronger environment transfer but is mostly rear view.
- `14.8s`: both lanes recover to readable half-body shots. Baseline face is not
  weaker than memory-assisted here, so the final frame cannot support a strong
  advantage claim.

## Claim Boundary

Verified:

- two live Kling I2V provider calls succeeded;
- both source videos are H.264 MP4, 1080x1920, 15.041667 seconds, 24 fps, and
  361 frames;
- the local side-by-side comparison video is H.264 MP4, 1080x960, 15.041667
  seconds, 24 fps, and 361 frames;
- generated artifacts are under ignored `data/processed/*`;
- text artifact scan found no provider URLs, bearer headers, data URLs,
  provider config paths, or local source-image absolute paths.

Not claimed:

- final human acceptance;
- creative-quality validation;
- business validation;
- durable Memory runtime behavior;
- definitive memory-advantage proof.

## Next Step

Use this as a diagnostic result, not as the final competition proof. The next
stronger proof setup should make the final identity check harder and more
objective:

- force a same-angle face check at the end instead of allowing different final
  camera angles;
- add an explicit occlusion-and-reappearance beat in the middle;
- if the provider route supports it, add official element/reference controls
  rather than relying only on prompt wording;
- score the pair with the same 0s/5s/10s/15s anchor grid before spending more
  generation budget.
