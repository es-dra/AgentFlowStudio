# AgentFlow Studio Local Alpha 0.2 Acceptance Package

Date: 2026-05-27

## Purpose

Local Alpha 0.2 is the first product-facing acceptance package after the
parallel development trial. It turns current engineering evidence into a
repeatable local demo and review flow.

The milestone is not a hosted product. It is an evidence-driven local AI
content production workbench:

```text
brief / local media
  -> workflow plan
  -> supervised local run
  -> artifacts
  -> inspect / review / package report
  -> Web workbench acceptance
  -> feedback event
  -> memory candidate
  -> next-round context reuse
```

## Acceptance Status

Overall status: `blocked`.

Reason: AgentFlow Production and AgentFlow Studio have recorded local Alpha evidence, and
the Web workbench can run a local mock workflow through the bridge. PosterFlow
live image smoke is still blocked until local image-provider environment
variables are intentionally enabled.

Use the read-only status command first:

```powershell
.venv\Scripts\python.exe -m apps.cli.main alpha-smoke
.venv\Scripts\python.exe -m apps.cli.main alpha-smoke --json
```

This command does not write runtime artifacts and does not call remote
providers.

## Demoable Capabilities

| Capability | Current status | Evidence |
|---|---|---|
| AgentFlow Production production handoff | pass | `docs/alpha_readiness_report.md`, `workflows/agentflow_production_handoff.yaml` |
| AgentFlow Studio finished package chain | pass on this machine with local ignored media and FFmpeg | `docs/alpha_readiness_report.md`, `workflows/video_to_finished_package_local_asr.yaml` |
| Web workbench Review Mode | available | `apps/web/README.md`, `docs/handoff/AFS-WEB-REPLAY.md` |
| Web workbench Production Mode | local bridge demo passed with `mock_text_to_slices` | `apps/web/README.md`, `docs/handoff/AFS-WEB-REPLAY.md` |
| PosterFlow Memory OS demo contracts | available through mocked/local tests and pre-provider artifacts | `workflows/posterflow_memory_demo.yaml`, `tests/test_posterflow_workflow.py` |
| PosterFlow live image smoke | blocked by default | `docs/alpha_readiness_report.md`, `docs/task_briefs/AFS-POSTER-LIVE-001.md` |

## Required Local Setup

- Python 3.12 local environment.
- FFmpeg / FFprobe for real AgentFlow Studio media workflows.
- Local ignored media for the AgentFlow Studio package demo.
- Optional local image-provider environment only for PosterFlow live smoke.

Do not put provider keys, signed URLs, cookies, tokens, or private credentials
in repository files.

## Rerun Commands

### AgentFlow Production Handoff

```powershell
.venv\Scripts\python.exe -m apps.cli.main run-workflow --workflow workflows/agentflow_production_handoff.yaml --input examples/agentflow_production/creative_brief.example.json --output data/processed/runs/demo_agentflow_production_handoff_alpha
.venv\Scripts\python.exe -m apps.cli.main inspect-run --run-dir data/processed/runs/demo_agentflow_production_handoff_alpha
.venv\Scripts\python.exe -m apps.cli.main review-run --run-dir data/processed/runs/demo_agentflow_production_handoff_alpha
```

Acceptance: workflow succeeds, inspect passes, review passes, and generated
handoff artifacts remain local runtime evidence rather than committed
deliverables.

### AgentFlow Studio Finished Package

```powershell
.venv\Scripts\python.exe -m apps.cli.main run-workflow --workflow workflows/video_to_finished_package_local_asr.yaml --input examples/demo_asr/video_to_finished_package_local_asr_input.example.json --output data/processed/runs/demo_agentflow_studio_package_alpha
.venv\Scripts\python.exe -m apps.cli.main inspect-run --run-dir data/processed/runs/demo_agentflow_studio_package_alpha
.venv\Scripts\python.exe -m apps.cli.main review-run --run-dir data/processed/runs/demo_agentflow_studio_package_alpha
.venv\Scripts\python.exe -m apps.cli.main package-report --run-dir data/processed/runs/demo_agentflow_studio_package_alpha
```

Acceptance: workflow succeeds, inspect passes, review passes, package report is
refreshed, and generated media stays ignored.

### Web Workbench Demo

Start the local bridge:

```powershell
.venv\Scripts\python.exe -m apps.cli.main web-bridge --host 127.0.0.1 --port 8787
```

Serve the static UI:

```powershell
python -m http.server 8769 -d apps/web --bind 127.0.0.1
```

Open:

```text
http://127.0.0.1:8769/index.html
```

Acceptance: Review Mode renders, Production Mode sees bridge health, the
`mock_text_to_slices` workflow can plan, run to success, list artifacts, and
refresh review reports.

### PosterFlow Live Smoke

Default status is blocked. Run only when local image-provider environment is
already configured and the task intentionally enables:

```powershell
$env:AFS_ALLOW_REMOTE_IMAGE="true"
```

Then follow `docs/alpha_readiness_report.md` and
`docs/task_briefs/AFS-POSTER-LIVE-001.md`.

Acceptance: live run artifacts remain ignored, inspect/review output is
recorded in docs, and a no-secret scan confirms no provider key, signed URL, or
generated media is staged.

## Acceptance Checklist

- [ ] `alpha-smoke --json` returns machine-readable status.
- [ ] AgentFlow Production handoff evidence is either still recorded or freshly rerun.
- [ ] AgentFlow Studio package evidence is either still recorded or freshly rerun with
      local ignored media.
- [ ] Web workbench local bridge demo is rerun or linked to current browser
      smoke evidence.
- [ ] PosterFlow live smoke is either completed under the image provider gate or
      explicitly remains blocked.
- [ ] Generated run artifacts and media are not staged.
- [ ] Provider secrets and private Company knowledge are not copied into the
      repository.
- [ ] Reports distinguish structure verification, runtime verification, human
      acceptance, and business validation.

## Non-Claims

Local Alpha 0.2 does not claim:

- hosted SaaS readiness;
- durable Memory runtime;
- AgentFlow Router or skill runtime;
- vector store, database, or RAG quality;
- mature creative quality;
- viral/editorial judgment quality;
- provider cost-quality optimization;
- publishing or distribution integration.

## Next Product Lanes

| Lane | What it removes |
|---|---|
| `AFS-WEB-UX-001` | Web workbench usability and Chinese copy friction |
| `AFS-MEMORY-DEMO-001` | Weakness in the round-1 to round-2 Memory OS explanation |
| `AFS-POSTER-LIVE-001` | PosterFlow live-provider readiness blocker, if local env is available |

Integration order remains: Alpha package first, Web UX and Memory Demo in
parallel, Poster live smoke last.
