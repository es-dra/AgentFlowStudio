# NarratoCut Web UI Workbench

This branch now has two local modes:

- `Review Mode`: the original read-only, local-only artifact viewer.
- `Production Mode`: a supervised local production workbench that talks only to
  the optional NarratoCut Web Bridge on `127.0.0.1`.

Open the UI directly in a browser:

```text
apps/web/index.html
```

No server is required for Review Mode.

For Production Mode, start the local bridge in a separate terminal:

```powershell
python -m apps.cli.main web-bridge --host 127.0.0.1 --port 8787
```

Then open `apps/web/index.html` or serve it locally. The browser connects only
to `http://127.0.0.1:8787`.

## Current Slice

The current branch includes:

- M1.1 release-candidate hardening for safe local artifact parsing.
- M1.2 Chinese-first workbench presentation with an in-memory language toggle.
- M1.2.1 polish for denser workbench layout, Chinese panel titles, quieter empty
  state, and acceptance-oriented metrics.
- M1.3 artifact universe expansion for additional NarratoCut run artifacts.
- M1.5 local video preview for explicitly selected `.mp4`, `.webm`, or `.mov`
  files only.
- M2 feedback event copy, which generates JSON text for manual copy/export.
- M1.4 information architecture polish, which turns the default surface from an
  artifact-first dashboard into a production-oriented local review workbench.
- M3 supervised production workbench foundation:
  - optional stdlib local bridge, with no FastAPI dependency;
  - workflow discovery from `workflows/*.yaml`;
  - `workflow_plan.json` generation through the same planner used by
    `ncut draft-plan`;
  - input bundle diagnostics that surface missing local media/config references
    before or during a run;
  - background workflow execution through the existing workflow engine path;
  - step progress polling through `bridge_status.json`;
  - review refresh through `inspect-run`, `review-run`, and `package-report`;
  - step timeline, artifact timeline, current task, blockers, and supervision
    controls in the browser.
- M3.1 production readiness workspace:
  - product-facing workflow display names such as `本机演示：文本到切片` and
    `完整成品包：本地 ASR`;
  - a preflight panel for production target, local environment, input
    diagnostics, and next action;
  - categorized input blockers for local media, BGM, script, config, and other
    file references;
  - a Production Mode video review panel for explicitly selected local video
    files only;
  - honest supervision actions that record intent instead of pretending to
    pause, resume, or rerun a Python step;
  - run-level feedback JSON copy with run/workflow context and optional video
    timestamp.
- Local Alpha 0.3 operator loop:
  - the Production Path now follows workflow selection -> plan -> supervised
    run -> artifact inspection -> review refresh -> feedback capture;
  - the acceptance panel shows the current loop state, review report refs, and
    whether run feedback has been captured for copy;
  - run-level feedback JSON includes review status plus `review_report` and
    `quality_report` refs after review refresh.

The viewer uses default Chinese UI copy for human-facing labels. The language
toggle is in-memory only. Refreshing the page returns to Chinese.
The viewer does not use `localStorage`, IndexedDB, cookies, or any persistence
mechanism.

## Chinese Copy And Terminal Mojibake

The source files are UTF-8 and the browser renders Chinese copy directly. Some
Windows terminal sessions may show terminal mojibake when printing those files
with legacy code pages. For review, prefer the browser, an editor opened as
UTF-8, or a `unicode_escape`/UTF-8-aware check instead of judging the raw
terminal rendering.

## Supported Artifacts

The viewer reads only files explicitly selected by the user with the file picker.
It does not scan directories and it does not follow paths declared inside
manifests.

Recommended product-run set:

```text
run_manifest.json
finished_package_manifest.json
quality_report.json
review_report.json
package_report.md
```

Optional delivery handoff set:

```text
delivery_readiness.json
delivery_readiness.md
```

Expanded read-only artifact universe:

```text
selection_diagnostics.json
highlight_score_report.json
candidate_windows.json
clip_plan.json
real_slice_manifest.json
final_video_manifest.json
subtitle_manifest.json
audio_mix_manifest.json
cover_manifest.json
```

Package manifest aliases:

```text
package_manifest.json
finished_package_manifest.json
```

Both are normalized internally as `package_manifest`. The original selected file
name remains visible in the UI.

