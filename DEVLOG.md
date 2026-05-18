# DEVLOG

## 2026-05-19 - Phase 13.7 Finished Video Package Manifest

- Started `feature/phase-13-7-finished-video-package` from the merged Phase
  13.6 `master`.
- Added `workflows/final_video_package.yaml` as a narrow manifest-only
  workflow: existing final video artifacts -> `finished_package_manifest.json`.
- Added `narratocut/package_sop/` and `write_finished_package` workflow node to
  index the required final video plus optional subtitle-burned video,
  BGM-mixed video, cover image, and review report paths.
- Added `finished_package` inspect/review support so declared package assets
  are checked for manifest status and file existence.
- Added example input under `examples/demo_package/` that references ignored
  generated artifacts and does not commit real media.
- Kept this increment free of file copying, uploads, final assembly changes,
  subtitle burn-in, BGM mixing, cover export, remote providers, and Web UI.

## 2026-05-19 - Phase 13.6 BGM Mix Hardening

- Started `feature/phase-13-6-bgm-hardening` from the merged Phase 13.5
  `master`.
- Hardened `BGMMixConfig` so `bgm_volume` and `original_audio_volume` must stay
  between `0` and `1`.
- Added a `mix_strategy` option. The default remains `mix_with_original`, while
  `bgm_only` builds a BGM-only audio filter path for silent final videos.
- Added BGM inspect/review warnings for known FFmpeg stderr patterns such as
  `Non-monotonic DTS` and for output duration drift beyond the BGM tolerance.
- Split BGM review tests into a separate focused test file so the main workflow
  test file stays under the 300-line project preference.
- Kept this increment free of music libraries, licensing management, beat
  detection, fades, transitions, final-video assembly changes, subtitles,
  covers, remote providers, and Web UI.

## 2026-05-19 - Phase 13.5 Local BGM Mix

- Started `feature/phase-13-5-bgm-mix` from the merged Phase 13.4 `master`.
- Added `workflows/final_video_with_bgm.yaml` as a narrow local BGM mix
  workflow: existing `final_video.mp4` plus local `bgm.mp3` ->
  `final_video_with_bgm.mp4` and `audio_mix_manifest.json`.
- Added `narratocut/bgm_sop/` for FFmpeg BGM mix command construction,
  execution, failed-manifest writing, volume configuration, and output-name
  safety.
- Added `bgm_mix` inspect/review support so BGM runs are checked for manifest
  status, FFmpeg command/return code, safe relative output paths, output video
  presence, non-empty output size, and video stream presence when FFprobe is
  available.
- Added example input under `examples/demo_bgm/` that references ignored local
  media paths and does not commit real video or music assets.
- Kept this increment free of music libraries, licensing management, beat
  detection, fades, transitions, final-video assembly changes, subtitles,
  covers, remote providers, and Web UI.

## 2026-05-19 - Phase 13.4 Cover Export

- Started `feature/phase-13-4-cover-export` from the merged Phase 13.3
  `master`.
- Added `workflows/final_video_to_cover.yaml` as a narrow cover export
  workflow: existing `final_video.mp4` -> `cover.jpg` plus
  `cover_manifest.json`.
- Added `narratocut/cover_sop/` for FFmpeg single-frame command construction,
  execution, failed-manifest writing, cover timestamp selection, and output-name
  safety.
- Added `cover_export` inspect/review support so cover runs are checked for
  manifest status, FFmpeg command/return code, safe relative output paths,
  cover image presence, and non-empty output size.
- Added example input under `examples/demo_cover/` that references an ignored
  generated final-video path and does not commit real media.
- Kept this increment free of BGM, transitions, subtitle changes, final-video
  assembly changes, cover templates, text overlays, remote providers, video
  frame highlight selection, and Web UI.

## 2026-05-19 - Phase 13.3 Subtitle Burn-In

- Started `feature/phase-13-3-subtitle-burn-in` from the merged Phase 13.2
  `master`.
- Added `workflows/final_video_with_subtitles.yaml` as a narrow execution
  workflow: existing `final_video.mp4` plus existing `subtitles.srt` ->
  `final_video_with_subtitles.mp4` and `subtitle_burn_manifest.json`.
