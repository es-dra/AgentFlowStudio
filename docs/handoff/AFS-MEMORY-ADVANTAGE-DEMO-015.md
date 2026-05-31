# AFS-MEMORY-ADVANTAGE-DEMO-015

Date: 2026-05-29

Status: memory-backed production protocol is implemented, planned, and run once
through Kling I2V. This is protocol/runtime evidence plus technical visual
review, not final human acceptance or business validation.

## Goal

Turn the demo framing away from "long prompt versus short prompt" and toward a
production-system comparison:

```text
baseline: stateless generation from the current task and current keyframe
memory-backed: same user task and keyframe plus automatic asset, scene, and
feedback memory reuse
```

The same user task is used for both lanes. The memory-backed lane receives a
runtime projection from structured memory cards:

- `character_memory_card`;
- `scene_memory_card`;
- `feedback_memory_patch`.

The provider prompt is treated as an execution projection, not the product
claim.

## Protocol Package

Ignored runtime root:

```text
data/processed/runs/memory_advantage_demo_015/memory_backed_desert_recovery_i2v
```

No-call protocol files:

- `plan/protocol_card.json`
- `plan/memory_inputs.json`
- `plan/generation_projections.json`
- `plan/video_requests.json`
- `plan/scorecard_rubric.json`
- `plan/run_plan.json`
- `plan/demo_015_report.md`

CLI:

```powershell
.\.venv\Scripts\python.exe -m apps.cli.main memory-advantage-demo-015-plan --source-keyframe-ref demo_012_memory_desert_candidate_001.jpg --output data\processed\runs\memory_advantage_demo_015\memory_backed_desert_recovery_i2v\plan
```

## Runtime Route

```text
source keyframe: DEMO-012 memory_assisted/desert_wind_walk candidate_001.jpg
provider: Kling I2V
model: kling-v3
duration requested: 15 seconds
duration observed: 15.041667 seconds
transport: curl
lanes: baseline, memory_backed
```

Runtime command:

```powershell
$env:NARRATOCUT_ALLOW_REMOTE_VIDEO='true'
.\.venv\Scripts\python.exe -m apps.cli.main memory-advantage-demo-015-i2v-runtime --source-keyframe data\processed\runs\memory_advantage_demo_012\asset_i2i_i2v_consistency\live\memory_assisted\desert_wind_walk\image\image_candidates\candidate_001.jpg --run-dir data\processed\runs\memory_advantage_demo_015\memory_backed_desert_recovery_i2v --duration 15 --mode pro --poll-interval-sec 5 --max-polls 180 --transport curl
```

## Runtime Outputs

Key artifacts:

- `live/baseline/desert_occlusion_recovery/i2v/video_candidates/candidate_001.mp4`
- `live/baseline/desert_occlusion_recovery/i2v/kling_i2v_smoke_manifest.json`
- `live/baseline/desert_occlusion_recovery/i2v/kling_i2v_task_state.json`
- `live/memory_backed/desert_occlusion_recovery/i2v/video_candidates/candidate_001.mp4`
- `live/memory_backed/desert_occlusion_recovery/i2v/kling_i2v_smoke_manifest.json`
- `live/memory_backed/desert_occlusion_recovery/i2v/kling_i2v_task_state.json`
- `comparison_videos/demo_015_baseline_vs_memory_backed_15s.mp4`
- `review_frames/demo_015_contact_sheet.jpg`
- `i2v_review.json`
- `i2v_review.html`

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

FFmpeg emitted `Late SEI is not implemented` and single-image sequence pattern
warnings while deriving review artifacts, but the derived MP4/JPG artifacts were
written and loaded successfully.

## Technical Visual Review

This run is useful, but not a decisive memory win.

Frame-level observations:

- `0s`: both lanes start from the same source keyframe.
- `3s`: baseline keeps a clearer front-readable face; memory-backed turns more
  side-facing while preserving outfit and ponytail.
- `6s`: baseline remains readable and keeps the tower; memory-backed enters the
  heavier sand occlusion specified by the protocol.
- `9s`: baseline is mostly a sand-obscured silhouette; memory-backed has
  recovered a side-body view with ponytail, outfit, and tower readable.
- `12s`: both lanes recover readable body and scene anchors.
- `14.8s`: both lanes retain the tower and wardrobe; memory-backed is slightly
  less front-facing than the final checkpoint asked for.

Scorecard in `i2v_review.json` records both lanes as tied after penalties:

```text
baseline: total_before_penalty 9, total_after_penalty 8
memory_backed: total_before_penalty 10, total_after_penalty 8
```

Decision:

```text
keep_as_protocol_evidence_not_decisive_memory_advantage_proof
```

## Claim Boundary

Verified:

- the no-call protocol package is generated;
- the CLI exposes plan and gated I2V runtime commands;
- two live Kling I2V provider calls succeeded;
- generated artifacts are under ignored `data/processed/*`;
- videos are valid H.264 MP4s with matching duration, frame rate, and frame
  count;
- manifests and task states do not persist provider URLs, bearer headers, JWTs,
  provider keys, source data URLs, or local source-image paths.

Not claimed:

- final human acceptance;
- creative-quality validation;
- business validation;
- durable Memory runtime behavior;
- statistically definitive memory-advantage proof.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_memory_advantage_demo_015.py -q
# 7 passed

python -m json.tool data\processed\runs\memory_advantage_demo_015\memory_backed_desert_recovery_i2v\i2v_review.json
# passed
```

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_memory_advantage_demo_015.py tests\test_kling_video_smoke.py tests\test_kling_video_request_plan.py tests\test_kling_video_task_recovery.py -q
# 23 passed

.\.venv\Scripts\python.exe -m compileall apps\cli narratocut\model_gateway narratocut\memory_advantage_demo_015.py narratocut\memory_advantage_demo_015_content.py
# passed

git diff --check
# passed with Windows line-ending warnings only
```

## Next Step

Use DEMO-015 to explain the mature experiment protocol:

```text
short user task -> stateless baseline
short user task -> memory-backed production with asset, scene, and feedback
memory reuse
```

For stronger visual evidence, do not keep retaking I2V from the same imperfect
keyframe. Wait for image quota and regenerate a cleaner source keyframe with the
shirt/waist anchor fixed, then rerun the same DEMO-015 protocol.
