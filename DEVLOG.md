# DEVLOG

## 2026-05-26 - Web UI Branch Baseline Repair

- Repaired the dedicated Web UI worktree after the repository rename left its
  `.git` pointer aimed at the removed `D:\Projects\NarratoCut` checkout.
- Verified the branch as a preserved parallel lane, not a direct merge
  candidate: it is useful Web UI work, but it still trails current
  `master` and must be rebased or replayed before integration.
- Sealed the current M3.1 production workbench slice for remote backup:
  modularized Web UI code, local bridge, production readiness workspace,
  supervised local demo path, and bridge-backed run observation.
- Verification: targeted Web UI tests `41 passed`, full branch pytest
  `374 passed`, CLI help/version passed, JS syntax checks passed,
  `compileall` passed, and `git diff --check` passed.
- Environment note: this old worktree currently ran verification with
  Python 3.13.5; future integration into `master` should rerun the same matrix
  with the project-preferred Python 3.12 environment.

## 2026-05-22 - Web UI Production Workbench Modularization

- Closed the remaining module-size debt in the supervised production workbench
  slice.
- Split DOM reference collection and static copy binding into
  `apps/web/app-elements.js`, keeping `apps/web/app.js` focused on UI
  orchestration and rendering flow.
- Split review/run feedback event wiring into `apps/web/feedback-wiring.js`
  so feedback JSON construction and copy actions no longer live in the main
  app entrypoint.
- Split product-facing workflow profile text and readiness hints into
  `apps/web_bridge/workflow_profiles.py`, keeping the local bridge focused on
  HTTP request handling and workflow runner integration.
- Verification: JS syntax checks passed, bridge/Python compile passed, and
  focused production Web UI tests passed.

## 2026-05-22 - Web UI Production Readiness Workspace

- Added a production readiness wizard to Production Mode: production target,
  local environment, input diagnostics, and next action now sit above the run
  workspace.
- Extended bridge workflow profiles with product-facing display names,
  readiness hints, and review focus fields while still reading workflows from
  `workflows/*.yaml`.
- Extended input diagnostics with missing-reference categories, summaries, and
  next actions so missing video/BGM/script/config paths can be shown as
  actionable blockers.
- Reorganized Production Mode toward a task-first run workspace: current task,
  blocker, next action, deliverable, step timeline, and artifact timeline are
  still visible, but readiness now leads the workflow.
- Added a Production Mode video review panel. It only previews explicitly
  selected local video files and only weak-matches artifact file names; it does
  not auto-read manifest paths or scan directories.
- Renamed supervision controls to honest first-slice actions: confirm continue,
  record pause note, record rerun suggestion, and record change request. The UI
  no longer implies true pause/resume or step-level rerun.
- Added run-level feedback JSON copy for Production Mode. It includes run,
  workflow, decision, risk category, reviewer note, and optional video timestamp
  while still avoiding file writes, uploads, browser persistence, or
  `feedback.jsonl` mutation.
- Verification so far: production focused tests passed, bridge compile passed,
  and production JS syntax checks passed.

## 2026-05-22 - Web UI Supervised Production Demo Path

- Added Web UI workflow profiles for Production Mode so the UI can distinguish product workflows from runnable local demo workflows.
- Added quick actions for local demo and complete product in the Production Mode workflow selector.
- Kept video_to_finished_package_local_asr visible as the complete product path while showing its current blockers, including missing local ASR dependencies on this machine.
- Added a runnable mock_text_to_slices demo path that needs no media, FFmpeg, or ASR and can verify the bridge-backed supervision loop end-to-end.
- Fixed a real browser smoke issue where the workflow select value and internal production state could diverge after quick switching.
- Split Production Mode UI code into production-render.js and production-workflows.js; production-mode.js is back under the 300-line target.
- Browser smoke on http://127.0.0.1:8769/ with bridge http://127.0.0.1:8787 verified: select local demo, generate plan, run mock_text_to_slices to success, list artifacts, and refresh review to passed.
- Boundary kept: no SaaS, no cloud upload, no remote provider call, no database, no directory scanning, no true pause/resume, and no step-level rerun yet.

## 2026-05-21 - Web UI M3 Supervised Local Production Bridge

- Added the first supervised Production Mode for the Web UI branch while preserving the existing Review Mode artifact viewer.
- Added apps/web_bridge, a small stdlib local HTTP bridge bound to 127.0.0.1 by default. It intentionally avoids FastAPI, database, upload, provider configuration, SaaS accounts, and remote execution.
- Added ncut web-bridge as the explicit local startup command for browser production mode.
- Bridge endpoints: GET /health, GET /workflows, POST /plans, POST /runs, GET /runs/{id}, and POST /runs/{id}/review.
- Added Web UI Production Mode with workflow selection, explicit input/output paths, bridge health, current task, next action, blockers, step timeline, artifact timeline, execution log, and human supervision controls.
- Added bridge_status.json progress snapshots and a WorkflowRunner progress callback so Production Mode can show pending/running/success/failed step states while a local run is still in progress.
- Added browser-side polling of GET /runs/{id} after starting a run. The UI disables duplicate run/plan/review actions during an active run and records supervision button intent in memory for the current page session.
- Added input_check diagnostics to plan/run responses so the workbench can flag missing referenced local media/config files before users waste a run on an unavailable input bundle.
- Added optional local ASR dependency reporting in bridge health. On this machine faster_whisper / ctranslate2 are not installed, so full local-ASR product workflows are correctly shown as blocked even though mock workflows and Review Mode remain usable.
- Boundary change: Review Mode remains static/read-only/no-network. Production Mode allows local fetch only to http://127.0.0.1:8787.
- Current limitation: supervision buttons make intent visible but do not yet implement true pause/resume, step-level rerun, or run-note persistence.