- Added `narratocut/subtitle_burn_sop/` for FFmpeg subtitle burn-in command
  construction, execution, failed-manifest writing, and output-name safety.
- Added `subtitle_burn` inspect/review support so subtitle-burn runs are
  checked for manifest status, FFmpeg command/return code, output video
  presence, non-empty output size, FFmpeg warning classification, and video
  stream presence when FFprobe is available.
- Added example input under `examples/demo_subtitles/` with a committed small
  `.srt` fixture and an ignored generated final-video path.
- Fixed workflow input bundle loading for UTF-8 BOM JSON files so PowerShell
  generated input bundles are parsed as structured workflow inputs instead of
  falling back to legacy `input_text_file` mode.
- Kept this increment free of subtitle generation, final-video assembly
  regeneration, slicing, BGM, covers, transitions, Web UI, remote providers,
  ASR behavior, and video-frame understanding.

## 2026-05-19 - Phase 13.2 Basic Subtitle Export

- Started `feature/phase-13-2-basic-subtitle-export` from the merged Phase
  13.1 `master`.
- Added `workflows/transcript_to_subtitles.yaml` as a narrow subtitle export
  workflow: timestamped `transcript.json` -> `subtitles.srt` plus
  `subtitle_manifest.json`.
- Added `narratocut/subtitle_sop/` for deterministic SRT formatting and
  subtitle manifest generation without FFmpeg, media re-encoding, or remote
  providers.
- Added the `subtitle_export` inspect/review profile so subtitle runs are
  checked for manifest status, subtitle file existence, cue count alignment,
  valid cue ranges, monotonic cue ordering, and non-empty text.
- Added example input under `examples/demo_subtitles/` with a committed text
  transcript fixture and no media dependency.
- Kept this increment free of subtitle burn-in, final-video regeneration, BGM,
  covers, transitions, Web UI, real ASR behavior, visual understanding, and
  remote provider calls.

## 2026-05-19 - Phase 13.1 Final Video Quality Hardening

- Started `feature/phase-13-1-final-video-quality-hardening` from the Phase
  12 completion point at `8347e30`.
- Hardened final-video inspection without changing assembly behavior:
  `final_video_manifest.json` remains the source of truth for generated output
  paths, and FFmpeg concat output is not regenerated differently.
- Added known FFmpeg stderr warning classification for final-video runs.
  `Non-monotonic DTS` is reported as a quality warning rather than a hard
  failure when FFmpeg exits successfully and FFprobe can read the output.
- Added final-video stream presence checking so a missing video stream is
  surfaced as a failed quality check.
- Made `review-run` clearer when `quality_report.json` is missing by telling
  users to run `inspect-run` before `review-run`.

## 2026-05-19 - Phase 12.2 Simple Video Assembly

- Added `workflows/clips_to_final_video.yaml` as the Phase 12 simple assembly
  workflow: existing `real_slice_manifest.json` plus `clips/` -> assembly plan
  -> FFmpeg concat -> `final_video.mp4` and `final_video_manifest.json`.
- Added `narratocut/assembly_sop/` for assembly-specific plan and concat logic
  so slicing remains separate from final-video assembly.
- Added `final_video` harness quality/review support for assembly artifacts,
  including final manifest status, final video existence, non-empty file size,
  and duration tolerance when FFprobe is available.
- Added an example input under `examples/demo_assembly/` that references an
  ignored generated run path rather than committing media.
- Kept this increment free of subtitles, BGM, transitions, covers, Web UI,
  remote providers, video-frame understanding, and new ASR behavior.

## 2026-05-19 - Phase 12.1B Video To Real Clips Composition

- Synced `master` to the merged Phase 12.1A PR and started
  `feature/phase-12-1b-video-to-real-clips`.
- Added `workflows/video_to_real_clips.yaml` as a composition smoke workflow
  that reuses the Phase 11 mock-ASR planning path and then executes the
  generated `clip_plan.json` through Phase 12.1 real slicing.