## Artifact Classification

The viewer normalizes selected files before any panel renders them:

- `known_contract`: a supported NarratoCut artifact that participates in the
  summary, evidence map, risk ledger, asset ledger, and inspector views.
- `unknown_json`: a JSON object that parsed successfully but is not a known
  NarratoCut contract. It is visible in inventory but not included in summary.
- `unsupported_file`: a selected file type that the static viewer does not use.
  It is visible as a load note but not included in summary.
- `local_media`: a user-selected video file eligible for local preview only.
- invalid JSON or non-object JSON: shown as a recoverable load error.

Missing `schema_version` is a warning, not a fatal error. Some current
NarratoCut artifacts, including `run_manifest.json` and `quality_report.json`,
may omit it while still being readable by this viewer.

## Workbench Views

- Top bar: selected file count, acceptance input count, risk count, parse error
  count, delivery status, language toggle, and local file picker.
- Review path: a compact navigation rail for delivery overview, video preview,
  asset check, risk handling, report review, and contract inspection.
- Recommended file sets: package run, upstream evidence, and handoff gate
  checklists to help users select the right cross-run artifacts.
- Delivery overview: loaded run, package, review, and delivery readiness
  summary.
- Video preview: explicit selected local media only; no manifest path auto-read.
- Asset check: final video, clips, subtitles, cover, BGM, and package asset
  paths.
- Risk handling: warnings, failures, review recommendations, diagnostics
  signals, delivery readiness failures, nested review warnings, and viewer load
  notes.
- Review inspector: quality/review checks, recommendations, readiness runs,
  warnings, and failures from normalized artifacts.
- Evidence chain: selected artifacts plus `run_manifest.artifact_index` and
  `package_manifest.evidence` entries.
- Contract Inspector: file name, artifact type, schema state, source role, parse
  status, and whether the file participates in acceptance summary. This is an
  engineering inspector, not the default production focus.
- Report review: Markdown rendered as escaped text, with tabs when both
  `package_report.md` and `delivery_readiness.md` are selected.
- Production Mode: workflow selector, input/output fields, plan generation,
  local run launch, production readiness, review refresh, step timeline,
  artifact timeline, bridge health, execution log, video review, and human
  supervision controls.

Markdown reports are displayed as escaped text. Inline HTML such as `<script>`
is shown literally and is not executed.

## Local Video Preview

Local video preview is explicit-file-only:

- The user must select a `.mp4`, `.webm`, or `.mov` file with the file picker.
- The viewer uses a temporary object URL in the browser.
- The viewer does not read manifest paths, open local paths automatically, scan
  folders, upload media, or call a backend.
- `.mov` playback depends on browser support and may not work in every browser.

## Feedback Event Copy

M2 feedback event copy generates a `feedback_event` JSON object in the browser
and copies it when the Clipboard API is available. If Clipboard is unavailable,
the JSON remains in a textarea for manual copy.

This does not write files, append JSONL, upload data, call a backend, or persist
state. It is a static local copy/export aid only.

## Production Mode Boundary

Production Mode is local execution, not SaaS:

- It requires the user to start `ncut web-bridge` explicitly.
- It only connects to `http://127.0.0.1:8787`.
- Workflow execution still goes through `WorkflowRunner` and existing CLI
  contracts; browser code does not run Python directly.
- `GET /health` reports local bridge, Python, workspace, FFmpeg, and FFprobe
  readiness plus optional local ASR dependency state without exposing provider
  keys or environment secrets.
- `GET /workflows` lists workflow definitions from `workflows/*.yaml`.
- `POST /plans` writes `workflow_plan.json` without running the workflow.
- `POST /runs` starts a local workflow run.
- `GET /runs/{id}` returns run status, steps, files, artifact index, and next
  actions.
- `POST /runs/{id}/review` refreshes `quality_report.json`,
  `review_report.json`, and `package_report.md`.

`POST /plans` and `POST /runs` also return `input_check`, a local diagnostic
summary of file-like values from the selected input bundle. Missing referenced
media, BGM, script, config, or other files are shown as categorized blockers in
the Production Mode readiness panel.
`GET /health` reports whether optional `faster-whisper` local ASR dependencies
are installed. A missing ASR dependency is shown as a blocker for local-ASR
workflows, but it does not prevent Review Mode or mock workflows from working.