## 2026-05-21 - Web UI M1.4 Production Review Workbench IA

- Reworked the static Web UI information architecture from an artifact-first
  dashboard into a production-oriented local review workbench.
- Removed the large hero-first surface and replaced it with a compact top bar
  for delivery status, metrics, language toggle, and explicit local file
  selection.
- Added a left review path rail and recommended file sets grouped by package
  run, upstream evidence, and delivery handoff. This addresses the real-smoke
  finding that useful review evidence often spans multiple run directories.
- Re-centered the main stage on delivery overview, explicit local video
  preview, asset check, and report review. Artifact contract details now live
  in the right-side `Contract Inspector` instead of dominating the default
  view.
- Kept the same local-only boundary: no upload, no persistence, no backend, no
  directory scanning, no manifest path auto-read, and no CLI/API execution from
  the Web UI.

## 2026-05-21 - Web UI Local Review Workbench Expansion

- Continued local-only development on `codex/narratocut-web-ui` without pushing
  the branch or merging latest `master`, per the current branch cadence.
- Polished the M1.2 workbench into M1.2.1: reduced the hero height, switched
  major panel titles to Chinese, changed the metric strip to acceptance
  language (`已选文件`, `参与验收`, `风险提示`, `解析错误`), and stopped showing
  missing recommended artifact warnings in the empty state.
- Expanded the static viewer's read-only artifact universe for M1.3:
  `selection_diagnostics.json`, `highlight_score_report.json`,
  `candidate_windows.json`, `clip_plan.json`, `real_slice_manifest.json`,
  `final_video_manifest.json`, `subtitle_manifest.json`,
  `audio_mix_manifest.json`, and `cover_manifest.json`.
- Added normalized Evidence Map, Risk Ledger, and Asset Ledger view-models so
  the UI can inspect local artifact relationships, warning/failure signals, and
  media asset paths without reading raw schemas directly in the render layer.
- Added explicit local video preview for user-selected `.mp4`, `.webm`, and
  `.mov` files only. The viewer uses temporary object URLs and revokes the
  previous URL when switching; it still does not follow manifest paths or scan
  directories.
- Added M2 feedback event copy as a static browser-only utility:
  `feedback_event` JSON can be generated and copied, with textarea fallback
  when Clipboard is unavailable. It does not write files, upload, persist state,
  or call a backend.
- Split more static browser logic into small modules:
  `artifact-contracts.js`, `artifact-values.js`, `artifact-ledgers.js`,
  `video-preview.js`, and `feedback-event.js`, keeping `normalizeWorkspace()`
  as the single UI view-model boundary.
- External references remained conceptual only: W&B-style metadata/lineage,
  LangSmith-style run debugging, Langfuse-style scores/comments, and Frame.io /
  Workfront-style review status informed the workbench shape. No SaaS,
  account, cloud storage, permission, backend, collaboration system, runtime
  code, or dependency was added.
- Boundary kept: no React/Vite/Next, no backend, no CLI/API execution, no
  provider calls, no upload, no persistence, no automatic directory scanning,
  and no manifest path auto-read.

## 2026-05-21 - Web UI Real Artifact Smoke and M1.3.1 Rendering Fixes

- Ran a local real-media smoke with generated ignored media under
  `data/raw/webui_smoke/` and ignored run artifacts under
  `data/processed/runs/webui_smoke_*`. These artifacts are intentionally not
  committed.
- Exercised the workflow chain that the static viewer is expected to inspect:
  `video_to_real_clips`, `clips_to_final_video`, `transcript_to_subtitles`,
  `final_video_with_subtitles`, `final_video_to_cover`,
  `final_video_with_bgm`, `final_video_package`, `inspect-run`, `review-run`,
  `package-report`, and `delivery-readiness`.
- Real smoke result: package inspect passed with warnings, review reported
  warning status, and delivery readiness failed because the final package run
  did not itself contain `highlight_score_report.json` or
  `selection_diagnostics.json`. That is useful validation data for the Web UI
  risk ledger rather than a Web UI failure.
- Added an OCR candidate-scoring smoke run to produce real
  `candidate_windows.json`, `highlight_score_report.json`, and
  `selection_diagnostics.json` artifacts for Web UI normalization checks.
- Fixed M1.3.1 rendering gaps found by the real artifacts:
  `package_manifest.evidence` entries now appear in Evidence Map, nested
  `review_report.sections[].checks` warnings and
  `delivery_readiness.runs[].failures/warnings` now appear in Risk Ledger, and
  multiple Markdown reports can be switched with report tabs.
- Boundary kept: the Web UI still does not execute workflows. The real smoke
  was performed from CLI only to validate the viewer against actual artifacts.

