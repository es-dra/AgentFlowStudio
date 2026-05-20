# NarratoCut Static Artifact Viewer

This is a read-only, local-only static viewer for NarratoCut workflow artifacts.
It currently includes the M1.1 hardening slice and the M1.2 Chinese workbench
presentation slice for the `codex/narratocut-web-ui` branch.

Open it directly in a browser:

```text
apps/web/index.html
```

No server is required.

## M1.2 Workbench UI

The M1.2 viewer uses default Chinese UI copy because the current review and
delivery workflow is Chinese-facing. Contract names, artifact types, schema
fields, and machine-readable keys remain in English.

The language toggle is in-memory only. Refreshing the page returns to Chinese.
The viewer does not use `localStorage`, IndexedDB, cookies, or any other
persistence mechanism.

M1.2 borrows only visual and interaction ideas from the local Zhike reference:
dark workbench structure, status colors, a metric strip, and a right-side
inspection rail. No Zhike runtime code, business logic, provider code, routes,
database code, or dependencies are included.

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
  summary and inspector views.
- `unknown_json`: a JSON object that parsed successfully but is not a known
  NarratoCut contract. It is visible in inventory but not included in summary.
- `unsupported_file`: a selected file type that the static viewer does not use.
  It is visible as a load note but not included in summary.
- invalid JSON or non-object JSON: shown as a recoverable load error.

Missing `schema_version` is a warning, not a fatal error. Some current
NarratoCut artifacts, including `run_manifest.json` and `quality_report.json`,
may omit it while still being readable by this viewer.

## Privacy Boundary

- read-only
- local-only
- no upload
- no backend execution
- no persistence
- no provider calls
- no workflow execution
- no automatic directory scanning
- no video preview
- no provider config
- no CLI/API bridge

The viewer parses selected JSON and Markdown files in the browser and renders a
temporary inspection view. It does not write files, save settings, submit
feedback, or store state.

Markdown reports are displayed as escaped text. Inline HTML such as `<script>`
is shown literally and is not executed.

## Non-Goals

Feedback writing is out of scope for this first slice.

Also out of scope:

- running `ncut`
- scanning a run directory
- backend execution
- workflow execution
- uploading artifacts
- opening provider configuration
- provider config
- video preview
- playing local videos
- editing timelines
- saving review decisions

## Test Fixture

`tests/fixtures/web_static_artifact_viewer/product_run/` contains a small,
sanitized artifact set based on the real NarratoCut `final_video_package`
workflow shape. It keeps contract fields for run/package/quality/review/delivery
coverage, uses relative placeholder media paths, and does not include media
files or generated runtime directories.

Future slices may add feedback event copy/export or explicit local video preview,
but those features must keep the local-only boundary.