The workflow list now includes a Web UI profile for the production surface:

- `完整成品`: product workflows such as
  `video_to_finished_package_local_asr`, which require local media, FFmpeg,
  BGM, and local ASR dependencies before they can complete.
- `本机演示`: demo workflows such as `mock_text_to_slices`, which require no
  media, FFmpeg, or ASR and can be used to verify the supervised production
  loop on a clean machine.

The Production Mode form exposes quick buttons for both paths. The default
product path is still visible, but the demo path can now run end-to-end through
plan generation, background workflow execution, step polling, artifact listing,
and review refresh.

Current supervision controls are first-slice UI gates. They make the user intent
visible (`continue`, `pause`, `rerun`, `needs changes`) but do not yet support
true step-level pause/resume or rerun-from-step. The button labels are explicit:
they record pause notes, rerun suggestions, and change requests rather than
interrupting a running local Python step.

Production Mode can generate a run-level feedback JSON event for manual copy.
It includes `run_dir`, `run_id`, workflow, decision, risk category, reviewer
note, optional `video_time_sec`, and review refs when review refresh has run:
`review_status`, `review_report`, and `quality_report`. It does not write
`feedback.jsonl`, upload data, or persist browser state.

Workflow runs started from Production Mode are launched in a background bridge
thread. The page polls `GET /runs/{id}` and reads `bridge_status.json`, so the
user can see pending/running/success/failed step states while the run is still
in progress. This is observability, not full orchestration: the current bridge
does not interrupt an already running Python step.

## Privacy Boundary

- Review Mode is read-only and local-only.
- Production Mode is local-only and explicitly bridge-backed.
- no upload
- no backend execution in Review Mode
- no remote backend execution
- no persistence in browser state
- no browser persistence
- no provider calls
- no workflow execution in Review Mode
- no browser-side workflow execution
- no automatic directory scanning
- no manifest path auto-read
- no provider config
- no SaaS, account system, cloud storage, database, or collaboration service

Review Mode parses selected JSON, Markdown, and video files in the browser and
renders a temporary inspection view. Production Mode sends explicit workflow
paths, input paths, and output directories to the local bridge selected by the
user.

## Non-Goals

Out of scope for this static viewer:

- scanning a run directory
- uploading artifacts
- opening provider configuration
- provider config
- editing timelines
- saving review decisions
- writing feedback files
- remote/cloud execution
- step-level pause/resume
- rerun-from-step
- timeline editing
- provider credential management

## Reference Boundary

M1.2+ borrows only visual and interaction ideas from the local Zhike reference:
dark workbench structure, status colors, dense panels, and right-side inspection
rhythm. No Zhike runtime code, business logic, provider code, routes, database
code, or dependencies are included.

The broader product references are W&B-style artifact metadata and lineage,
LangSmith-style run debugging, Langfuse-style scores/comments, and Frame.io /
Workfront-style review status. Those references are UX concepts only; this
viewer remains static and local.

## Test Fixture

`tests/fixtures/web_static_artifact_viewer/product_run/` contains a small,
sanitized artifact set based on the real NarratoCut `final_video_package`
workflow shape. It keeps contract fields for run/package/quality/review/delivery
coverage, uses relative placeholder media paths, and does not include media
files or generated runtime directories.

## Real Smoke Notes

The viewer has also been checked locally against ignored real run artifacts
generated under `data/processed/runs/webui_smoke_*`. Those smoke artifacts are
not committed, but they cover real FFmpeg-generated media, package manifest
evidence paths, package report, quality report, review report, delivery
readiness, and candidate-scoring artifacts.

The real smoke is intentionally run from the CLI, not from the Web UI. This
viewer remains a static artifact consumer.

Production Mode smoke now also covers the local bridge path:

```text
python -m apps.cli.main web-bridge --host 127.0.0.1 --port 8787
python -m http.server 8769 -d apps/web
```

In the browser, selecting `生产 -> 本机演示` with `mock_text_to_slices` has been
verified to generate `workflow_plan.json`, run to `success`, show all four step
states as passed, list actual run artifacts, and refresh the review report to
`passed`.