## 2026-05-21 - Web UI M1.2 Chinese Workbench Polish

- Merged the latest `origin/master` into `codex/narratocut-web-ui` after the
  NarratoStudio mainline landed, keeping the open Web UI PR on a non-rebased
  history.
- Upgraded the static viewer presentation from an English artifact dashboard to
  a Chinese-first local review workbench. Human-facing copy now defaults to
  Chinese while artifact names, contract types, schema fields, and machine keys
  remain English.
- Added an in-memory language toggle between Chinese and English. It does not
  use `localStorage`, IndexedDB, cookies, or any persistence mechanism; refresh
  returns to the Chinese default.
- Added a top metric strip and refined the dark workbench styling with
  restrained grid/scan-line texture, cyan/lime/amber/red status colors, and
  denser inspection panels inspired by the local Zhike reference.
- Split static Web UI modules so `artifact-workspace.js` remains normalization
  and view model logic, `app.js` handles orchestration, `ui-copy.js` owns zh/en
  copy, and `render-helpers.js` owns status labels and small rendering helpers.
- Boundary kept: no video preview, no feedback event, no directory scanning, no
  manifest path reads, no CLI/API bridge, no backend, no React/Vite/Next, no
  upload, and no persistence.

## 2026-05-20 - M1.1 Web UI Release Candidate Hardening

- Hardened the static `apps/web` artifact viewer as a read-only, local-only release candidate slice. The branch still has no backend, no upload, no persistence, no CLI/API bridge, no workflow execution, no feedback writing, and no local video preview.
- Strengthened `artifact-workspace.js` as the single normalization boundary for UI rendering. Selected files are now classified as `known_contract`, `unknown_json`, `unsupported_file`, or invalid, and only normalized `known_contract` artifacts participate in summary/inspector views.
- Kept `package_manifest` as the internal canonical name while continuing to accept both `package_manifest.json` and `finished_package_manifest.json`.
- Treated missing `schema_version` as a warning rather than a fatal error, matching current repo artifacts such as `run_manifest.json` and `quality_report.json`.
- Added a sanitized real-shape fixture under `tests/fixtures/web_static_artifact_viewer/product_run/`, based on the local `final_video_package` workflow artifact structure. The fixture keeps run/package/quality/review/delivery/report contract fields, uses relative placeholder media paths, and commits no media files or generated run directories.
- Updated inventory rendering to show file name, artifact type, artifact class, schema version/status, parse status, source role, summary inclusion, and schema warnings from the normalized view model.
- Kept Markdown report preview safe by rendering escaped text only; the fixture includes a `<script>` probe that must display as text.
- Documented that Zhike remains only a UX reference for a dark workbench, status visualization, and artifact panels. No Zhike runtime code, business logic, provider code, database, routing, or dependencies are included.
- Follow-up risks remain out of scope for this PR: M1.5 explicit local video preview, M2 feedback event copy/export, and M3 Run Review Workspace. Those should stay on later branches.

## 2026-05-20 - Web UI M1 Static Artifact Viewer

- Started `codex/narratocut-web-ui` from the v0.1.0 closeout baseline as a
  narrow, mergeable Web UI branch.
- Added a static, read-only `apps/web` artifact viewer with no backend, no
  framework build chain, no provider calls, no upload, and no persistence.
- Added a local file-picker contract for selected artifacts only. The viewer
  does not scan run directories, does not follow manifest paths, and does not
  write feedback or generated files.
- Added artifact detection and normalization for `run_manifest.json`,
  `finished_package_manifest.json`, `package_manifest.json`,
  `quality_report.json`, `review_report.json`, `delivery_readiness.json`,
  `package_report.md`, and `delivery_readiness.md`.
- Normalized `finished_package_manifest.json` and `package_manifest.json` under
  the internal `package_manifest` concept while preserving the selected file
  name in the UI.
- Kept `quality_report.json` as an optional trust artifact because the current
  repo documents and generates it through `inspect-run`.
- Rendered Markdown reports as escaped text instead of executable HTML.
- Zhike boundary: used only as visual and interaction reference for a dark
  workbench, status rail, artifact inventory, and inspector layout. No Zhike
  runtime code, business logic, provider adapters, routes, database code, or
  dependencies are included.
- Follow-up boundary: local video preview, feedback event copy/export, and a
  richer workbench shell are deferred to later slices.
- Implementation note: `apps/web/app.js` is intentionally a single static
  browser module for M1 because this branch avoids a bundler/build chain. If
  the viewer grows beyond this read-only slice, split detection,
  normalization, and rendering into separate modules before adding features.

## 2026-05-20 - NarratoCut v0.1.0 Delivery Closeout

- Synced `master` to PR #38, confirmed the old delivery-hardening branch had an
  identical tree to `origin/master`, deleted the stale remote branch, and
  started `codex/phase-1-v0-1-delivery-closeout`.
- Repositioned NarratoCut as the distribution-side short video highlight
  workflow module of AgentFlow Studio while keeping the repo and local folder
  named `NarratoCut`.
- Extended `run_manifest.json` with an additive `artifact_index` while keeping
  the existing `artifacts` string map backward-compatible for current tests,
  reviewers, and workflows.
