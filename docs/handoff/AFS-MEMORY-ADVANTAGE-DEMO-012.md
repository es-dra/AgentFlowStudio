# AFS-MEMORY-ADVANTAGE-DEMO-012

Date: 2026-05-29

Status: MiniMax I2I/reference-image support is wired and the six-keyframe
fixed-asset consistency experiment has run once. Six keyframes were generated
under the ignored runtime path. The user then accepted the keyframes as
sufficient for storyboard comparison, and Kling I2V generated six matching
5-second clips. This is usable comparison evidence, not final product
validation.

## Goal

Test whether the accepted Yiqi character reference holds identity and physical
continuity better when the generation lane receives structured visual memory.

This replaces the earlier prompt-retake direction. The proof target is not
better prompt wording. The proof target is one fixed character asset moving
through different scene stresses.

## Budget

```text
3 scenes x 2 lanes = 6 keyframes
```

The six images are the full planned keyframe budget:

- baseline/desert_wind_walk;
- baseline/neon_rain_turn;
- baseline/combat_dodge_motion;
- memory_assisted/desert_wind_walk;
- memory_assisted/neon_rain_turn;
- memory_assisted/combat_dodge_motion.

No retakes are allowed before the first review unless the request fails at the
provider/runtime level.

The first six-image run has now been spent and reviewed. The follow-on six I2V
video calls have also been spent. Treat the outputs as early demo evidence, not
as final demo proof.

## Provider Route

Image route:

```text
MiniMax / image-01 / /v1/image_generation / subject_reference character
```

The subject reference image is sent at runtime as a data URL. It is not written
to committed files, safe manifests, or provider plans.

Video route:

```text
Kling I2V / kling-v3 / 6 clips generated
```

Kling I2V started after the user explicitly judged the keyframes worth turning
into storyboard comparison clips.

## Fairness Contract

Baseline and memory-assisted lanes use:

- the same fixed character reference image;
- the same MiniMax service;
- the same `image-01` model;
- the same `9:16` aspect ratio;
- one candidate per request;
- the same seed per scene.

The only intended difference is:

```text
baseline: normal professional character-consistency prompt
memory_assisted: same reference plus Visual Memory Asset Card Yiqi v1
```

## Scene Stress Tests

| Scene | Stressor | Review focus |
|---|---|---|
| `desert_wind_walk` | wind and wide-environment transfer | Ponytail, T-shirt, jeans, wind direction, body lean. |
| `neon_rain_turn` | wet lighting and three-quarter face transfer | Face family, wet high-ponytail silhouette, outfit under neon rain. |
| `combat_dodge_motion` | fast pose and motion-physics transfer | Hair inertia, sneaker traction, body balance, natural 3D anime proportions. |

## No-Call Package

Generated under ignored runtime root:

```text
data/processed/runs/memory_advantage_demo_012/asset_i2i_i2v_consistency/plan
```

Files:

- `accepted_character_asset.json`
- `visual_memory_asset_card.json`
- `scene_stress_tests.json`
- `image_requests.json`
- `evaluation_rubric.json`
- `run_plan.json`
- `demo_012_report.md`

CLI:

```powershell
.\.venv\Scripts\python.exe -m apps.cli.main memory-advantage-demo-012-plan --subject-reference-image-ref yiqi_front.png --output data\processed\runs\memory_advantage_demo_012\asset_i2i_i2v_consistency\plan
```

Runtime CLI, only after the user confirms the local reference image path and
the image provider gate is intentionally enabled:

```powershell
$env:AFS_ALLOW_REMOTE_IMAGE='true'
.\.venv\Scripts\python.exe -m apps.cli.main memory-advantage-demo-012-i2i-runtime --subject-reference-image <ignored-local-reference.png> --run-dir data\processed\runs\memory_advantage_demo_012\asset_i2i_i2v_consistency
```

Storyboard CLI, only after the keyframes are accepted for video spending and
the video provider gate is intentionally enabled:

```powershell
$env:AFS_ALLOW_REMOTE_VIDEO='true'
.\.venv\Scripts\python.exe -m apps.cli.main memory-advantage-demo-012-i2v-runtime --run-dir data\processed\runs\memory_advantage_demo_012\asset_i2i_i2v_consistency --duration 5 --mode pro --poll-interval-sec 5 --max-polls 120 --transport curl
```

## Claim Boundary

Verified:

- MiniMax I2I payload path supports `subject_reference` with a runtime data URL.
- Safe manifests persist source image hash, byte count, and MIME type only.
- Safe plans and manifests do not persist provider keys, bearer headers, source
  image data URLs, provider URLs, or local absolute source-image paths.
- DEMO-012 no-call request matrix is generated.
- Six MiniMax I2I provider calls succeeded with `image-01`.
- The generated files are JPEG images stored as `.jpg` under the ignored
  runtime path.
- Six Kling I2V provider calls succeeded with `kling-v3`.
- The generated videos are 1080x1920 H.264 MP4 files, about 5.04 seconds each,
  at 24 fps.

Not claimed:

- final human acceptance of generated videos;
- creative-quality validation;
- business validation;
- durable Memory runtime behavior;
- final memory-advantage proof.

## 2026-05-29 Runtime Notes