- Added the `video_real_clips` harness profile so `inspect-run` and
  `review-run` cover video/transcript artifacts, highlight/clip-plan artifacts,
  and real clip slicing artifacts in one run.
- Split real-clip quality checks into `narratocut/harness/real_clip_quality.py`
  and shared profile constants into `quality_profiles.py` so the generic
  quality entrypoint stays thin as Phase 12 adds execution-layer checks.
- Added `examples/demo_asr/video_to_real_clips_input.example.json` using mock
  ASR and the existing ignored local demo video path.
- Kept this increment free of real ASR, video-frame highlight detection, clip
  concatenation, subtitles, BGM, covers, Web UI, remote providers, and
  `final_video.mp4` export.

## 2026-05-19 - Phase 12.1 ClipPlan To Real Clips

- Added `workflows/clip_plan_to_real_clips.yaml` as the Phase 12.1 primary
  execution workflow: source video plus existing `clip_plan.json` -> metadata
  probe -> validation -> real slicing -> `real_slice_manifest.json` and
  `clips/`.
- Kept this phase scoped to ClipPlan execution. It does not run ASR, detect
  highlights, regenerate clip plans, concatenate clips, add subtitles, add BGM,
  create covers, call remote providers, or export `final_video.mp4`.
- Added `examples/demo_slicing/clip_plan_to_real_clips_input.example.json` and
  a small `clip_plan.example.json`; the example references an ignored local
  video path and does not commit real media.
- Extended the real clip inspection/review path with a `real_clips` profile
  that reuses the existing real-video artifact checks without requiring
  transcript, highlight, or audio artifacts.
- Enriched `real_slice_manifest.json` with source video, clip plan path, clips
  directory, FFmpeg command, return code, stdout, and stderr so later assembly
  phases can inspect the execution result.
- Deferred `video_to_real_clips.yaml` to Phase 12.1B unless a follow-up needs a
  separate composition smoke workflow.

## 2026-05-18 - Phase 11.7 Video Artifact Review Hardening

- Started `feature/phase-11-7-video-artifact-review` from the merged Phase
  11.6 `master` after syncing the branch and deleting the completed Phase 11.6
  branch locally and on `origin`.
- Added Phase 11 video artifact harness profiles for `mock_asr_transcript`,
  `real_asr_transcript`, `video_highlight_clip_plan`, and
  `real_asr_highlight_clip_plan`.
- `inspect-run` now recognizes Phase 11 audio/transcript artifacts and writes
  summaries for audio extraction status, transcript provider, segment count,
  timestamp validity, monotonic segment order, and text presence.
- `review-run` now adds a `video_artifacts` section for Phase 11 profiles,
  including audio manifest checks, Transcript schema checks, ASR provider
  metadata checks, source-segment alignment checks for video-to-highlight runs,
  and obvious API secret value leakage checks for explicit real-ASR runs.
- Video-to-highlight runs still include the existing `highlight_artifacts`
  section, so HighlightPlan and ClipPlan review remains shared with Phase 10.
- Kept this increment free of new workflows, new product CLI commands, real
  slicing, final assembly, subtitles, BGM, Web UI, video-frame highlight
  detection, and default remote ASR calls.

## 2026-05-18 - Phase 11.6 Real-ASR Video-to-ClipPlan Workflow

- Synced local `master` to the merged Phase 11.5 PR and deleted the completed
  `feature/phase-11-5-real-asr-workflow` branch locally and on `origin`.
- Started `feature/phase-11-6-real-asr-highlight-clip-plan` from the latest
  `master`.
- Added `workflows/video_to_highlight_clip_plan_real_asr.yaml`, which composes
  explicit OpenAI-compatible ASR with the Phase 10 deterministic highlight
  detection, ROI ranking, and ClipPlan generation path.
- Added an example input bundle under `examples/demo_asr/` that references an
  API-key environment variable name without committing secrets.
- Kept this increment free of video-frame highlight detection, real slicing,
  clip generation, final assembly, subtitles, BGM, Web UI, and new product CLI
  commands.

## 2026-05-18 - Phase 11.5 Explicit Real-ASR Workflow