- Extended `review_report.json` with `quality_level` and `delivery_status` so
  agents and future UI code can read handoff state without inferring it only
  from raw check counts.
- Added v0.1.0 delivery docs: agent usage guide, delivery checklist, golden
  sample path, project manifest contract, feedback contract, platform profile
  contract, and asset lifecycle.
- Added contract examples with `schema_version`: project manifest JSON,
  feedback JSONL, and Douyin/Xiaohongshu/YouTube Shorts platform profiles.
- Boundary kept: no Web UI, no NarratoStudio, no Router runtime, no Memory
  runtime, and no claim that deterministic highlight scoring is editorially
  mature.

## 2026-05-20 - Phase 14.5 Selection Diagnostics

- Started `feature/phase-14-5-selection-diagnostics` from the merged Phase
  14.4E `master` after syncing `origin/master` and deleting the merged
  Phase 14.4E branch locally and remotely.
- Added `selection_diagnostics.json` generation from the existing
  `highlight_score_report.json` state. The diagnostic artifact summarizes
  selected score range, top rejected candidates, near misses, rejection reason
  counts, source-time distribution, boundary strategy distribution, and warning
  signals such as clustered selection, duplicate-source-window pressure, weak
  hook evidence, and near-miss rejected candidates.
- Added workflow node `write_selection_diagnostics` and inserted it after
  `write_highlight_score_report` in ASR-first finished-package workflows and
  the OCR-subtitle candidate scoring workflow.
- Updated `package_report.md` so finished-package reports include a compact
  Selection Diagnostics section alongside selected clips and rejected
  candidates.
- Extended the candidate scoring harness to require and validate
  `selection_diagnostics.json` for candidate-scoring runs.
- Updated workflow docs, workspace/tool contracts, tool catalog, and agent
  skill output contracts so agents can read diagnostics before deciding whether
  to rerun, review manually, or tune candidate settings.
- Boundary kept: diagnostics are read-only over existing scores. This phase
  does not change scoring weights, selected highlights, clip boundaries, media
  execution, ASR/OCR providers, or Web UI behavior.

## 2026-05-19 - Phase 14.2A Candidate Windows

- Started `feature/phase-14-2a-candidate-windows` from the merged local-ASR
  product acceptance `master`.
- Added `narratocut.candidate_sop.generate_candidate_windows` to expand a
  timestamped transcript into adjacent 1..N segment windows and record the
  transcript content channel for future ASR/OCR/fused transcript inputs.
- Added the `generate_candidate_windows` workflow node and
  `workflows/transcript_to_candidate_windows.yaml`, producing
  `candidate_windows.json` without scoring, highlight selection, FFmpeg,
  remote models, or video-frame inspection.
- Added a demo input and focused tests for window generation, duration bounds,
  node artifact writing, workflow loading, and static plan drafting.
- Added a `candidate_windows` inspect/review quality profile so
  `inspect-run` and `review-run` validate `candidate_windows.json` directly
  instead of falling back to the legacy mock hooks/scripts/clips checks.
- Updated the static tool catalog, tool contracts, README, and workflow docs so
  `candidate_windows.json` is a formal Phase 14.2A artifact for later viral
  scoring.
- Updated the viral quality plan after route review: keep Phase 14.2A narrow,
  prioritize Subtitle OCR Timeline next, then add ASR/OCR candidate fusion and
  scoring.
- Boundary kept: Phase 14.2A only generates candidate windows. Viral scoring,
  selected/rejected reasons, package reports, Web UI, and multimodal detection
  remain future work.

## 2026-05-19 - Phase 14.0B Product Quality Smoke Reclassification

- Started `feature/phase-14-0b-product-quality-smoke` from the merged Phase
  14.0 documentation `master`.
- Reclassified the Phase 13 Golden Path as an engineering smoke, not a
  product-quality acceptance run.
- Added optional `evidence` paths to `finished_package_manifest.json` so package
  review can inspect upstream artifacts such as `final_video_manifest.json`,
  `real_slice_manifest.json`, `clip_plan.json`, `subtitle_manifest.json`, and
  `audio_mix_manifest.json`.
- Added finished-package product-quality warnings for single-clip demo cuts,
  `0s`-only starts, missing highlight evidence, missing subtitle source-video
  binding, subtitle duration exceeding the primary video, and unverified BGM
  content fit.
- Updated the Golden Path docs and package example so the next product test can
  surface engineering success separately from product-quality warnings.
- Added `docs/product_quality_smoke.md` with the current expected warning set
  and the local Phase 14.0B baseline:
  `inspect-run` reports `11 passed / 0 failed / 6 warnings`, while
  `review-run` reports `17 passed / 0 failed / 7 warnings`.

## 2026-05-19 - Phase 14.0 Documentation and Golden Path Prep

- Started `feature/phase-14-0-docs-golden-path` from the Phase 13 complete
  `master`.
- Refreshed `README.md` and `README.zh-CN.md` to position NarratoCut as a
  CLI-first technical MVP with real final-video, subtitle, cover, BGM, package,
  inspect, and review capabilities.
- Replaced the stale Phase 13 Web UI roadmap with a Phase 14 Productization
  roadmap.
