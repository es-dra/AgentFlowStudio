# Local Alpha 0.4 Scenario Package

Date: 2026-05-27

Status: scenario package plus first runtime/Web evidence loop and
side-effect-free memory reuse review.

This package fixes the shared scenario before runtime and Web implementation
work begins. It is now also the common evidence index for completed
`AFS-RUN-PACKAGE-001`, integrated `AFS-WEB-OPERATOR-002`, and the next
`AFS-MEMORY-QUALITY-002` evidence pass.

AFS-RUN-PACKAGE-001 and AFS-WEB-OPERATOR-002 have completed their first
controller-side loop. AFS-MEMORY-QUALITY-002 now has a trace-only review
contract for the feedback-to-context path.

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
- `trace.json`
- `transcript.json`
- `script_highlight_alignment.json`
- `boundary_signal_manifest.json`
- `candidate_windows.json`
- `highlight_score_report.json`
- `selection_diagnostics.json`
- `highlight_plan.json`
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
- `clips/`
- `final_video.mp4`
- `final_video_with_bgm.mp4`

The Web lane may reference these paths in operator feedback, but it must not
persist browser state, upload files, scan directories automatically, or store
provider configuration.

Observed first real run evidence on this workstation:

```text
data/processed/runs/local_alpha_0_4_product_loop
```

The first real run reached workflow `success`; `inspect-run` passed with
`8 passed / 0 failed / 0 warnings`; `review-run` passed with
`42 passed / 0 failed / 0 warnings`; `package-report` wrote
`package_report.md`; and the final BGM video was 720x1280 at about 18.58
seconds. These artifacts remain ignored and must not be committed.

## Blocked-State Rules

If any required ignored input or local media tool is missing,
`AFS-RUN-PACKAGE-001` should return `BLOCKED` rather than creating substitute
sample media or claiming product acceptance.

Blocking checks include:

| Missing item | Blocker category |
|---|---|
| `data/raw/demo_real_video/input.mp4` | missing source video |
| `data/raw/demo_bgm/bgm.wav` | missing BGM audio |
| `data/models/faster-whisper/` | missing local ASR model cache |
| `data/processed/local_alpha_0_4/video_script_local_asr_input.json` | missing local input bundle |
| FFmpeg or FFprobe unavailable | missing local media tool |

The blocked handoff must list:

- exact missing paths;
- whether the missing item is local media, model cache, input bundle, or tool;
- the command that was attempted or intentionally skipped;
- whether the repository state stayed clean except committed docs/handoff
  updates;
- whether `alpha-smoke --json` still reports the expected provider state;
- the next local setup action for the operator.

Missing local media, model cache, or BGM is not a product failure. It is a
local setup blocker.

## Acceptance Checklist

- [x] The local input bundle exists only under ignored `data/processed/`.
- [x] The source video, BGM, ASR model cache, and generated run outputs remain
      ignored and unstaged.
- [x] The selected workflow is
      `workflows/video_script_to_finished_package_local_asr.yaml`.
- [x] The terminal run either produces package evidence or records an
      actionable local-input blocker.
- [x] `inspect-run`, `review-run`, and `package-report` evidence is linked from
      the runtime handoff when available.
- [x] The Web operator path can point to the scenario, show the next action,
      refresh review/package evidence, and capture feedback.
- [x] Feedback, memory candidate, promotion decision, context bundle, and
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
| Acceptance reconciliation | Pass/block/non-claim ledger | `docs/local_alpha_0_4_acceptance_reconciliation.md` |
| Tracker | Integration state and branch hygiene | `TASK_TRACKER.md` |

## Parallel Dispatch

Initial parallel dispatch rule:

AFS-RUN-PACKAGE-001 and AFS-WEB-OPERATOR-002 may run in parallel because their
write scopes are separate.

Initial parallel dispatch outcome:

- `AFS-RUN-PACKAGE-001`: completed after ignored local inputs were supplied.
- `AFS-WEB-OPERATOR-002`: integrated, with a follow-up fix so passed bridge
  input-check evidence overrides stale static setup blockers.

`AFS-RUN-PACKAGE-001` owned runtime evidence and local-input blockers.
`AFS-WEB-OPERATOR-002` owned Web workbench behavior and browser smoke. The
controller then reconciled their evidence in this package, the handoffs,
DEVLOG, and `TASK_TRACKER.md`.

Use `AFS-MEMORY-QUALITY-002` as the structural gate before any real second-pass
generation work. It proves traceability, not product quality improvement.
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
