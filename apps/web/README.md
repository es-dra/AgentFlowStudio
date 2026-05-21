# NarratoCut Static Artifact Viewer

This is a read-only, local-only static viewer for NarratoCut workflow artifacts.
It is the Web UI branch's local acceptance workbench, not a workflow console.

Open it directly in a browser:

```text
apps/web/index.html
```

No server is required.

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

The viewer uses default Chinese UI copy for human-facing labels. The language
toggle is in-memory only. Refreshing the page returns to Chinese.
The viewer does not use `localStorage`, IndexedDB, cookies, or any persistence
mechanism.

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

## Privacy Boundary

- read-only
- local-only
- no upload
- no backend execution
- no persistence
- no provider calls
- no workflow execution
- no automatic directory scanning
- no manifest path auto-read
- no provider config
- no CLI/API bridge

The viewer parses selected JSON, Markdown, and video files in the browser and
renders a temporary inspection view.

## Non-Goals

Out of scope for this static viewer:

- running `ncut`
- scanning a run directory
- backend execution
- workflow execution
- uploading artifacts
- opening provider configuration
- provider config
- editing timelines
- saving review decisions
- writing feedback files

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