- Added `docs/current_architecture.md` to summarize the post-Phase-13
  architecture and artifact model.
- Added `docs/golden_path.md` to define the local Phase 13 complete product
  smoke from source video and ClipPlan to `finished_package_manifest.json`.
- Ran the Phase 13 complete Golden Path with local ignored media:
  `clip_plan_to_real_clips`, `clips_to_final_video`, `transcript_to_subtitles`,
  `final_video_with_subtitles`, `final_video_to_cover`,
  `final_video_with_bgm`, and `final_video_package`.
- Recorded the smoke result in `docs/product_smoke_phase13.md`: all seven
  workflows succeeded, and every inspect/review report showed `0 failed` and
  `0 warnings`.
- Generated real product artifacts under ignored
  `data/processed/runs/golden_path_phase13_*` directories, including
  `final_video.mp4`, `subtitles.srt`, `final_video_with_subtitles.mp4`,
  `cover.jpg`, `final_video_with_bgm.mp4`, and
  `finished_package_manifest.json`.
- Kept generated media and smoke outputs under ignored `data/` paths.

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

## 2026-05-19 - Phase 14.1 ASR-First Product Golden Path

- Started `feature/phase-14-1-asr-highlight-product-golden-path` from the merged Phase 14.0B `master`.
- Added deterministic script-highlight-to-ASR-transcript alignment via `script_highlight_alignment.json`, producing timestamped highlights from script-only highlights without visual semantic retrieval.
- Added clip-timeline subtitle export so subtitles are remapped from original-video transcript timestamps onto the assembled final-video timeline instead of reusing the source-video timeline directly.
- Extended `SubtitleManifest` with `timeline`, and package quality review now warns when subtitle evidence is not explicitly `final_video` timeline.
- Added optional local BGM metadata ingestion to `mix_bgm`; `quality_verified=true` is now carried into `audio_mix_manifest.json` so package review can distinguish verified music from arbitrary noise.
- Added two ASR-first product workflows:
  - `workflows/video_to_finished_package_real_asr.yaml`
  - `workflows/video_script_to_finished_package_real_asr.yaml`
- Added examples for the two workflows and a local BGM metadata example. Examples reference ignored local media only and do not commit videos or music.
- Added focused tests for script alignment, clip-timeline subtitles, BGM verified metadata, product package warning clearance, and both product Golden Path workflows with mocked ASR/FFmpeg.
- Product-quality intent: the old Phase 13 demo warning set remains a useful negative smoke, while the Phase 14.1 workflows can clear the six known product warnings when they receive multi-segment highlights, final-timeline subtitles, and verified BGM metadata.
- Boundaries kept: no visual/multimodal highlight detection, no Web UI, no publishing/upload, no automatic music recommendation, no real ASR in tests, and no default remote ASR without `NARRATOCUT_ALLOW_REMOTE_ASR=true`.

## 2026-05-19 - Local Faster-Whisper ASR Path

- Added `FasterWhisperASRProvider` for local `faster-whisper` transcription with CPU-first defaults (`model=tiny`, `device=cpu`, `compute_type=int8`).
- Added workflow node `transcribe_audio_faster_whisper` and local-ASR product workflow variants:
  - `workflows/video_to_finished_package_local_asr.yaml`
  - `workflows/video_script_to_finished_package_local_asr.yaml`
- Added example input bundles that use ignored local media and local model cache paths, without API keys or remote ASR opt-in.
- Updated tool contracts/catalog and workflow docs to distinguish remote ASR from local ASR.
- Verification so far: focused provider/workflow tests pass with mocked local ASR and FFmpeg. Real local ASR smoke still depends on installing `faster-whisper` and downloading a local model cache.

## 2026-05-19 - Local ASR Quality Hardening

- Improved script-to-transcript alignment for Chinese text by adding Chinese character and bigram tokens instead of relying only on English/number word tokens.
- Added transcript sliding-window matching so one script highlight can align to multiple adjacent ASR segments, which is important for local Whisper models that split Chinese speech into short fragments.
- Updated local-ASR examples to prefer `small` + CPU `int8` for better Chinese quality, with `tiny` kept as the faster engineering-only option.
- Local product smoke:
  - video-only local ASR with `small/int8/cpu`: workflow succeeded, `inspect-run` passed with 0 warnings, `review-run` passed with 0 warnings.
  - video+script local ASR with `small/int8/cpu` and lower local alignment threshold: workflow succeeded, `inspect-run` passed with 0 warnings, `review-run` passed with 0 warnings.

## 2026-05-19 - Phase 14.2B/C OCR Timeline and Candidate Scoring

- Added a deterministic OCR-subtitle timeline SOP that converts frame-level OCR results into `ocr_transcript.json` and `ocr_transcript_manifest.json`.
- Added an explainable candidate scoring SOP that writes `highlight_score_report.json` and selects scored candidates into `highlight_plan.json`.
- Added `workflows/video_subtitle_ocr_to_highlight_plan.yaml` for the offline OCR evidence path: video path validation, OCR timeline, candidate windows, scoring, and selected highlights.
- Added `candidate_scoring` inspect/review quality checks for OCR transcript presence, candidate count, selected score breakdowns, and candidate IDs in selected highlights.
- Updated tool catalog, tool contract docs, workflow docs, and README workflow/artifact lists.
- Boundary kept: no real OCR provider dependency, no frame extraction, no FFmpeg execution, no remote calls, no media slicing, no Web UI.

