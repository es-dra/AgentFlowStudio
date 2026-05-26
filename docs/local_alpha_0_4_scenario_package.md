# Local Alpha 0.4 Scenario Package

Date: 2026-05-27

Status: controller scenario package for `AFS-PROD-LOOP-001`.

This package fixes the shared scenario before runtime and Web implementation
work begins. It is the common input for `AFS-RUN-PACKAGE-001`,
`AFS-WEB-OPERATOR-002`, and the later `AFS-MEMORY-QUALITY-002` evidence pass.

AFS-RUN-PACKAGE-001 and AFS-WEB-OPERATOR-002 may run in parallel after this
package is integrated to `master`.

## Scenario

Named scenario:

```text
short-drama source video plus local script
  -> local ASR transcript
  -> script-aligned highlight selection
  -> real clip slicing
  -> final short package with BGM
  -> inspect / review / package report
  -> Web operator review and feedback
  -> memory candidate and second-pass context reuse
```

Target user job:

```text
A local operator needs to turn one real source video and a script into a
reviewable short-video package, decide whether the package is acceptable, and
carry accepted evidence into a second pass without hiding local-input,
provider, review, or memory boundaries.
```

Chosen workflow:

```text
workflows/video_script_to_finished_package_local_asr.yaml
```

This workflow is the 0.4 default because it exercises the product path most
directly: local video, local script, local ASR, script alignment, highlight
selection, real slicing, subtitles, BGM mixing, finished package manifest, and
package report.

## Local Input Policy

Required ignored local inputs:

| Path | Purpose | Commit policy |
|---|---|---|
| `data/raw/demo_real_video/input.mp4` | Source video for the scenario | ignored; never commit |
| `data/raw/demo_bgm/bgm.wav` | Local BGM track | ignored; never commit |
| `data/models/faster-whisper/` | Local ASR model cache | ignored; never commit |
| `data/processed/local_alpha_0_4/video_script_local_asr_input.json` | Operator-specific input bundle | ignored; never commit |

Committed reference inputs:

| Path | Purpose |
|---|---|
| `examples/demo_highlight/script.txt` | Script reference for highlight intent |
| `examples/demo_highlight/roi_config.json` | ROI constraints for slicing review |
| `examples/demo_bgm/bgm.metadata.example.json` | BGM metadata template |
| `examples/demo_asr/video_script_to_finished_package_local_asr_input.example.json` | Example shape for the ignored input bundle |

The local input bundle may be copied from the example and adjusted locally.
Do not commit the adjusted bundle because it can expose local media paths or
private project context.

Template for the ignored input bundle:

```json
{
  "video_path": "data/raw/demo_real_video/input.mp4",
  "source_video": "data/raw/demo_real_video/input.mp4",
  "script_path": "examples/demo_highlight/script.txt",
  "audio_extraction_mode": "ffmpeg",
  "asr_model": "small",
  "asr_device": "cpu",
  "asr_compute_type": "int8",
  "asr_download_root": "data/models/faster-whisper",
  "asr_beam_size": 1,
  "asr_vad_filter": true,
  "roi_config_path": "examples/demo_highlight/roi_config.json",
  "language": "zh",
  "max_highlights": 4,
  "max_clips": 4,
  "alignment_min_confidence": 0.03,
  "bgm_path": "data/raw/demo_bgm/bgm.wav",
  "bgm_metadata_path": "examples/demo_bgm/bgm.metadata.example.json",
  "output_clips_dir": "clips",
  "output_dir": "data/processed/runs/local_alpha_0_4_product_loop"
}
```

## Runbook

First run the read-only status check:

```powershell
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main alpha-smoke --json
```

Then, only when the ignored local inputs exist, run the scenario:

```powershell
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main run-workflow --workflow workflows/video_script_to_finished_package_local_asr.yaml --input data/processed/local_alpha_0_4/video_script_local_asr_input.json --output data/processed/runs/local_alpha_0_4_product_loop
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main inspect-run --run-dir data/processed/runs/local_alpha_0_4_product_loop
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main review-run --run-dir data/processed/runs/local_alpha_0_4_product_loop
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main package-report --run-dir data/processed/runs/local_alpha_0_4_product_loop
```

Optional release-readiness summary after a terminal local run:

```powershell
D:\Projects\AgentFlowStudio\.venv\Scripts\python.exe -m apps.cli.main delivery-readiness --run-dir data/processed/runs/local_alpha_0_4_product_loop --output data/reports/local_alpha_0_4_delivery_readiness
```

## Expected Output Artifacts

Runtime artifacts stay ignored under `data/processed/` or `data/reports/`.

Expected run directory:

```text
data/processed/runs/local_alpha_0_4_product_loop
```

Expected evidence files include:

- `run_manifest.json`
- `transcript.json`
- `script_highlight_alignment.json`
- `boundary_signal_manifest.json`
- `highlight_score_report.json`
- `selection_diagnostics.json`
- `clip_plan.json`
- `clip_plan_validation.json`
- `real_slice_manifest.json`
- `final_video_manifest.json`
- `subtitle_manifest.json`
- `audio_mix_manifest.json`
- `finished_package_manifest.json`
- `quality_report.json` from `inspect-run`
- `review_report.json` from `review-run`
- `package_report.md` from `package-report`

The Web lane may reference these paths in operator feedback, but it must not
persist browser state, upload files, scan directories automatically, or store
provider configuration.

## Blocked-State Rules

If any required ignored input is missing, `AFS-RUN-PACKAGE-001` should return
`BLOCKED` rather than creating substitute sample media or claiming product
acceptance.

The blocked handoff must list:

- exact missing paths;
- the command that was attempted or intentionally skipped;
- whether the repository state stayed clean except committed docs/handoff
  updates;
- whether `alpha-smoke --json` still reports the expected provider state;
- the next local setup action for the operator.

Missing local media, model cache, or BGM is not a product failure. It is a
local setup blocker.

## Acceptance Checklist

- [ ] The local input bundle exists only under ignored `data/processed/`.
- [ ] The source video, BGM, ASR model cache, and generated run outputs remain
      ignored and unstaged.
- [ ] The selected workflow is
      `workflows/video_script_to_finished_package_local_asr.yaml`.
- [ ] The terminal run either produces package evidence or records an
      actionable local-input blocker.
- [ ] `inspect-run`, `review-run`, and `package-report` evidence is linked from
      the runtime handoff when available.
- [ ] The Web operator path can point to the scenario, show the next action,
      refresh review/package evidence, and capture feedback.
- [ ] Feedback, memory candidate, promotion decision, context bundle, and
      second-pass prompt remain auditable and side-effect-free.
- [ ] Verification, human acceptance, business validation, provider smoke, and
      memory promotion are reported as separate states.

## Evidence Map

| Lane | Required output | Evidence path |
|---|---|---|
| Product scenario | Shared scenario and runbook | `docs/local_alpha_0_4_scenario_package.md` |
| Runtime package | Terminal run or actionable blocker | `docs/handoff/AFS-RUN-PACKAGE-001.md` |
| Web operator | Local operator path and browser-smoke notes | `docs/handoff/AFS-WEB-OPERATOR-002.md` |
| Memory quality | Evidence reuse trace or blocker | `docs/handoff/AFS-MEMORY-QUALITY-002.md` |
| Tracker | Integration state and branch hygiene | `TASK_TRACKER.md` |

## Parallel Dispatch

After this package lands on `master`, dispatch:

- `AFS-RUN-PACKAGE-001` in `codex/afs-run-package-loop`.
- `AFS-WEB-OPERATOR-002` in `codex/afs-web-operator-loop`.

These two lanes can run in parallel because their write scopes are separate.
`AFS-RUN-PACKAGE-001` owns runtime evidence and local-input blockers.
`AFS-WEB-OPERATOR-002` owns Web workbench behavior and browser smoke. Both may
read this scenario package. Either lane may make narrow corrections to this
runbook if real execution reveals a mismatch, but broader scenario changes
should stop parallel work and return to controller review.

Open `AFS-MEMORY-QUALITY-002` only after the runtime evidence shape is known.
Keep `AFS-POSTER-LIVE-002` optional and blocked unless local image-provider
environment is intentionally configured.

## Non-Claims

This scenario does not claim:

- hosted SaaS readiness;
- customer or market validation;
- mature editorial or viral quality;
- durable Memory runtime;
- vector store, database, or RAG quality;
- autonomous Router or skill runtime;
- provider cost-quality optimization;
- publishing or distribution integration;
- browser persistence or account state.
