# Web Workbench Reference

This reference holds details that are useful for maintenance but too bulky for
`apps/web/README.md`.

## Artifact Sets

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

Both aliases normalize internally as `package_manifest`.

## Workbench Views

- Top bar: selected file count, acceptance input count, risk count, parse error
  count, delivery status, language toggle, and file picker.
- Review path: navigation for delivery overview, video preview, asset check,
  risk handling, report review, and contract inspection.
- Delivery overview: loaded run, package, review, and delivery readiness.
- Video preview: explicit selected local media only.
- Asset check: final video, clips, subtitles, cover, BGM, and package assets.
- Risk handling: warnings, failures, recommendations, diagnostics, delivery
  readiness failures, nested review warnings, and viewer load notes.
- Review inspector: quality/review checks, recommendations, readiness runs,
  warnings, and failures.
- Evidence chain: selected artifacts plus `run_manifest.artifact_index` and
  `package_manifest.evidence`.
- Contract Inspector: file name, artifact type, schema state, source role,
  parse status, and acceptance-summary participation.
- Report review: Markdown rendered as escaped text, with tabs when multiple
  reports are selected.
- Production Mode: workflow selector, input/output fields, plan generation,
  local run launch, readiness, review refresh, step timeline, artifact
  timeline, bridge health, execution log, video review, and supervision.
- Memory Workbench: project/assets rail, memory canvas, Baseline versus
  Memory-backed lanes, provenance inspector, feedback timeline, and copy-only
  feedback draft preview.

Markdown reports are displayed as escaped text. Inline HTML such as `<script>`
is shown literally and is not executed.

## Production Mode Boundary

Production Mode is local execution, not SaaS:

- It requires the user to start `web-bridge` explicitly.
- It only connects to `http://127.0.0.1:8787`.
- Browser code does not run Python directly.
- `GET /health` reports local bridge, Python, workspace, FFmpeg, FFprobe, and
  optional local ASR dependency state without exposing secrets.
- `GET /workflows` lists workflow definitions from `workflows/*.yaml`.
- `POST /plans` writes `workflow_plan.json` without running the workflow.
- `POST /runs` starts a local workflow run.
- `GET /runs/{id}` returns run status, steps, files, artifact index, and next
  actions.
- `POST /runs/{id}/review` refreshes `quality_report.json`,
  `review_report.json`, and `package_report.md`.

`POST /plans` and `POST /runs` return `input_check`, a diagnostic summary of
file-like values from the selected input bundle. Missing media, BGM, scripts,
configs, or other files are shown as categorized blockers.

Supervision controls currently record user intent. They do not interrupt a
running Python step or implement true step-level rerun.

## Local Video Preview

- The user must select a `.mp4`, `.webm`, or `.mov` file with the file picker.
- The viewer uses a temporary browser object URL.
- The viewer does not read manifest paths, open local paths automatically, scan
  folders, upload media, or call a backend.
- `.mov` playback depends on browser support.

## Smoke Notes

The committed fixture lives under:

```text
tests/fixtures/web_static_artifact_viewer/product_run/
```

It is a sanitized product-run-shaped artifact set with relative placeholder
paths and no generated runtime media.

Ignored real smoke runs have also been checked under
`data/processed/runs/webui_smoke_*`. Those artifacts are not committed. They
cover FFmpeg-generated media, package manifest evidence paths, package report,
quality report, review report, delivery readiness, and candidate-scoring
artifacts.

Production Mode smoke uses:

```text
python -m apps.cli.main web-bridge --host 127.0.0.1 --port 8787
python -m http.server 8769 -d apps/web
```

Selecting the local demo workflow with `mock_text_to_slices` has verified plan
generation, successful run completion, step states, run artifact listing, and
review refresh to `passed`.