## 2026-05-19 - Phase 14.2D Short Highlight Product Path

- Switched the ASR-first finished-package workflows from direct highlight detection to the candidate scoring path:
  - `video_to_finished_package_real_asr.yaml`
  - `video_script_to_finished_package_real_asr.yaml`
  - `video_to_finished_package_local_asr.yaml`
  - `video_script_to_finished_package_local_asr.yaml`
- Added product defaults for short promo clips in `generate_candidate_windows`: target windows default to about 5 seconds with 4-6 second preferred candidates when explicit candidate settings are not supplied.
- Added script-alignment evidence propagation into candidate windows, scored highlights, and final clip-plan segment metadata.
- Added duplicate-source-window rejection so the scorer does not fill the final edit with adjacent fixed splits from the same long ASR/alignment window.
- Added finished-package product-quality warnings for clips over the hard short-clip limit, final videos over the hard short-form limit, duplicate clip windows, and clip plans that bypass candidate scoring.
- Real local product acceptance after this change:
  - video-only: 4 clips, clip durations 4.2s / 4.6s / 5.0s / 5.0s, final duration 18.82322s, `inspect-run` pass with 0 warnings, `review-run` passed with 0 warnings.
  - video+script: 4 clips, clip durations 5.0s / 5.0s / 4.98s / 5.0s, final duration 20.00322s, 4 aligned / 0 skipped script highlights, `inspect-run` pass with 0 warnings, `review-run` passed with 0 warnings.
- Product judgment: this fixes the previous 30s/90s overlong-cut failure and makes the current local acceptance suitable for short promo validation. Remaining quality risk is editorial selection depth: scoring is still deterministic and text-first, with OCR/visual/audio fusion planned as later evidence channels.

## 2026-05-20 - Phase 14.3 Workspace and Agent Contract Hardening

- Added `package_report.md` generation for finished-package runs so humans and agents have one readable summary instead of scanning many JSON artifacts.
- Added `ncut package-report --run-dir ...` to refresh the report after `inspect-run` and `review-run`; the workflow writes an initial report, while formal acceptance should refresh it after quality and review artifacts exist.
- Added workflow metadata (`metadata.kind`, `metadata.status`, `metadata.audience`) to recommended product workflows so agents can choose product entrypoints without relying only on filenames.
- Added `skills/` with agent-readable task contracts for video-only and video+script short highlight package generation.
- Added `docs/workspace_contract.md`, refreshed docs/workflow navigation, and updated the tool catalog/docs for `write_package_report`.
- Split FFmpeg CLI handling into `apps/cli/media_commands.py` while adding package-report CLI handling in `apps/cli/report_commands.py`, keeping `apps/cli/main.py` under the 300-line target.
- Boundary kept: no Web UI, no new agent runtime, no autonomous workflow selection, no highlight scoring algorithm rewrite, and no cleanup of ignored local run/model/media artifacts.

## 2026-05-20 - Phase 14.4A Elastic Short Clip Boundaries

- Replaced rigid long-window fixed splits with elastic short-clip boundary generation.
- Long transcript/alignment windows now split into balanced 4-6 second candidates when possible instead of leaving a short tail fragment.
- Unsplittable overlong windows now trim to the target-length core instead of producing sub-four-second weak fragments.
- Candidate evidence now records `boundary_strategy`, `target_duration_sec`, and source-window bounds for selected clips.
- `package_report.md` now displays boundary strategy, target duration, and source window for each selected clip when scoring evidence is available.
- Boundary kept: this improves clip timing shape and explainability, but does not introduce scene/silence detection, visual models, Web UI, or a new viral scoring algorithm.

## 2026-05-20 - Phase 14.4B Elastic Boundary Acceptance

- Synced `master` to PR #32 and cleaned the merged Phase 14.4A branch locally and remotely.
- Re-ran the local video-only product workflow on `data/raw/demo_real_video/input.mp4`.
  - Result: 4 clips, durations 4.2s / 4.6s / 4.79s / 4.59s, final duration 18.222331s.
  - `inspect-run`: pass, 8 passed / 0 failed / 0 warnings.
  - `review-run`: passed, 37 passed / 0 failed / 0 warnings.
- Re-ran the local video+script product workflow on `data/raw/demo_zombie/input.mp4` and `script.txt`.
  - Result: 4 clips, durations 4.9225s / 4.98s / 5.346667s / 4.785s, final duration 20.082292s.
  - Script alignment: 4 aligned / 0 skipped.
  - `inspect-run`: pass, 8 passed / 0 failed / 0 warnings.
  - `review-run`: passed, 38 passed / 0 failed / 0 warnings.
- Refined `package_report.md` boundary display so native short transcript windows are labeled `native_transcript_window` instead of `unknown`.
- Added `docs/product_acceptance_phase14_4b_elastic_boundaries.md` as the acceptance record.
- Boundary kept: this is an execution and boundary-evidence acceptance pass, not a claim that deterministic viral selection is editorially mature.

## 2026-05-20 - Phase 14.4C Local Audio Boundary Signals

