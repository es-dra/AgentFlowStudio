# Workflows

This directory contains YAML workflow definitions for NarratoCut.

## Available workflows

### `mock_roi_to_script.yaml`

Phase 3 demo workflow:

1. `analyze_hooks`
2. `generate_scripts`

Example:

```powershell
.venv\Scripts\ncut run-workflow --workflow workflows/mock_roi_to_script.yaml --input examples/demo_text/story.txt --output data/processed/runs/demo_workflow
```

Generated files are written to the output directory. Runs under `data/processed/` are ignored by git.

`run-workflow` also writes run contract artifacts:

- `manifest.json`
- `run_manifest.json`
- `trace.json`
- `quality_report.json`

### `mock_text_to_slices.yaml`

Phase 6 full mock workflow:

1. `analyze_hooks`
2. `generate_scripts`
3. `generate_clip_plans`
4. `mock_slice`

Example:

```powershell
.venv\Scripts\ncut run-workflow --workflow workflows/mock_text_to_slices.yaml --input examples/demo_text/story.txt --output data/processed/runs/demo_full_mock
```

This workflow writes `hooks.json`, `scripts.json`, `clip_plans.json`, `slice_manifest.json`, `.txt` mock clips under `clips/`, and run contract artifacts.

Draft a static workflow plan without executing the workflow:

```powershell
.venv\Scripts\ncut draft-plan --workflow workflows/mock_text_to_slices.yaml --input examples/demo_text/story.txt --output data/reports/workflow_plan.json
```

Inspect the run:

```powershell
.venv\Scripts\ncut inspect-run --run-dir data/processed/runs/demo_full_mock
```

Generate an agent-readable review report:

```powershell
.venv\Scripts\ncut review-run --run-dir data/processed/runs/demo_full_mock
```