- Synced local `master` to the merged Phase 11.3/11.4 PR and deleted the
  completed `feature/phase-11-3-4-audio-asr-providers` branch locally and on
  `origin`.
- Started `feature/phase-11-5-real-asr-workflow` from the latest `master`.
- Added workflow node `transcribe_audio_openai_compatible`, which wires the
  optional OpenAI-compatible ASR provider into the workflow engine.
- Added `workflows/video_to_transcript_real_asr.yaml` as an explicit remote-ASR
  path that stops at `transcript.json`.
- Added an example input bundle that uses an API-key environment variable name
  rather than committing any secret.
- Kept default demo workflows on mock ASR and kept this increment free of
  highlight detection, ClipPlan generation, real slicing, final assembly,
  subtitles, BGM, Web UI, and new product CLI commands.

## 2026-05-18 - Phase 11.3/11.4 Audio Extraction and ASR Provider Contracts

- Started `feature/phase-11-3-4-audio-asr-providers` from the merged Phase 11.2
  `master`.
- Strengthened real FFmpeg audio extraction artifacts so `audio_manifest.json`
  records execution status, command arguments, return code, stdout, and stderr.
- Kept mock extraction available and explicitly marked as not executing FFmpeg.
- Added an optional `OpenAICompatibleASRProvider` adapter behind
  `NARRATOCUT_ALLOW_REMOTE_ASR=true`.
- Kept default workflows on fixture-backed mock ASR; no workflow now calls a
  remote ASR provider by default.
- Kept this increment free of video-frame highlight detection, real slicing,
  final assembly, subtitles, BGM, Web UI, and new product CLI commands.

## 2026-05-18 - Phase 11.2 Mock ASR Video-to-ClipPlan Workflow

- Synced local `master` to the merged Phase 11.1 PR and deleted the completed
  `feature/phase-11-video-to-transcript` branch locally and on `origin`.
- Started `feature/phase-11-2-video-to-highlight-clip-plan` from the latest
  `master`.
- Added `workflows/video_to_highlight_clip_plan.yaml`, which composes the
  Phase 11.1 mock-ASR transcript workflow with the Phase 10 deterministic
  highlight detection, ROI ranking, and highlight-to-ClipPlan generation path.
- Added a demo input bundle under `examples/demo_asr/` for the composed
  video-to-highlight-clip-plan workflow.
- Kept this increment free of real ASR providers, video-frame highlight
  detection, FFmpeg slicing, real clip generation, final-video assembly,
  subtitles, BGM, Web UI, and new product CLI commands.

## 2026-05-18 - Phase 11.1 Video-to-Transcript Foundation

- Synced local `master` to the merged Phase 10.7 PR and deleted the completed
  `feature/phase-10-7-highlight-artifact-review` branch locally and on
  `origin`.
- Started `feature/phase-11-video-to-transcript` from the latest `master`.
- Added `narratocut.audio_sop` for the video-to-audio artifact contract,
  including FFmpeg command construction and deterministic mock extraction for
  tests and offline workflow smoke runs.
- Added `narratocut.asr_sop` with an adapter protocol, fixture-backed
  `MockASRProvider`, and transcript normalization into the existing
  `Transcript` schema.
- Added `workflows/video_to_transcript.yaml`, which runs
  `load_video -> extract_audio -> transcribe_audio_mock -> write_transcript`.
- Added `examples/demo_asr/` with a mock ASR transcript fixture and workflow
  input bundle.
- Kept this increment free of video-frame highlight detection, Phase 10
  highlight workflows, ClipPlan generation, FFmpeg slicing, real ASR providers,
  remote LLM calls, clip assembly, subtitles, BGM, Web UI, and new product CLI
  commands.

## 2026-05-18 - Phase 10.7 Highlight Artifact Review

- Synced local `master` to the merged Phase 10 PR and deleted the completed
  `feature/phase-10-highlight-detection` branch locally and on `origin`.
- Started `feature/phase-10-7-highlight-artifact-review` from the latest
  `master`.
- Added a highlight artifact harness profile for `highlight_plan` and
  `highlight_clip_plan` quality profiles.