- Added `boundary_signal_manifest.json` generation from the already extracted local WAV artifact.
- Added workflow node `analyze_audio_boundary_signals` and inserted it into ASR-first finished-package workflows before transcription/scoring.
- Candidate windows now attach nearest low-energy audio boundary evidence when a successful boundary signal manifest is available.
- `package_report.md` now displays selected-clip audio boundary evidence alongside transcript boundary strategy and source-window evidence.
- Updated workflow docs, workspace contract, tool catalog/contracts, and agent skill outputs so agents can treat audio boundary evidence as a first-class advisory artifact.
- Boundary kept: audio signals are advisory and local-only. They do not replace transcript/scoring logic, do not call remote models, do not add visual/multimodal analysis, and do not fail the product workflow when mock audio or unsupported audio cannot be analyzed.

## 2026-05-20 - Phase 14.4D Audio Boundary Cut-Point Refinement

- Added safe audio-boundary refinement for candidate windows: nearby high-confidence audio boundaries can adjust candidate `start_sec` and/or `end_sec`.
- Refinement is constrained by maximum adjustment distance, source transcript window bounds, and the existing short-clip duration gates, so it cannot produce overlong or underlong candidates.
- Candidate evidence now records `audio_boundary_refinement`, `boundary_strategy=audio_boundary_refined`, and `base_boundary_strategy` for refined elastic subwindows.
- Updated scoring duplicate-source-window rejection so audio-refined split candidates still dedupe against the original transcript/alignment window.
- `package_report.md` now shows base boundary strategy and audio refinement before/after time ranges for selected clips.
- Kept the boundary narrow: no Web UI, no remote LLM, no new dependencies, no visual model, and no claim that deterministic viral selection is editorially mature.

## 2026-05-20 - Phase 14.4E Audio Boundary Refinement Acceptance

- Synced `master` to PR #35 and cleaned the merged Phase 14.4D branch locally and remotely after confirming the remote branch tree matched `master`.
- Re-ran the local video-only product workflow on `data/raw/demo_real_video/input.mp4`.
  - Result: 4 clips, durations 4.2s / 4.6s / 4.79s / 4.56s, final duration 18.189323s.
  - Audio refinement applied to selected candidate `cand_008`: 32.47s - 37.06s -> 32.50s - 37.06s.
  - `inspect-run`: pass, 8 passed / 0 failed / 0 warnings.
  - `review-run`: passed, 38 passed / 0 failed / 0 warnings.
- Re-ran the local video+script product workflow on `data/raw/demo_zombie/input.mp4` and `script.txt`.
  - Result: 4 clips, durations 4.9225s / 4.98s / 5.346667s / 4.785s, final duration 20.082292s.
  - Script alignment: 4 aligned / 0 skipped.
  - No selected candidate required audio-boundary refinement in this run.
  - `inspect-run`: pass, 8 passed / 0 failed / 0 warnings.
  - `review-run`: passed, 39 passed / 0 failed / 0 warnings.
- Refined `package_report.md` audio-boundary display so distant nearest boundaries are summarized as `not nearby` instead of cluttering acceptance reports with misleading far-away evidence.
- Added `docs/product_acceptance_phase14_4e_audio_boundary_refinement.md` as the acceptance record.
- Boundary kept: this is local product acceptance plus report readability hardening, not a broader scoring rewrite or Web UI step.

## 2026-05-20 - Phase 14.6 Delivery Readiness Gate

- Synced local `master` to PR #37, deleted the merged local and remote `feature/phase-14-5-selection-diagnostics` branch, and started `codex/phase-14-6-delivery-hardening` from the latest `master`.
- Added `ncut delivery-readiness` to summarize one or more refreshed product run directories into `delivery_readiness.json` and `delivery_readiness.md`.
- Added `narratocut.package_sop.delivery` as a report-only gate over existing run artifacts: package manifest, quality report, review report, package report, score report, and selection diagnostics.
- Updated tool catalog, tool-contract docs, workspace docs, workflow docs, and agent skill contracts so the delivery readiness report becomes the final handoff gate after `inspect-run`, `review-run`, and `package-report`.
- Smoke-tested the gate against the latest local Phase 14.4E acceptance run directories. The command wrote reports but correctly returned `fail` because those older local runs predate Phase 14.5 and do not contain `selection_diagnostics.json`; formal delivery readiness now requires rerunning the product paths after Phase 14.5+.
- Re-ran both formal local product paths as Phase 14.6 acceptance runs:
  - video-only: `product_acceptance_video_only_phase14_6`, 16 candidates, 4 selected clips, final duration 18.189323s, `inspect-run` pass, `review-run` passed with 39 checks / 0 warnings.
  - video+script: `product_acceptance_video_script_phase14_6`, 18 candidates, 4 selected clips, final duration 20.082292s, 4 aligned / 0 skipped script highlights, `inspect-run` pass, `review-run` passed with 40 checks / 0 warnings.