The first live attempt against `image-01-live` failed with MiniMax response
`status_code 2056`. The local Token Plan route was therefore switched to
`image-01`, which is the model exposed in the existing MiniMax image smoke path
and the safer choice for this account's image resource package. With `image-01`,
the six I2I calls completed.

Runtime outputs:

```text
data/processed/runs/memory_advantage_demo_012/asset_i2i_i2v_consistency/image_runtime_summary.json
data/processed/runs/memory_advantage_demo_012/asset_i2i_i2v_consistency/image_review.json
data/processed/runs/memory_advantage_demo_012/asset_i2i_i2v_consistency/image_review.html
data/processed/runs/memory_advantage_demo_012/asset_i2i_i2v_consistency/i2v_runtime_summary.json
data/processed/runs/memory_advantage_demo_012/asset_i2i_i2v_consistency/i2v_review.json
data/processed/runs/memory_advantage_demo_012/asset_i2i_i2v_consistency/i2v_review.html
data/processed/runs/memory_advantage_demo_012/asset_i2i_i2v_consistency/i2v_media_probe.json
data/processed/runs/memory_advantage_demo_012/asset_i2i_i2v_consistency/live/
```

The initial technical image review said the keyframes were imperfect and should
not be overclaimed. The user then explicitly judged the keyframes sufficient for
storyboard comparison, so the video gate was opened for this controlled I2V
batch.

Kling I2V runtime:

```text
i2v_storyboard_provider_smoke_succeeded
```

Generated comparison artifacts:

```text
data/processed/runs/memory_advantage_demo_012/asset_i2i_i2v_consistency/review_frames/i2v_contact_sheet.jpg
data/processed/runs/memory_advantage_demo_012/asset_i2i_i2v_consistency/comparison_videos/desert_wind_walk_baseline_vs_memory.mp4
data/processed/runs/memory_advantage_demo_012/asset_i2i_i2v_consistency/comparison_videos/neon_rain_turn_baseline_vs_memory.mp4
data/processed/runs/memory_advantage_demo_012/asset_i2i_i2v_consistency/comparison_videos/combat_dodge_motion_baseline_vs_memory.mp4
data/processed/runs/memory_advantage_demo_012/asset_i2i_i2v_consistency/comparison_videos/all_scenes_baseline_vs_memory_sequence.mp4
```

Current side-by-side findings:

- `desert_wind_walk`: memory-assisted keeps a more stable face and hair
  silhouette through the sand walk. Both lanes still have imperfect shirt/waist
  anchoring.
- `neon_rain_turn`: memory-assisted keeps face readability better across the
  turn, but shirt material and color drift remain under the neon/rain lighting.
- `combat_dodge_motion`: memory-assisted keeps face and pose readability better
  during the dodge. The pink hair tie from the keyframe still persists.

This is useful early demo evidence: the fixed-reference I2I -> I2V pipeline now
runs end to end, and the side-by-side clips show a visible memory-assisted
continuity signal. It is still not final creative-quality validation or business
validation.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_minimax_image_smoke.py tests\test_memory_advantage_demo_012.py -q
# 15 passed

.\.venv\Scripts\python.exe -m apps.cli.main memory-advantage-demo-012-plan --subject-reference-image-ref yiqi_front.png --output data\processed\runs\memory_advantage_demo_012\asset_i2i_i2v_consistency\plan
# provider calls not started

$env:AFS_ALLOW_REMOTE_IMAGE='true'
.\.venv\Scripts\python.exe -m apps.cli.main memory-advantage-demo-012-i2i-runtime --subject-reference-image <ignored-local-reference.png> --run-dir data\processed\runs\memory_advantage_demo_012\asset_i2i_i2v_consistency
# Images: 6

$env:AFS_ALLOW_REMOTE_VIDEO='true'
.\.venv\Scripts\python.exe -m apps.cli.main memory-advantage-demo-012-i2v-runtime --run-dir data\processed\runs\memory_advantage_demo_012\asset_i2i_i2v_consistency --duration 5 --mode pro --poll-interval-sec 5 --max-polls 120 --transport curl
# Videos: 6
```

Focused verification:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_memory_advantage_demo_012.py tests\test_kling_video_smoke.py tests\test_kling_video_request_plan.py -q
# 24 passed
```

`ffprobe` confirmed all six source videos are H.264 MP4, 1080x1920, about
5.04 seconds, 24 fps, and 121 frames. The derived side-by-side comparison videos
also probed as valid MP4s.

Sensitive string scans over the generated plan, runtime reviews, and comparison
metadata found no keys, bearer headers, data URLs, provider URLs, or local
absolute source-image paths.

## Next Step

Use the current comparison clips as the first competition-facing evidence case,
with a careful explanation of the measurement boundary:

- show baseline and memory-assisted clips side by side;
- mark per-scene anchors: face family, ponytail, outfit, pose/body geometry,
  scene physics, and motion continuity;
- say "early visual evidence" instead of "final proof";
- keep final human acceptance and business validation pending.

The next controlled generation slice should not be more random prompt retakes.
It should prepare a stricter reference-prep path:

- crop/export a single front-facing subject reference for MiniMax
  `subject_reference`;
- keep the multiview sheet as memory evidence, not the direct subject image;
- add a preflight visual QA gate before I2V: no exposed midriff, no hair
  accessories, full-length tucked white T-shirt, blue skinny jeans, white
  sneakers, and same face family.