- `inspect-run` now reports Phase 10 artifact summaries for
  `highlight_plan.json`, including input mode, highlight count, highlight type
  distribution, timestamp presence, ranking factor presence, and score ranges.
- `review-run` now adds a `highlight_artifacts` section that checks
  script-only timestamp boundaries, timestamped transcript ranges, ranking
  factors, highlight IDs, source segment IDs, clip segment metadata, and
  highlight-to-clip ordering.
- Kept this increment free of new workflow nodes, new CLI commands, ASR,
  raw-video analysis, FFmpeg execution, LLM calls, clip assembly, subtitles,
  BGM, and Web UI.

## 2026-05-18 - Phase 10.1/10.2 Highlight Contracts

- Started Phase 10 on `feature/phase-10-highlight-detection` after Phase 9
  was merged into `master`.
- Added `HighlightSegment` and `HighlightPlan` contracts for `script_only`
  and `timestamped_transcript` highlight planning.
- Added `TranscriptSegment` and `Transcript` contracts for externally
  supplied timestamped transcript input. Phase 10 consumes transcripts; it does
  not generate them through ASR.
- Enforced the key Phase 10 boundary: `script_only` highlight plans must not
  carry timestamps, while `timestamped_transcript` plans require timestamps on
  every highlight.
- Added `examples/demo_highlight/` input examples for script-only and
  timestamped-transcript workflows, plus a reusable ROI config.
- Kept this increment free of detector logic, ROI ranking, ClipPlan generation,
  workflow nodes, CLI commands, remote LLM calls, ASR, Web UI, subtitles, BGM,
  and final-video assembly.

## 2026-05-18 - Phase 10.3 Deterministic Highlight Detector

- Added `narratocut.highlight_sop` as the local highlight-detection module.
- Added `DeterministicHighlightDetector` plus convenience functions for
  script-only and timestamped-transcript inputs.
- The detector is a stable, offline baseline. It uses simple rules for hook,
  conflict, insight, and CTA candidates; it does not call the model gateway,
  remote LLMs, ASR, OCR, FFmpeg, or any network service.
- Script-only detection writes untimed `HighlightPlan` objects. Timestamped
  transcript detection preserves `TranscriptSegment` time ranges and source
  segment IDs.
- Kept ROI ranking, ClipPlan generation, workflow nodes, CLI commands, and
  real slicing integration out of Phase 10.3. Those remain later Phase 10
  increments.

## 2026-05-18 - Phase 10.4 ROI-aware Highlight Ranking

- Added `ROIHighlightRanker` and `rank_highlights_by_roi(...)` under
  `narratocut.highlight_sop`.
- Ranking returns a new `HighlightPlan` instead of mutating detector output,
  so later workflows can keep raw and ranked plans separate.
- Added transparent local ranking factors under
  `highlight.metadata.ranking_factors`, including base score, confidence,
  content goal, target platform, priority boosts, matched rules, and
  `final_score`.
- Kept `highlight.score` as the detector score. ROI ranking uses
  `metadata.ranking_factors.final_score` for ordering.
- Added user-facing ROI tags such as `goal:*`, `platform:*`, and
  `priority:*` without discarding detector-provided tags.
- Kept this increment free of performance prediction, virality prediction,
  ClipPlan generation, workflow nodes, CLI commands, remote LLM calls, ASR, and
  final-video assembly.

## 2026-05-18 - Phase 10.5 Highlight-to-ClipPlan Generation

- Added `HighlightClipPlanGenerator` and
  `generate_clip_plan_from_highlights(...)` under `narratocut.highlight_sop`.
- The generator accepts only `timestamped_transcript` `HighlightPlan` objects
  and rejects `script_only` plans instead of inventing timestamps.
- Generated one executable `ClipPlan` with one `ClipSegment` per selected
  highlight, preserving the incoming ranked order.
- Required caller-provided `source_video` for generated segments so the output
  can enter Phase 9 validation and real slicing when the caller supplies a real
  video path.
- Preserved highlight evidence in segment metadata, including highlight ID,
  type, score, confidence, ROI tags, source transcript segment IDs, and ranking
  factors.