- Ran final `delivery-readiness` for both Phase 14.6 runs. Result: `warning`, 0 failed runs, 2 warning runs. The warnings are selection-quality signals (`near_miss_rejected`, `too_many_selection_limit_rejections`, `duplicate_source_window_pressure`, `few_strong_hooks`), not execution failures.
- Added `docs/product_acceptance_phase14_6_delivery_readiness.md` as the acceptance record.
- Boundary kept: this gate does not rerun ASR/OCR/slicing/assembly, does not call remote providers, does not add Web UI, and does not claim deterministic selection quality is editorially final.

## 2026-05-20 - Phase 14.6 Selection-Quality Hardening

- Investigated the Phase 14.6 delivery-readiness warnings and confirmed the main root cause was not execution failure: selected candidates were tying on duration-fit because the deterministic scorer did not recognize Chinese short-drama/promo hook, conflict, payoff, or specificity cues.
- Added a focused `candidate_sop.signals` module for multilingual deterministic content signals, keeping `scoring.py` under the 300-line target.
- Updated candidate scoring so Chinese terms such as `消失`, `后悔`, `重生`, `末世`, `广播`, `疫苗`, `年入`, `百万`, `穷酸`, and related payoff/conflict cues contribute to `hook_strength`, `conflict_intensity`, `payoff_or_reversal`, and `specificity_or_novelty`.
- Added a small source-window position penalty for later repeated elastic subwindows, while preserving timeline-ordered `highlight_plan.json` output so final assembly remains natural.
- Refined `selection_diagnostics.json` warnings so expected overlap and duplicate-source pruning remain visible as near-miss evidence but do not raise delivery-readiness warnings unless the pressure is actionable.
- Added regression tests for Chinese short-drama hook prioritization, repeated source subwindow penalties, and non-actionable selection-limit/duplicate pruning warnings.
- Re-ran formal local product paths as selection-quality acceptance runs:
  - video-only: `product_acceptance_video_only_phase14_6_selection_quality`, 16 candidates, 4 selected clips, final duration 18.788998s, `selection_diagnostics.json` 0 warnings, `inspect-run` pass, `review-run` 39 passed / 0 warnings.
  - video+script: `product_acceptance_video_script_phase14_6_selection_quality`, 18 candidates, 4 selected clips, final duration 20.419887s, `selection_diagnostics.json` 0 warnings, `inspect-run` pass, `review-run` 40 passed / 0 warnings.
- Ran final `delivery-readiness` for the selection-quality reruns. Result: `pass`, 2 passed / 0 warning / 0 failed.
- Boundary kept: this closes the visible deterministic selection warnings for current local acceptance素材, but it is still text-first heuristic scoring, not a claim that viral/editorial judgment is mature.

## 2026-05-20 - Post-v0.1.0 Startup Scan and Phase 15 Planning

- Confirmed the release baseline after the `v0.1.0` closeout:
  - local `master`: `bf5e7a1`
  - `origin/master`: `bf5e7a1`
  - remote head: only `master`
  - `v0.1.0` tag type: annotated tag
  - `v0.1.0` tag object: `460deba`
  - `v0.1.0^{}`: `bf5e7a1`
  - working tree: clean before the planning edits
- Added `docs/post_v0_1_0_plan.md` as the post-release operating plan.
- Updated `docs/README.md` and `docs/product_roadmap.md` so future agents start from the Phase 15 plan instead of reopening older phase notes.
- Planning boundary: keep the `v0.1.0` CLI/Agent MVP stable, open a future Web UI branch as a package/run viewer, and expand AgentFlow Studio mainline through architecture/contracts before runtime work.
- Boundary kept: no workflow, schema, CLI, provider, media, or Web UI implementation changed in this planning pass.

## 2026-05-20 - NarratoStudio Mainline MVP

- Added `NarratoStudio` as a sibling production-side MVP module inside the current repository. `NarratoCut` remains the distribution-side module.
- Implemented the first recommended workflow:
  - `creative_brief.json`
  - `story_bible.json`
  - `episode_outline.json`
  - `scene_plan.json`
  - `shot_plan.json`
  - `prompt_pack.json`
  - `production_handoff.json`
  - `production_report.md`
- Added local deterministic SOP logic and Pydantic contracts under `narratostudio/`; no remote LLM, Agent runtime, database, or Web UI was added.
- Added Agent-native auxiliary artifacts:
  - `memory_candidates.json` with candidate-only promotion status
  - `cost_quality_trace.json` with `execution_mode: local_deterministic`
  - `feedback_signal_log.json` as a derived artifact, not a feedback source of truth
  - `execution_trace.json` as a local workflow execution trace
- Added `narratostudio_production_handoff` inspect/review profile and agent skill contract.
- Added `docs/narratostudio_contracts.md`, workflow docs, and the example creative brief.
- Verification:
  - `.venv\Scripts\python.exe -m pytest`: 333 passed
  - `.venv\Scripts\python.exe -m compileall apps narratocut narratostudio tests`: passed
  - `git diff --check`: passed
  - `.venv\Scripts\python.exe -m apps.cli.main --help`: passed
  - `.venv\Scripts\python.exe -m apps.cli.main version`: `0.1.0`
  - NarratoStudio CLI smoke: workflow success, inspect `58 passed / 0 failed / 0 warnings`, review `76 passed / 0 failed / 0 warnings`
- Boundary kept: Web UI branch remains separate; this change does not migrate `D:\Projects\Zhike` and does not rename the repo or CLI.
