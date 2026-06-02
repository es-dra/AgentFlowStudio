# AgentFlow Studio Web UI Workbench

This folder contains the local static Web workbench used by AgentFlow Studio
and AgentFlow Studio review flows. It has three modes:

- `Review Mode`: read-only, local-only artifact inspection.
- `Production Mode`: supervised local production through the optional Web
  Bridge on `127.0.0.1`.
- `Memory Workbench`: static/local-only evidence canvas for the
  Project -> Assets -> Memory Loaded -> Baseline Run -> Memory-backed Run ->
  Review -> Feedback -> Next Pass loop.

Open the UI directly:

```text
apps/web/index.html
```

Review Mode and Memory Workbench need no server. For Production Mode, start the
local bridge in another terminal:

```powershell
python -m apps.cli.main web-bridge --host 127.0.0.1 --port 8787
```

Then open `apps/web/index.html` or serve the folder locally. The browser only
connects to `http://127.0.0.1:8787`.

## Current Slice

The current workbench line includes:

- M1.1 safe local artifact parsing.
- M1.2 default Chinese UI with an in-memory language toggle.
- M1.2.1 denser workbench layout and acceptance-oriented metrics.
- M1.3 expanded artifact universe.
- M1.4 production-oriented review information architecture.
- M1.5 local video preview for explicitly selected `.mp4`, `.webm`, or `.mov`
  files only.
- M2 feedback event copy for manual JSON copy/export.
- M3 and M3.1 supervised Production Mode with workflow selection, plan
  generation, local run launch, polling, review refresh, video review, and
  run-level feedback JSON copy.
- M4 through M4.9 static Memory Workbench, explicit memory package loading,
  selected bundle summaries, read-only artifact inspector, canvas focus,
  workflow action strip, browser-local feedback draft preview, sample bundle,
  protocol panel, and demo evidence summary.
- M5 through M5.3 AgentFlow Studio Canvas polish, demo-ready checklist,
  readiness cockpit, and operator command dock.

Detailed history lives in
[`../../docs/workbench/web_workbench_milestones.md`](../../docs/workbench/web_workbench_milestones.md).

## Supported Artifacts

The viewer reads only files explicitly selected by the user with the file
picker. It does not scan directories and it does not follow paths declared
inside manifests.

Recommended product-run set:

```text
run_manifest.json
finished_package_manifest.json
quality_report.json
review_report.json
package_report.md
```

Optional and expanded read-only artifacts include:

```text
delivery_readiness.json
delivery_readiness.md
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

`package_manifest.json` and `finished_package_manifest.json` are normalized as
`package_manifest`; the selected file name remains visible.

Artifact classification:

- `known_contract`: supported AgentFlow Studio artifact participating in summary,
  evidence, risk, asset, and inspector views.
- `unknown_json`: parsed JSON object that is visible in inventory but excluded
  from acceptance summary.
- `unsupported_file`: selected file type that remains a load note only.
- `local_media`: explicit video file eligible for local video preview only.
- Invalid JSON or non-object JSON: recoverable load error.

Missing `schema_version` is a warning, not a fatal error.

Reference details live in
[`../../docs/workbench/web_workbench_reference.md`](../../docs/workbench/web_workbench_reference.md).

## Boundaries

- Review Mode is read-only and local-only.
- Production Mode is local-only and explicitly bridge-backed.
- Memory Workbench is static/local-only and uses either the sanitized fixture or
  explicitly selected memory pipeline JSON artifacts.
- no upload
- no backend execution in Review Mode
- no remote backend execution
- no persistence in browser state
- no browser persistence
- no provider calls
- no provider config
- no workflow execution in Review Mode
- no browser-side workflow execution
- no automatic directory scanning
- no manifest path auto-read
- no SaaS, account system, cloud storage, database, or collaboration service

Feedback event copy generates JSON text for manual copy. It does not write
files, append JSONL, upload data, call a backend, or persist state.

Production Mode sends explicit workflow paths, input paths, and output
directories to the local bridge selected by the user. Workflow execution still
goes through `WorkflowRunner` and existing CLI contracts; browser code does not
run Python directly.

## Encoding Note

The source files are UTF-8 and the browser renders Chinese copy directly. Some
Windows terminals may show terminal mojibake with legacy code pages. For review,
prefer the browser, an editor opened as UTF-8, or an encoding-aware check. The
default Chinese copy is restored on refresh because the language toggle is
in-memory only.

## More Detail

- Design brief:
  [`../../docs/workbench/AFS-WORKBENCH-REDESIGN-001.md`](../../docs/workbench/AFS-WORKBENCH-REDESIGN-001.md)
- Milestones:
  [`../../docs/workbench/web_workbench_milestones.md`](../../docs/workbench/web_workbench_milestones.md)
- Artifact and boundary reference:
  [`../../docs/workbench/web_workbench_reference.md`](../../docs/workbench/web_workbench_reference.md)