- Kept this increment free of FFmpeg execution, workflow nodes, CLI commands,
  ASR, remote LLM calls, clip assembly, subtitles, BGM, and final-video export.

## 2026-05-18 - Phase 10.6 Highlight Workflow Integration

- Added highlight workflow nodes for loading scripts/transcripts, detecting
  highlights, ROI ranking, generating ClipPlan from timestamped highlights, and
  writing highlight/clip plan artifacts.
- Added `workflows/script_to_highlight_plan.yaml`, which writes a ranked
  `highlight_plan.json` and intentionally does not write `clip_plan.json`.
- Added `workflows/transcript_to_highlight_clip_plan.yaml`, which writes a
  ranked `highlight_plan.json` plus executable `clip_plan.json`.
- Kept Phase 10.6 on the existing `ncut run-workflow` path instead of adding a
  product-specific CLI command.
- Updated highlight examples with `max_highlights` and an optional
  `source_video` placeholder for transcript-driven clip plan generation.
- Kept this increment free of ASR, raw-video highlight detection, FFmpeg
  execution, clip assembly, subtitles, BGM, Web UI, and final-video export.

## 2026-05-18 - Phase 9 ROI-aware Real Video Workflow Closure

- Phase 9 establishes the real video execution foundation: it runs a provided
  `ClipPlan` against a local video and produces inspectable/reviewable
  artifacts. It intentionally does not include automatic highlight detection,
  ASR, clip assembly, subtitles, BGM, Web UI, or agent runtime.
- Added a real-video workflow mode with explicit `workflow_mode` and
  `quality_profile` fields in `run_manifest.json`.
- Added `ROISettings`, `VideoMetadata`, and `ClipPlanValidationReport`
  contracts for one local video, one ROI config, one `ClipPlan`, and many
  segments.
- Added FFmpeg/FFprobe path resolution through CLI/env/config and structured
  `ncut ffmpeg-check --json` output.
- Added `workflows/real_video_roi_to_clips.yaml` plus example input JSON files
  under `examples/demo_real_video/` without committing real media.
- Kept `run-workflow`, `inspect-run`, and `review-run` separated:
  `run-workflow` writes execution artifacts, `inspect-run` writes
  `quality_report.json`, and `review-run` writes `review_report.json`.
- Added real-video inspection and review recommendations for FFmpeg/FFprobe,
  validation, and slicing failures.
- Extended the static tool catalog with implemented Phase 9 real-video nodes
  and added optional FFprobe-based clip duration tolerance checks.
- Honored the structured input bundle's relative `output.clips_dir` while
  keeping `clips` as the default output folder.
- Validated the real-video success path with a local ignored demo mp4:
  FFmpeg/FFprobe were ready, `real_slice_manifest.json` reported one succeeded
  10-second clip, `inspect-run` reported `11 passed / 0 failed / 0 warnings`,
  and `review-run` reported `16 passed / 0 failed / 0 warnings`.
- Follow-up direction: Phase 10 should address script/timestamped transcript
  highlight detection, Phase 11 should add video ASR to timestamped transcript,
  and Phase 12 should assemble clips into a final video.

## 2026-05-16 - Phase 4 Model Gateway Lite

- Added a lightweight model gateway layer with config loading, provider errors, `ModelGateway`, and a minimal OpenAI-compatible provider.
- Kept existing ROI and workflow commands on the default mock path; no CLI command requires API keys or network access.
- Added `NARRATOCUT_ALLOW_REMOTE_LLM=true` as an explicit provider-side guard before OpenAI-compatible HTTP calls.
- Updated example model and environment configuration without storing secrets.
- Verification: `pytest` passed with 37 tests, `compileall` passed, and the mock CLI/workflow commands still generated local ignored artifacts under `data/processed/runs/`.

## 2026-05-16 - Phase 5 ClipPlan + Slicing MVP

