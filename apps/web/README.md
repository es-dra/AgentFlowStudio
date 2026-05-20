# NarratoCut Static Artifact Viewer

This is a read-only, local-only static viewer for NarratoCut workflow artifacts.
It is the first Web UI slice for the `codex/narratocut-web-ui` branch.

Open it directly in a browser:

```text
apps/web/index.html
```

No server is required.

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

## Privacy Boundary

- read-only
- local-only
- no upload
- no backend execution
- no persistence
- no provider calls
- no workflow execution
- no automatic directory scanning

The viewer parses selected JSON and Markdown files in the browser and renders a
temporary inspection view. It does not write files, save settings, submit
feedback, or store state.

## Non-Goals

Feedback writing is out of scope for this first slice.

Also out of scope:

- running `ncut`
- scanning a run directory
- uploading artifacts
- opening provider configuration
- playing local videos
- editing timelines
- saving review decisions

Future slices may add feedback event copy/export or explicit local video preview,
but those features must keep the local-only boundary.