- Added deterministic `ShortVideoScript -> ClipPlan` planning and mock slicing that writes `.txt` placeholder clips plus `slice_manifest.json`.
- Kept Phase 5 free of FFmpeg, real media reads, real `.mp4` generation, network calls, Web/API, database, queues, and complex workflow DAGs.
- Added CLI commands `generate-clip-plans` and `mock-slice`; CLI remains a thin wrapper over `narratocut.slicing_sop`.
- Verification: `pytest` passed with 41 tests, `compileall` passed, and the Phase 5 CLI chain generated `clip_plans.json`, `slice_manifest.json`, and 3 ignored mock clip files under `data/processed/runs/demo_phase5/`.

## 2026-05-16 - Phase 6 Workflow Full Mock Pipeline

- Added workflow nodes `generate_clip_plans` and `mock_slice`, reusing the Phase 5 slicing SOP without FFmpeg or real media access.
- Added `workflows/mock_text_to_slices.yaml` for the full mock chain: text -> hooks -> scripts -> clip_plans -> mock clips.
- Updated workflow docs with the full mock run command and expected artifacts.
- Verification: full mock workflow test passed and CLI run generated `hooks.json`, `scripts.json`, `clip_plans.json`, `slice_manifest.json`, and 3 ignored `.txt` mock clip files.

## 2026-05-16 - Phase 7 Real Slicing Design + FFmpeg Probe

- Added `ffmpeg_probe` for structured FFmpeg availability checks without requiring FFmpeg during tests.
- Added `real_slicer` command-contract helpers that build, but do not execute, minimal FFmpeg slice commands.
- Added `ffmpeg-check` CLI as an informational local probe; it does not alter mock workflows or require real video assets.
- Added real slicing design notes documenting the current mock boundary and future FFmpeg input/output contract.

## 2026-05-17 - Phase 7.5 Run Contract + Harness Inspection Baseline

- Added standardized run contract artifacts for workflow runs: `run_manifest.json` and `trace.json`.
- Added harness quality checks and run inspection that write `quality_report.json` without moving quality decisions into workflow nodes.
- Added `ncut inspect-run --run-dir ...` to inspect generated workflow run directories and return a non-zero exit code when quality checks fail.
- Documented the run contract boundary in `docs/run_contract.md` and updated workflow/README guidance.
- Verification: `pytest` passed with 57 tests, `compileall` passed, `ncut version` returned `0.1.0`, the full mock workflow generated the run contract artifacts, `inspect-run` reported `12 passed / 0 failed / 0 warnings`, and `git diff --check` passed with line-ending warnings only.

## 2026-05-17 - Phase 7.6 Agent Reviewer Contract

- Added a read-only harness reviewer that reads an existing workflow run and writes `review_report.json`.
- Added `ncut review-run --run-dir ...` for agent-readable review report generation with `passed`, `warning`, and `failed` status aggregation.
- Kept the reviewer outside workflow execution: it does not rerun workflows, call FFmpeg, call remote LLMs, or modify source run artifacts.
- Documented the reviewer contract in `docs/agent_reviewer_contract.md`.

## 2026-05-17 - Phase 7.7 Workflow Plan Draft

- Added a static workflow planner that converts workflow YAML and a planned input file into `workflow_plan.json`.
- Added `ncut draft-plan --workflow ... --input ... --output ...` without executing workflow nodes or creating run artifacts.
- Used `configs/tool_catalog.yaml` only to enrich plan step purpose text; workflow YAML remains the source of step order and outputs.
- Kept planning separate from execution, FFmpeg, remote LLMs, Web/API, database, queue, and agent runtime.
- Documented the planning contract in `docs/workflow_plan_contract.md`.

## 2026-05-17 - Phase 8 Minimal Real Slicing PoC

- Added standalone `slice_clip_plans_real(...)` execution for local FFmpeg slicing from validated clip plans.
- Added `ncut slice-real --video ... --clip-plans ... --output ...` as a separate PoC command; it does not replace the default mock workflow.
- Added `real_slice_manifest.json` output with passed/failed status, clip paths, durations, and errors.
- Kept tests independent from installed FFmpeg by mocking `subprocess.run`; missing FFmpeg returns a clear failed manifest.
- Updated tool contracts so `slice_real` requires FFmpeg, executes an external process, is not safe for automatic agent execution, and requires human review.
